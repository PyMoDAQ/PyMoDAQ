from typing import Iterable, List

from qtpy import QtCore

from pymodaq.control_modules.control_module_selector import ModuleSelector
from pymodaq_utils.categorizing import categorize_items, flatten_categories


class ActuatorSelector(ModuleSelector):
    """Menu button to choose the instrument plugin of a ``DAQ_Move``

    The same button as the one of the ``DAQ_Viewer``, with the plugins grouped as in the add menus (Remote, Mock,
    Plugin...) but, as the actuators have no dimensionality, with one level less.

    Attributes
    ----------
    module_changed: Signal[str]
        Emitted with the name of the actuator when it is changed, by the user or from the code
    """

    module_changed = QtCore.Signal(str)

    def __init__(self, actuators: Iterable[str] = ()):
        super().__init__('', [])
        self._actuators: List[str] = []
        self._actuator = ''
        self.actuators = actuators

    @property
    def actuator(self) -> str:
        return self._actuator

    @actuator.setter
    def actuator(self, name: str):
        if name == self._actuator:
            return
        self._actuator = name
        self.add_widget.setText(name)
        self.add_widget.adjustSize()
        self.module_changed.emit(name)

    @property
    def actuators(self) -> List[str]:
        return list(self._actuators)

    @actuators.setter
    def actuators(self, actuators: Iterable[str]):
        """Fill the menu and select the first one of the menu"""
        self._actuators = list(actuators)
        categorized = categorize_items(self._actuators)
        self.add_menu_entries = categorized
        self.update_add_menu()
        if self._actuator not in self._actuators:
            self._actuator = ''  # the former choice is not available anymore: the signal below tells the change
            in_menu_order = [name for _, name in flatten_categories(categorized)]
            self.actuator = in_menu_order[0] if in_menu_order else ''

    def _add_menu_item_selected(self, name, path_tuple):
        self.actuator = path_tuple[-1]
