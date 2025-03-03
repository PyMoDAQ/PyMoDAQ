from pymodaq_gui.parameter import Parameter, ParameterTree, utils, ioxml, pymodaq_ptypes
from sys import modules as sysmodules
from pymodaq_utils.warnings import deprecation_msg


sysmodules["pymodaq.utils.parameter.pymodaq_ptypes"] = pymodaq_ptypes


deprecation_msg('Importing Parameter stuff from pymodaq is deprecated in pymodaq>5.0.0,'
                'please use the pymodaq_gui package')
