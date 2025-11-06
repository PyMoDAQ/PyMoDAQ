from pymodaq_utils.warnings import deprecation_msg

from pymodaq_gui.messenger import messagebox

deprecation_msg('importing messagebox from pymodaq directly is deprecated. It should now be'
                ' imported from pymodaq_gui.messenger')