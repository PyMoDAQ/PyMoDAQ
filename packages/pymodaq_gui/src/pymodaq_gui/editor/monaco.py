import pymodaq_gui


from qtpy.QtWidgets import QApplication
from qtmonaco import Monaco

from pymodaq_gui.utils.utils import mkQApp


def main():
    qapp = mkQApp('Monaco')


    widget = Monaco()
    # set the default size
    widget.resize(800, 600)
    widget.set_language("python")
    widget.set_theme("vs-dark")
    widget.editor.set_minimap_enabled(False)
    widget.set_text(
        """
    import numpy as np
    from typing import TYPE_CHECKING
    
    if TYPE_CHECKING:
        from bec_lib.devicemanager import DeviceContainer
        from bec_lib.scans import Scans
        dev: DeviceContainer
        scans: Scans
    
    #######################################
    ########## User Script #####################
    #######################################
    
    # This is a comment
    def hello_world():
        print("Hello, world!")
                """
    )

    widget.show()
    qapp.exec_()

if __name__ == "__main__":
    main()