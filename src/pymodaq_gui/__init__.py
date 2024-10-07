import importlib.util
import os
import sys
from pint import UnitRegistry
from pathlib import Path

import warnings


def check_qt_presence():
    try:
        from qtpy import QtWidgets
    except ImportError as e:
        msg = f"\n\n" \
              f"****************************************************************************************\n" \
              f"No Qt backend could be found in your system, please install either pyqt5/6 or pyside2/6.\n\n" \
              f"pyqt5 is still preferred, while pyqt6 should mostly work.\n\n" \
              f"do:\n" \
              f"pip install pyqt5\n for instance\n"\
              f"****************************************************************************************\n"
        warnings.warn(msg, FutureWarning, 2)
        sys.exit()


check_qt_presence()


try:
    from pymodaq_utils.logger import set_logger
    from pymodaq_utils.utils import get_version, PackageNotFoundError
    try:
        __version__ = get_version(__package__)
    except PackageNotFoundError:
        __version__ = '0.0.0dev'
    try:
        logger = set_logger('pymodaq_gui', base_logger=False)
    except Exception:
        print("Couldn't create the local folder to store logs , presets...")

    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info('Starting PyMoDAQ modules')
    logger.info('************************')
    logger.info('')
    logger.info('')


    # in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
    from pymodaq_gui.plotting import data_viewers  # imported here as to avoid circular imports later on
    from pymodaq_gui.qt_utils import setLocale, set_qt_backend

    from pymodaq_utils.config import Config
    from pymodaq_data.plotting.plotter.plotter import register_plotter, PlotterFactory

    # issue on windows when using .NET code within multithreads, this below allows it but requires the
    # pywin32 (pythoncom) package
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

    logger.info('************************')
    logger.info(f"Setting Qt backend to: {config['qtbackend']['backend']} ...")
    set_qt_backend()
    logger.info('************************')
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info(f"Setting Locale to {config['style']['language']} / {config['style']['country']}")
    logger.info('************************')
    setLocale()
    logger.info('')
    logger.info('')

    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info(f"Registering PyMoDAQ qt plotters...")
    register_plotter(parent_module_name='pymodaq_gui.plotting.plotter')
    logger.info(f"Done")
    logger.info('************************')

except Exception as e:
    try:
        logger.exception(str(e))
    except Exception as e:
        print(str(e))
