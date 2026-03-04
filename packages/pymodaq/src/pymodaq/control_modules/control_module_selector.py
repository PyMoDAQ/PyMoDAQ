from qtpy import QtWidgets, QtCore

from pymodaq.control_modules.instruments import DET_TYPES
from pymodaq_gui.utils.menu_utils import build_menu_from_iterable

REMOTE_ITEMS  = {'LECODirector', 'TCPServer'}
MOCK_ITEMS = {}



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


def categorize_items(item_list, remote_items=None, mock_items=None):
    """
    Core function: categorize any list of items into Mock/Plugin/Remote.

    Args:
        item_list: List of items to categorize
        remote_items: Custom set of remote items (optional)
        mock_items: Custom set of mock items (optional)

    Returns: dict {category: [items]} with only non-empty categories
    """
    remote_items = remote_items or REMOTE_ITEMS
    mock_items = mock_items or MOCK_ITEMS

    categorized = {'Remote': [], 'Mock': [], 'Plugin': []}

    for item in item_list:
        if item in remote_items:
            categorized['Remote'].append(item)
        elif item in mock_items or 'mock' in item.lower():
            categorized['Mock'].append(item)
        else:
            categorized['Plugin'].append(item)

    # Return only non-empty categories
    return {k: v for k, v in categorized.items() if v}

def add_category_layers(dimension_dict, remote_items=None, mock_items=None):
    """
    Add category layers to a dimension dictionary.
    Uses categorize_items for each dimension.

    Args:
        dimension_dict: {dimension: [items]}

    Returns: {dimension: {category: [items]}}
    """
    result = {}

    for dimension, items in dimension_dict.items():
        # Reuse the core categorization function
        result[dimension] = categorize_items(items, remote_items, mock_items)

    return result




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


