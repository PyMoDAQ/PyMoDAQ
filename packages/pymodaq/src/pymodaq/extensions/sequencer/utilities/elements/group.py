from typing import Any
from serializall import SerializableFactory

from pymodaq_data import DataToExport
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class GroupElt(SeqEltBase):
    """ A plain, non-looping container: runs its children once, then finishes.

    Distinct from RepeatElt (loops a fixed number of times) and RootElt (the sequence's
    singular, auto-created top-level container) - this is the general-purpose "collapse a few
    steps into one named unit" primitive, addable anywhere like any other element.
    """
    elt_name = 'group'
    children_allowed = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ind_execute: int = 0

    def initialize_element(self):
        """ Reset the re-entry counter so a fresh pass starts clean when this element's
        composite state is entered from outside its normal flow (e.g. a choice jumping
        straight into it) rather than resuming mid-iteration.
        """
        self._ind_execute = 0

    def _eq(self, other: 'SeqEltBase'):
        return True

    def _execute(self, dte: DataToExport = None):
        if self._ind_execute == 0:
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
        return {}

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods

        to be reimplemented
        """
        pass

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        """ Particular Widget allowing the edition of this Element

        Parameters
        ----------
        base_widget :
            You should build your widget based on base_widget
        """
        return base_widget

    def check_set_is_valid(self):
        """ Check the validity of the element

        Nothing to validate: a group has no parameters of its own, only children (which are
        each validated independently by Sequence.is_valid's own tree walk).
        """
        return None
