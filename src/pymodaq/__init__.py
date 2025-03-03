import importlib.util
import os
import sys
from pint import UnitRegistry
from pathlib import Path

import warnings

import pymodaq_utils  # to init stuff related to pymodaq_utils  # necessary, leave it there
import pymodaq_data  # to init stuff related to pymodaq_data  # necessary, leave it there
import pymodaq_gui  # to init stuff related to pymodaq_gui  # necessary, leave it there

from pymodaq_data import Q_, Unit, ureg  # necessary, leave it there


try:
    # with open(str(Path(__file__).parent.joinpath('resources/VERSION')), 'r') as fvers:
    #     __version__ = fvers.read().strip()

    from pymodaq_utils.logger import set_logger
    from pymodaq_utils.utils import get_version
    __version__ = get_version('pymodaq')
    try:
        logger = set_logger('pymodaq', add_handler=True, base_logger=True)

        from pymodaq.utils.daq_utils import copy_preset, get_instrument_plugins

        from pymodaq_utils.config import Config
        from pymodaq.utils.scanner.utils import register_scanners
        from pymodaq_data.plotting.plotter.plotter import register_plotter, PlotterFactory

        # issue on windows when using .NET code within multithreads, this below allows it but requires
        # the pywin32 (pythoncom) package
        if importlib.util.find_spec('clr') is not None:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ModuleNotFoundError as e:
                infos = "You have installed plugins requiring the pywin32 package to work correctly," \
                        " please type in *pip install pywin32* and restart PyMoDAQ"
                print(infos)
                logger.warning(infos)

        config = Config()  # to ckeck for config file existence, otherwise create one
        copy_preset()

        from pymodaq_utils.config import Config
        from pymodaq.utils.scanner.utils import register_scanners

        try:
            # Need the config to exists before importing
            from pymodaq_utils.environment import EnvironmentBackupManager

            if config['backup']['keep_backup']:
                ebm = EnvironmentBackupManager()
                ebm.save_backup()
        except ModuleNotFoundError as e:
            infos = "Your pymodaq_utils version is outdated and doesn't allow for automatic backup of pip packages." \
                    " You should update it."
            print(infos)
            logger.warning(infos)

        logger.info('*************************************************************************')
        logger.info(f"Getting the list of instrument plugins...")
        logger.info('')
        get_instrument_plugins()
        logger.info('*************************************************************************')

        logger.info('')
        logger.info('')
        logger.info('************************')
        logger.info(f"Registering Scanners...")
        register_scanners()
        logger.info(f"Done")
        logger.info('************************')

    except Exception:
        print("Couldn't create the local folder to store logs , presets...")



except Exception as e:
    try:
        logger.exception(str(e))
    except Exception as e:
        print(str(e))
