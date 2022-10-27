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
    with open(str(Path(__file__).parent.joinpath('resources/VERSION')), 'r') as fvers:
        __version__ = fvers.read().strip()

    # in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
    from .daq_utils.daq_utils import set_logger, copy_preset, setLocale, set_qt_backend
    from pymodaq.daq_utils.config import Config

    try:
        logger = set_logger('pymodaq', add_handler=True, base_logger=True)
    except Exception:
        print("Couldn't create the local folder to store logs , presets...")

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
    copy_preset()
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info('Starting PyMoDAQ modules')
    logger.info('************************')
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info(f"Setting Qt backend to: {config['qtbackend']['backend']} ...")
    logger.info('************************')
    set_qt_backend()
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info(f"Setting Locale to {config['style']['language']} / {config['style']['country']}")
    logger.info('************************')
    setLocale()
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info('Initializing the pint unit register')
    logger.info('************************')
    ureg = UnitRegistry()
    Q_ = ureg.Quantity
    logger.info('')
    logger.info('')

except Exception as e:
    try:
        logger.exception(str(e))
    except Exception as e:
        print(str(e))
