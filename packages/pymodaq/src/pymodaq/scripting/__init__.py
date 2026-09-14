from pymodaq_scripting.devices import Actuator, Detector, Dashboard

from pymodaq_utils.warnings import deprecation_msg

deprecation_msg('Please do not import Scripting Devices from pymodaq.scripting, '
                'but from pymodaq_scripting package directly')