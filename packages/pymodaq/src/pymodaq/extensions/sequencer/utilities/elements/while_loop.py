from typing import Any

from serializall import SerializableFactory

from pymodaq_data import DataToExport

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory
from pymodaq.extensions.sequencer.utilities.elements.group import GroupElt
from pymodaq.extensions.sequencer.utilities.holders.condition_holder import ConditionHolder
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class WhileElt(GroupElt):
    """ A condition-driven loop: runs its children repeatedly while a condition evaluates True,
    finishes once it evaluates False.

    A GroupElt whose "run once" becomes "run while this condition holds" - this is the
    "while True: repeat this action" primitive, sibling to RepeatElt (which counts instead).
    The condition itself, its picker UI, and its dashboard wiring all come from
    ConditionHolder - the same one ChoiceElt uses - so there's nothing WhileElt-specific to add
    beyond deciding, each pass, whether to loop again.
    """
    elt_name = 'while'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.condition = ConditionHolder(self, combo_tooltip='Loop while this condition evaluates True')

    def do_things_with_dashboard(self):
        self.condition.bind_to_dashboard()

    @property
    def choice_model(self):
        return self.condition.model

    @choice_model.setter
    def choice_model(self, value: str):
        self.condition.model = value

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        return self.condition.create_widget(base_widget)

    def to_dict_custom(self) -> dict[str, Any]:
        return self.condition.to_dict()

    def from_dict_custom(self, dict_config: dict[str, Any]):
        self.condition.from_dict(dict_config)

    def _eq(self, other: 'WhileElt') -> bool:
        if not hasattr(other, 'condition'):
            return False
        return self.condition.eq(other.condition)

    def check_set_is_valid(self):
        self.condition.check_set_is_valid()

    def _execute(self, dte: DataToExport = None):
        if self.choice_model.evaluate(dte):
            self.children_signal.emit()
        else:
            self.done_signal.emit()

    def __repr__(self):
        return f'{super().__repr__()} - while {self.choice_model.model_name}'
