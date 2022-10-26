from .daq_utils import set_logger
from .parameter.ioxml import *
from .parameter.pymodaq_ptypes import *
from .parameter.utils import *

logger = set_logger('custom_paramater', add_to_console=True)
logger.warning('Calling the custom_parameter_module will soon be deprecated!\n'
               'Please use either the ioxml, utils or pymodaq_ptypes submodules from the '
               'pymodaq.daq_utils.parameter module')
