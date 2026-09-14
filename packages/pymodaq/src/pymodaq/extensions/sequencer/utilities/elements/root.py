from typing import Any
from serializall import SerializableFactory

from pymodaq_data import DataToExport
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class RootElt(SeqEltBase):
    elt_name = 'root'
    children_allowed = True

    def __init__(self, id: int = -1, parent=None, **kwargs):  # should keep the signature of the base
        # Pass a specific string or ID to distinguish it from standard data
        super().__init__(id=id, parent=parent, **kwargs)
        self._ind_execute: int = 0

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
