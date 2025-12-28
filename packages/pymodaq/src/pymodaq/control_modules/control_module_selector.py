from qtpy import QtWidgets
from pymodaq.control_modules.instruments import DET_TYPES

REMOTE_ITEMS  = {'LECODirector', 'TCPServer'}
MOCK_ITEMS = {}



class ModuleSelector:
    """
    Group parameters are used mainly as a generic parent item that holds (and groups!) a set
    of child parameters. It also provides a simple mechanism for displaying a button or combo
    that can be used to add new parameters to the group.
    """

    def __init__(self, add_text: str, add_menu_entries):
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
            self._build_menu_from_iterable(self.add_menu, self.add_menu_entries)
        finally:
            self.add_widget.blockSignals(False)

    def _build_menu_from_iterable(self, menu, items, path=()):
        if isinstance(items, dict):
            for key, value in items.items():
                self._handle_menu_item(menu, key, value, path)
        elif isinstance(items, (list, tuple)):
            for item in items:
                if isinstance(item, dict):
                    for key, value in item.items():
                        self._handle_menu_item(menu, key, value, path)
                elif isinstance(item, str):
                    self._add_leaf_action(menu, item, path + (item,))

    def _handle_menu_item(self, menu: QtWidgets.QMenu, key, value, path):
        """Handle a single menu item (key-value pair)"""
        new_path = path + (key,)

        if self._is_nested(value):
            # Create submenu and recurse
            submenu = menu.addMenu(key)
            self._build_menu_from_iterable(submenu, value, new_path)
        else:
            # Create leaf action
            self._add_leaf_action(menu, key, new_path)

    def _is_nested(self, value):
        """Check if a value represents nested structure"""
        return isinstance(value, (dict, list, tuple)) and value  # Not empty

    def _add_leaf_action(self, menu: QtWidgets.QMenu, name, path):
        """Add a leaf action to the menu"""
        action = menu.addAction(name)
        action.triggered.connect(lambda checked, data=path: self._add_menu_item_selected(data))

    def _add_menu_item_selected(self, path_tuple):
        """Called when a menu item is selected from the nested add menu
        The parameter MUST have an 'addNew' method defined.
        """
        # Call the parameter's addNew method with the selected type
        self.add_widget.setText(f'{path_tuple[0]}/{path_tuple[-1]}')
        self.add_widget.adjustSize()


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
    from pymodaq_gui.utils.utils import mkQApp

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

    app.exec()


