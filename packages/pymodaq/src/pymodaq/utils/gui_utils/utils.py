from pymodaq_utils.config import Config
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.utils.splash import get_splash_sc


config = Config()
logger = set_logger(get_module_name(__file__))

from pymodaq_utils.warnings import deprecation_msg

deprecation_msg('Importing get_splash_sc stuff from pymodaq is deprecated '
                'in pymodaq>5.0.0,'
                'please use the same method from the '
                'pymodaq_gui.utils.splash module')



