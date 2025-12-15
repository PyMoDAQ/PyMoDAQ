import importlib.util
import os
import sys
import pkgutil

def set_and_check_qt_backend_or_die(config):
    wanted_backend = config('qtbackend', 'backends')[0]
    backend = wanted_backend
    #filter to get only qt backend modules
    available_backends = [mod.name.lower() for mod in pkgutil.iter_modules() \
                          if mod.name.lower() in [ backend.lower() for backend in config('qtbackend', 'backends')]]

    backend_found = wanted_backend.lower() in available_backends
    if not backend_found:
        #trying in the remaining backends and taking the first one
        logger.warning(f"{backend} is not available. Trying to find another backend.")
        other_backends = [backend for backend in available_backends if backend != wanted_backend]
        if len(other_backends) > 0:
            backend_found = True
            backend =  other_backends[0]
            config['qtbackend']['backend'] = backend

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



try:
    from pymodaq_utils.utils import get_version, PackageNotFoundError
    __version__ = get_version(__package__)
except PackageNotFoundError:
    __version__ = '0.0.0dev'


from pymodaq_utils.config import Config
config = Config()  # to check for config file existence, otherwise create one

from pymodaq_utils.logger import set_logger
logger = set_logger('pymodaq_gui', base_logger=False)

logger.info('Starting PyMoDAQ GUI modules')
logger.info(f"Trying to set Qt backend to: {config('qtbackend', 'backends')[0]}")
set_and_check_qt_backend_or_die(config)


from pymodaq_gui.qt_utils import setLocale

from pymodaq_data.plotting.plotter.plotter import register_plotter, PlotterFactory

logger.info(f"Setting Locale to {config('style', 'language')} / {config('style', 'country')}")
setLocale()

logger.info(f"Registering PyMoDAQ qt plotters...")

register_plotter(parent_module_name='pymodaq_gui.plotting.plotter')

logger.info(f"Done")

# in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
from pymodaq_gui.plotting import data_viewers  # imported here as to avoid circular imports later on


