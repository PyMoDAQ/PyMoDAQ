from pymodaq_gui.utils.widgets.lcd import LCD

from pymodaq_utils.warnings import deprecation_msg

deprecation_msg('Importing make_window from pymodaq is deprecated '
                'in pymodaq>=5.2.0,'
                'please use the same method from the '
                'pymodaq_gui.utils.widgets.window module')
