from typing import Any

from serializall import SerializableFactory

from qtpy import QtCore

from pymodaq.utils.managers.modules import ModuleType
from pymodaq_data import DataToExport
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager

ser_factory = SerializableFactory()

@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class RepeatElt(SeqEltBase):

    elt_name = 'repeat'
    children_allowed = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._n_repeat: int = 3
        self._ind_execute = 0

    def initialize_element(self):
        self._ind_execute = 0

    def do_things_with_dashboard(self):
        pass

    @property
    def n_repeat(self) -> int:
        return self._n_repeat

    @n_repeat.setter
    def n_repeat(self, value: int):
        self._n_repeat = value

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        spinbox = SpinBox(parent=base_widget, int=True, value=self.n_repeat)
        base_widget.add_widget_top(spinbox)
        spinbox.sigValueChanged.connect(self.set_repeat_from_spinbox)
        base_widget.give_focus_to(spinbox)
        return base_widget

    def set_repeat_from_spinbox(self, spinbox: SpinBox):
        self.n_repeat = spinbox.value()

    def _execute(self, dte: DataToExport=None):
        if self._ind_execute < self.n_repeat:
            """ This will execute the children state and its bundled elements n_repeat times"""
            self._ind_execute += 1
            self.children_signal.emit()
        else:
            self._ind_execute = 0
            self.done_signal.emit()

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return {'n_repeat': self.n_repeat}

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.n_repeat = dict_config.pop('n_repeat')

    def _eq(self, other: 'RepeatElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return self.n_repeat == other.n_repeat

    def __repr__(self):
        return f'{super().__repr__()} - {self.n_repeat}'

    def check_set_is_valid(self):
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        if not (self.n_repeat >= 1):
            raise ElementError(f'Element {self}: at least one repetition required')
