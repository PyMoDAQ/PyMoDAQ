import importlib.util
import os
import sys
import pkgutil
from qtpy import QtWidgets

def set_and_check_qt_backend_or_die(config):
    wanted_backend = config('gui', 'qtbackend', 'backend')[0]
    backend = wanted_backend
    #filter to get only qt backend modules
    available_backends = [mod.name.lower() for mod in pkgutil.iter_modules() \
                          if mod.name.lower() in [ backend.lower() for backend in config('gui', 'qtbackend', 'backend')]]

    backend_found = wanted_backend.lower() in available_backends
    if not backend_found:
        #trying in the remaining backends and taking the first one
        logger.warning(f"{backend} is not available. Trying to find another backend.")
        other_available = [b for b in available_backends if b != wanted_backend]
        if len(other_available) > 0:
            backend_found = True
            backend = other_available[0]
            # Reorder full list so the working backend is first; preserve all entries
            full_list = config('gui', 'qtbackend', 'backend')
            config['gui', 'qtbackend', 'backend'] = [backend] + [b for b in full_list if b != backend]

    if backend_found:
        # environment variable is set
        os.environ['QT_API'] = backend
        try:
            import qtpy
            logger.info(f"{qtpy.API_NAME} Qt backend loaded")
        except ImportError as e:
            print(f'Should have selected {backend} for qtpy but still failed:')
            print(e)
            sys.exit(-1)

    else:
        msg = "No Qt backend could be found in your system, please install either pyqt6 or pyside6." \
              "(pyqt6 is preferred).\n"
        logger.error(msg)
        print(msg)
        sys.exit(-1)

def set_check_style():
    current_styles = config('gui', 'style', 'style')
    styles_default = ['Fusion']
    styles = QtWidgets.QStyleFactory.keys()
    styles_default.extend(styles)
    for style in current_styles[:]:
        if style not in styles_default:
            current_styles.remove(style)
    for style in styles_default:
        if style not in current_styles:
            current_styles.append(style)

    config['gui', 'style', 'style'] = current_styles
    config.save()


try:
    from pymodaq_utils.utils import get_version, PackageNotFoundError
    __version__ = get_version(__package__)
except PackageNotFoundError:
    __version__ = '0.0.0dev'

#registering config
from pymodaq_gui import config as local_config
from pymodaq_utils.config import GlobalConfig as Config
config = Config()  # to check for config file existence, otherwise create one

from pymodaq_utils.logger import set_logger
logger = set_logger('pymodaq_gui', base_logger=False)



logger.info('Starting PyMoDAQ GUI modules')
if not isinstance(config('gui', 'qtbackend', 'backend'), list):  #True for old usage
    logger.error(f"{config('gui', 'qtbackend', 'backend')} is not a list, please delete your actual "
                 f"pymodaq_utils configuration file to "
                 f"reflect this new type")
    sys.exit(-1)
logger.info(f"Trying to set Qt backend to: {config('gui', 'qtbackend', 'backend')[0]}")
set_and_check_qt_backend_or_die(config)


from pymodaq_gui.qt_utils import setLocale

set_check_style()

from pymodaq_data.plotting.plotter.plotter import register_plotter, PlotterFactory

logger.info(f"Setting Locale to {config('gui', 'style','language')} / {config('gui', 'style', 'country')}")
setLocale()


logger.info(f"Registering PyMoDAQ qt plotters...")

register_plotter(parent_module_name='pymodaq_gui.plotting.plotter')
backends_config = config('data', 'plotting', 'backend')
for backend in PlotterFactory.backends():
    if backend not in backends_config:
        backends_config.append(backend)
config['data', 'plotting', 'backend'] = backends_config
config.save()
logger.info(f"Done")

# in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
from pymodaq_gui.plotting import data_viewers  # imported here as to avoid circular imports later on


