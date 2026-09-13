from qtpy import QtWidgets, QtCore

from pymodaq.control_modules.instruments import DET_TYPES
from pymodaq_gui.utils.menu_utils import build_menu_from_iterable

from pymodaq_utils.categorizing import categorize_items, find_last_index, add_category_layers, REMOTE_ITEMS, MOCK_ITEMS


class ModuleSelector(QtCore.QObject):
    """
    Group parameters are used mainly as a generic parent item that holds (and groups!) a set
    of child parameters. It also provides a simple mechanism for displaying a button or combo
    that can be used to add new parameters to the group.
    """

    module_changed = QtCore.Signal(tuple)

    def __init__(self, add_text: str, add_menu_entries):
        super().__init__()
        self.add_widget = QtWidgets.QPushButton(add_text)
        #self.add_widget.clicked.connect(self.addClicked)
        self.add_menu_entries = add_menu_entries

        # Create the nested menu
        self.add_menu = QtWidgets.QMenu(self.add_widget)
        self.add_widget.setMenu(self.add_menu)
        # Populate the nested menu structure
        self.update_add_menu()

    def update_add_menu(self):
        self.add_widget.blockSignals(True)
        try:
            self.add_menu.clear()
            build_menu_from_iterable(self.add_menu, self.add_menu_entries,
                                     self._add_menu_item_selected)
        finally:
            self.add_widget.blockSignals(False)

    def _add_menu_item_selected(self, name, path_tuple):
        """Called when a menu item is selected from the nested add menu."""
        self.add_widget.setText('/'.join(path_tuple))
        self.add_widget.adjustSize()
        self.module_changed.emit(path_tuple)





if __name__ == '__main__':
    import sys
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('Selector')

    options = {
        'DAQ0D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ0D']]],
        'DAQ1D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ1D']]],
        'DAQ2D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ2D']]],
        'DAQND': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQND']]],
    }
    add_menu_entries = add_category_layers(options)


    selector = ModuleSelector('Add', add_menu_entries)
    selector.add_widget.show()

    sys.exit(app.exec())


