import weakref
from typing import TYPE_CHECKING, Any, Union
import numpy as np


from qtpy import QtWidgets, QtCore

from serializall import SerializableFactory
from pymodaq_data import DataToExport

from pymodaq_gui.utils.widgets.combo import ComboBox
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from pymodaq_utils.utils import find_objects_in_list_from_attr_name_val

if TYPE_CHECKING:
    from pymodaq.extensions.sequencer.utilities.sequencer.sequence import Sequence


ser_factory = SerializableFactory()

@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class SequenceElt(SeqEltBase):

    elt_name = 'sequence'
    children_allowed = False
    sequences: list['Sequence'] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sequence: str = None
        self.sequence: str = None if len(self.get_sequences_name()) == 0 else self.get_sequences_name()[0]

        self._combo: weakref.ref[ComboBox] | None = None  # weakref to the combobox holding the states

    @classmethod
    def register_sequence(cls, sequence: 'Sequence'):
        if sequence.title not in [seq.title for seq in cls.sequences]:
            cls.sequences.append(sequence)

    def get_sequences(self) -> list['Sequence']:
        """ Get the list of Sequences that can be started, removing the one this element belong to"""
        sequences = list(self.sequences)
        if self.parent_sequence is not None:
            sequences.remove(find_objects_in_list_from_attr_name_val(
                sequences, 'title', self.parent_sequence.title)[0])
        return sequences

    def get_sequences_name(self) -> list[str]:
        """ Get the list of Sequences that can be started, removing the one this element belong to"""
        return [seq.title for seq in self.get_sequences()]

    def do_things_with_parent_sequence(self):
        """ If this Element is using the Dashboard, once its setter has been called, this method will be executed

        Do whatever is needed to instantiate your element with the Dashboard
        """
        pass
        #self.sequence: str = None if len(self.get_sequences_name()) == 0 else self.get_sequences_name()[0]

    @property
    def sequence_obj(self) -> Union['Sequence', None]:
        match =  find_objects_in_list_from_attr_name_val(
            self.get_sequences(),
            'title',
            self.sequence)
        if len(match) > 0:
            return match[0]
        return None

    @property
    def sequence(self) -> str:
        return self._sequence

    @sequence.setter
    def sequence(self, value: str):
        self._sequence = value
        self.mstate.clear_transitions()
        self.mstate.add_external_transition(self.sequence_obj.machine.finished,
                                            self.mstate.done_state)

    def update_combo_sequences(self):
        if self._combo is not None and self._combo() is not None:
            self._combo().set_items(self.get_sequences_name())

    @QtCore.Slot(str)
    def set_sequence(self, value: str):
        self.sequence = value

    def do_things_with_dashboard(self):
        pass

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:

        combo = ComboBox(base_widget)
        combo.set_items(self.get_sequences_name())
        base_widget.add_widget_top(combo)
        combo.setCurrentText(self.sequence)
        combo.currentTextChanged.connect(self.set_sequence)
        self._combo = weakref.ref(combo)

        return base_widget

    def _execute(self, dte: DataToExport = None):
        self.sequence_obj.start_sequence()

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return {'sequence': self.sequence,
                }

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.sequence = dict_config.pop('sequence')

    def _eq(self, other: 'SequenceElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return (self.sequence == other.sequence)

    def __repr__(self):
        return f'{super().__repr__()} - {self.sequence}'

    def check_set_is_valid(self) -> bool:
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        pass