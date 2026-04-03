import sys

from qtpy import QtWidgets

from pymodaq.utils.managers.configurator.configurator import Configurator
from pymodaq_gui.utils.utils import mkQApp


def main() :
    app = mkQApp('Bug sync')
    configurator = Configurator()

    win = QtWidgets.QMainWindow()
    win.setWindowTitle('Bug sync')
    win.setCentralWidget(configurator.add_toolbar('test'))
    configurator.preset_manager.get_external_toolbar_menu(toolbar=configurator.get_toolbar('test'))
    configurator.get_external_toolbar_menu(toolbar=configurator.get_toolbar('test'))
    configurator.preset_manager.enable_actions(True)
    configurator.enable_actions(True)

    win.show()
    sys.exit(app.exec())



if __name__ == '__main__' :
    main()