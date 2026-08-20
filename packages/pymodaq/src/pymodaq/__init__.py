import importlib.util
import os
import sys
from pint import UnitRegistry
from pathlib import Path

import warnings

import pymodaq_utils  # noqa to init stuff related to pymodaq_utils  # necessary, leave it there
import pymodaq_data  # noqa to init stuff related to pymodaq_data  # necessary, leave it there
import pymodaq_gui  # noqa to init stuff related to pymodaq_gui  # necessary, leave it there

from pymodaq_data import Q_, Unit, ureg  # noqa necessary, leave it there

from pymodaq.utils.config import Config  #  noqa Necessary for registration
from pymodaq_utils.config import GlobalConfig
try:
    # with open(str(Path(__file__).parent.joinpath('resources/VERSION')), 'r') as fvers:
    #     __version__ = fvers.read().strip()

    from pymodaq_utils.logger import set_logger
    from pymodaq_utils.utils import get_version
    __version__ = get_version('pymodaq')
    try:
        logger = set_logger('pymodaq', add_handler=True, base_logger=True)

        from pymodaq.utils.daq_utils import copy_experiment, get_instrument_plugins

        from pymodaq.utils.scanner.utils import register_scanners
        from pymodaq.control_modules.ui_utils import register_uis
        from pymodaq_data.plotting.plotter.plotter import register_plotter, PlotterFactory

        # issue on windows when using .NET code within multithreads, this below allows it but requires
        # the pywin32 (pythoncom) package
        try:
            if 'win' in sys.platform and importlib.util.find_spec('clr') is not None:
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                except ModuleNotFoundError as e:
                    infos = "You have installed plugins requiring the pywin32 package to work correctly," \
                            " please type in *pip install pywin32* and restart PyMoDAQ"
                    print(infos)
                    logger.warning(infos)
        except ValueError:
            pass

        config = GlobalConfig()  # to ckeck for config file existence, otherwise create one
        copy_experiment()


        from pymodaq.utils.scanner.utils import register_scanners

        from pymodaq_utils.environment import EnvironmentBackupManager

        if config('utils', 'backup', 'keep_backup'):
            ebm = EnvironmentBackupManager()
            ebm.save_backup()
    
        logger.info('*************************************************************************')
        logger.info(f"Registering UIs...")
        register_uis(parent_module_name='pymodaq.control_modules.daq_move_ui')

        # check the registered UI wrt the configuration
        from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory

        uis_registered = ActuatorUIFactory().keys()
        
        uis_config = config('pymodaq', 'actuator', 'ui')
        if not isinstance(uis_config, list):
            uis_config = [uis_config]

        for ui in uis_registered:
            if ui not in uis_config:
                uis_config.append(ui)
                
        config['pymodaq', 'actuator', 'ui'] = uis_config
        config.save()


        logger.info(f"Done")
        logger.info('************************')

        logger.info('*************************************************************************')
        logger.info(f"Getting the list of instrument plugins...")
        logger.info('')
        CONTROL_MODULES = get_instrument_plugins()
        logger.info('*************************************************************************')

        logger.info('')
        logger.info('')
        logger.info('************************')
        logger.info(f"Registering Scanners...")
        register_scanners()
        logger.info(f"Done")
        logger.info('************************')


    except Exception as e:
        try:
            logger.exception(str(e))
        except Exception as e:
            print(str(e))


except Exception as e:
    try:
        logger.exception(str(e))
    except Exception as e:
        print(str(e))
