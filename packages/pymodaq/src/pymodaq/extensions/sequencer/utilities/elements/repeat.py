from typing import Any

from serializall import SerializableFactory

from pymodaq_data import DataToExport
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.elements.group import GroupElt
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar

ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class RepeatElt(GroupElt):
    """ Loops its children a fixed number of times, then finishes.

    A GroupElt that counts: GroupElt's "run once" _execute becomes "run n_repeat times" here,
    reusing its re-entry counter (_ind_execute) and composite-state contract unchanged.
    """

    elt_name = 'repeat'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._n_repeat: int = 3

    @property
    def n_repeat(self) -> int:
        return self._n_repeat

    @n_repeat.setter
    def n_repeat(self, value: int):
        self._n_repeat = value

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        base_widget = super()._create_widget(base_widget)
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
        dict_config = super().to_dict_custom()
        dict_config['n_repeat'] = self.n_repeat
        return dict_config

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        super().from_dict_custom(dict_config)
        self.n_repeat = dict_config.pop('n_repeat')

    def _eq(self, other: 'RepeatElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return super()._eq(other) and self.n_repeat == other.n_repeat

    def __repr__(self):
        return f'{super().__repr__()} - {self.n_repeat}'

    def check_set_is_valid(self):
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        super().check_set_is_valid()
        if not (self.n_repeat >= 1):
            raise ElementError(f'Element {self}: at least one repetition required')
