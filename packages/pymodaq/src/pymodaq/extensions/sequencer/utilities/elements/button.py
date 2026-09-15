from typing import Any
from qtpy import QtWidgets
from serializall import SerializableFactory

from pymodaq_data import DataToExport
from pymodaq_gui.utils.menu_utils import MenuButton
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase

from pymodaq.extensions.sequencer.utilities.elements.root import RootElt
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar

seq_factory = SeqEltFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class AddButtonPlaceholder(SeqEltBase):
    elt_name = 'button'
    children_allowed = False

    def __init__(self, id: int = -2, parent=None, **kwargs):  # should keep the signature of the base
        # Pass a specific string or ID to distinguish it from standard data
        super().__init__(id=id, parent=parent, **kwargs)

    def create_widget(self, parent=None) -> QtWidgets.QWidget:
        return MenuButton('Add Element',
                          [elt.capitalize() for elt in seq_factory.elements if not
                          (elt == AddButtonPlaceholder.elt_name or
                           elt == RootElt.elt_name)],
                          update_button_text=False,
                          parent=parent)

    def _eq(self, other: 'SeqEltBase'):
        return True

    def _execute(self, dte: DataToExport = None):
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
