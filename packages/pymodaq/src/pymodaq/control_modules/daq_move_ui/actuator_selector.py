from typing import Iterable, List

from qtpy import QtCore

from pymodaq_gui.utils.menu_utils import MenuButton
from pymodaq_utils.categorizing import categorize_items, flatten_categories


class ActuatorSelector(MenuButton):
    """Menu button to choose the instrument plugin of a ``DAQ_Move``

    The plugins are grouped as in the add menus (Remote, Mock, Plugin...) but, as the actuators have no
    dimensionality, with one level less than the selector of the ``DAQ_Viewer``. The button shows the name of the
    chosen actuator.

    Attributes
    ----------
    actuator_changed: Signal[str]
        Emitted with the name of the actuator when it is changed, by the user or from the code
    """

    actuator_changed = QtCore.Signal(str)

    def __init__(self, actuators: Iterable[str] = (), parent=None):
        super().__init__('', parent=parent, update_button_text=False)
        self._actuators: List[str] = []
        self._actuator = ''
        self.triggered.connect(self._actuator_chosen)
        self.actuators = actuators

    def _actuator_chosen(self, path: tuple):
        self.actuator = path[-1]

    @property
    def actuator(self) -> str:
        return self._actuator

    @actuator.setter
    def actuator(self, name: str):
        if name == self._actuator:
            return
        self._actuator = name
        self.setText(name)
        self.adjustSize()
        self.actuator_changed.emit(name)

    @property
    def actuators(self) -> List[str]:
        return list(self._actuators)

    @actuators.setter
    def actuators(self, actuators: Iterable[str]):
        """Fill the menu and select the first actuator of the menu if the current one is not in the list"""
        self._actuators = list(actuators)
        categorized = categorize_items(self._actuators)
        self.update_entries(categorized)
        if self._actuator not in self._actuators:
            self._actuator = ''  # the former choice is not available anymore: the signal below tells the change
            in_menu_order = [name for _, name in flatten_categories(categorized)]
            self.actuator = in_menu_order[0] if in_menu_order else ''
