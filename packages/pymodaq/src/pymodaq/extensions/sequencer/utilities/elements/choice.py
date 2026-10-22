from typing import Any

from pyqtgraph import mkColor

from serializall import SerializableFactory

from pymodaq_data import DataToExport

from pymodaq_utils.warnings import deprecation_msg

from qt_themes import get_theme
from pymodaq_gui.utils.widgets.combo import ComboBox
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq.extensions.sequencer.utilities.holders.branch_holder import BranchHolder
from pymodaq.extensions.sequencer.utilities.holders.condition_holder import ConditionHolder
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class ChoiceElt(SeqEltBase):
    """ Branches to one of two other elements (by id, anywhere in the tree) based on a
    pluggable condition.

    Composes two independent, reusable pieces rather than inheriting them: `condition`
    (ConditionHolder - picks a ChoiceModel) and `branches` (BranchHolder - holds the
    True/False targets). go_to_true/go_to_false stay as plain properties over branches'
    storage (public API / YAML keys unchanged).

    `condition` is constructed before `branches` deliberately: branches' first touch of
    self.mstate (building its first ValueTransition) lazily constructs a CompositeState that
    stringifies this element via __repr__, which reads self.choice_model - so condition needs
    to already exist. With composition this is just the plain, visible order of two lines
    below, not a cooperative-super()-unwind-order puzzle to get right (see git history for the
    two different bugs that puzzle caused when this was built from mixins instead).
    """

    elt_name = 'choice'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.condition = ConditionHolder(self, combo_tooltip='Choice Model')
        self.branches = BranchHolder(self, {True: 'True', False: 'False'})

    def do_things_with_dashboard(self):
        self.condition.bind_to_dashboard()

    @property
    def choice_model(self):
        return self.condition.model

    @choice_model.setter
    def choice_model(self, value: str):
        self.condition.model = value

    def set_choice_model(self, value: str):
        """ Deprecated: set `choice_model` directly instead. """
        deprecation_msg('ChoiceElt.set_choice_model is deprecated, set choice_model directly')
        self.choice_model = value

    @property
    def go_to_true(self) -> int:
        return self.branches._go_to[True]

    @go_to_true.setter
    def go_to_true(self, value: int):
        self.branches.set_go_to(True, value)

    def set_go_to_true(self, index: int):
        """ Deprecated: set `go_to_true` directly with an element id instead. `index` here is
        an index into `get_ids(without_ids=self.without_ids, without_types=self.without_types)`,
        not an id. """
        deprecation_msg('ChoiceElt.set_go_to_true is deprecated, set go_to_true directly with an element id')
        self.go_to_true = self.branches._index_to_id(index)

    @property
    def go_to_false(self) -> int:
        return self.branches._go_to[False]

    @go_to_false.setter
    def go_to_false(self, value: int):
        self.branches.set_go_to(False, value)

    def set_go_to_false(self, index: int):
        """ Deprecated: set `go_to_false` directly with an element id instead. `index` here is
        an index into `get_ids(without_ids=self.without_ids, without_types=self.without_types)`,
        not an id. """
        deprecation_msg('ChoiceElt.set_go_to_false is deprecated, set go_to_false directly with an element id')
        self.go_to_false = self.branches._index_to_id(index)

    @property
    def without_ids(self):
        """ Deprecated: was only ever used to build set_go_to_true/set_go_to_false's index. """
        deprecation_msg('ChoiceElt.without_ids is deprecated')
        return (self.id,)

    @property
    def without_types(self):
        """ Deprecated: was only ever used to build set_go_to_true/set_go_to_false's index. """
        deprecation_msg('ChoiceElt.without_types is deprecated')
        return (AddButtonPlaceholder,)

    def _style_go_to_combo(self, combo: ComboBox, branch: bool):
        color_name = 'green' if branch else 'red'
        combo.setStyleSheet(
            f"""background-color: #{hex(mkColor(getattr(get_theme(), color_name)).rgb())[2:]};
                color: #{hex(mkColor(get_theme().base).rgb())[2:]};
            """)

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        base_widget = self.condition.create_widget(base_widget)
        self.branches.create_widgets(base_widget, style_hook=self._style_go_to_combo)
        return base_widget

    def to_dict_custom(self) -> dict[str, Any]:
        dict_config = {'go_to_true': self.go_to_true,
                       'go_to_false': self.go_to_false}
        dict_config.update(self.condition.to_dict())
        return dict_config

    def from_dict_custom(self, dict_config: dict[str, Any]):
        self.go_to_true = dict_config.pop('go_to_true')
        self.go_to_false = dict_config.pop('go_to_false')
        self.condition.from_dict(dict_config)

    def _eq(self, other: 'ChoiceElt') -> bool:
        if not hasattr(other, 'go_to_true'):
            return False
        if not (self.go_to_false == other.go_to_false and
                self.go_to_true == other.go_to_true):
            return False
        return self.condition.eq(other.condition)

    def __repr__(self):
        return f'{super().__repr__()} - Model: {self.choice_model.model_name} - True: {self.go_to_true} - False: {self.go_to_false}'

    def _execute(self, dte: DataToExport=None):
        self.choice_model.execute(dte)

    def check_set_is_valid(self) -> bool:
        self.branches.check_set_is_valid()
        self.condition.check_set_is_valid()
