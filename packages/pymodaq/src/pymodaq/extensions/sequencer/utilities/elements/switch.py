import weakref
from typing import Any, Union

from qtpy import QtCore, QtWidgets

from serializall import SerializableFactory

from pymodaq_data import DataToExport
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_gui.utils.widgets.combo import ComboBox
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq.extensions.sequencer.utilities.element_factory import (
    SeqEltBase, SeqEltFactory, SeqEltCategory, ElementError)
from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq.extensions.sequencer.utilities.holders.rule import CONTINUE, MANUAL_OVERRIDE_ID, Rule, Target
from pymodaq.extensions.sequencer.utilities.holders.condition_holder import ConditionHolderBase
from pymodaq.extensions.sequencer.utilities.states import ValueTransition
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


logger = set_logger(get_module_name(__file__))


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class SwitchElt(SeqEltBase):
    """ Branches to one of several other elements (by id, anywhere in the tree) based on an
    ordered Rule list: each Rule pairs a pluggable Condition (the same ChoiceModelBase family
    ChoiceElt uses) with a Target, evaluated top to bottom - the first Rule whose Condition
    matches fires. A mandatory, always-last fallback Rule (pinned to the trivial
    TrueChoiceModel) guarantees every evaluation resolves to exactly one target.

    `ChoiceElt` is the permanently-locked 2-Rule case of this (`rules_locked = True`, exactly
    one pluggable-condition Rule plus the fallback).

    A separate, element-level manual override (not a Rule, not a Condition) can force
    execution straight to a chosen target, bypassing Rule evaluation entirely - for forcing a
    branch while building or testing a sequence.
    """

    elt_name = 'switch'
    elt_category = SeqEltCategory.LOGIC

    #: ChoiceElt locks this to True: no add/remove-Rule UI or API, so it cannot grow past its
    #: fixed 2 rows.
    rules_locked = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rules: list[Rule] = []
        self._next_rule_id = 0
        self._live_rows_widget = None

        self._fallback = self._new_rule(is_fallback=True)
        self._rules.append(self._fallback)

        manual_transition = ValueTransition(self.go_to_signal, MANUAL_OVERRIDE_ID,
                                            source_state=self.mstate)
        self.mstate.addTransition(manual_transition)
        self._manual_target = Target(self, manual_transition)
        self._manual_enabled = False

    def _new_rule(self, is_fallback: bool = False) -> Rule:
        rule_id = self._next_rule_id
        self._next_rule_id += 1
        return Rule(self, rule_id, is_fallback=is_fallback)

    def _insert_rule(self) -> Rule:
        """ Internal: insert a new regular rule just before the fallback - no rules_locked
        check, so ChoiceElt can use it to build its own fixed rules in __init__. """
        rule = self._new_rule()
        self._rules.insert(len(self._rules) - 1, rule)
        return rule

    def _rule_by_id(self, rule_id: int) -> Union[Rule, None]:
        for rule in self._rules:
            if rule.id == rule_id:
                return rule
        return None

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    @property
    def fallback_rule(self) -> Rule:
        return self._fallback

    def add_rule(self) -> Rule:
        if self.rules_locked:
            raise ElementError(f'Element {self}: rules are locked, cannot add a rule')
        rule = self._insert_rule()
        self._refresh_live_widget()
        return rule

    def remove_rule(self, rule_id: int):
        if self.rules_locked:
            raise ElementError(f'Element {self}: rules are locked, cannot remove a rule')
        rule = self._rule_by_id(rule_id)
        if rule is None or rule.is_fallback:
            return
        self.mstate.removeTransition(rule.transition)
        self._rules.remove(rule)
        self._refresh_live_widget()

    @property
    def manual_override_enabled(self) -> bool:
        return self._manual_enabled

    @manual_override_enabled.setter
    def manual_override_enabled(self, value: bool):
        self._manual_enabled = bool(value)

    @property
    def manual_override_target(self) -> Union[int, str, None]:
        return self._manual_target.go_to

    @manual_override_target.setter
    def manual_override_target(self, value: Union[int, str]):
        self._manual_target.go_to = value

    def do_things_with_dashboard(self):
        for rule in self._rules:
            rule.condition.bind_to_dashboard()

    def _execute(self, dte: DataToExport = None):
        if self._manual_enabled:
            self.go_to_signal.emit(MANUAL_OVERRIDE_ID)
            return
        for rule in self._rules:
            if rule.condition.model.evaluate(dte):
                self.go_to_signal.emit(rule.id)
                return

    def check_set_is_valid(self):
        for rule in self._rules:
            rule.check_set_is_valid()
        if self._manual_enabled:
            self._manual_target.check_is_valid('manual override')
        else:
            self._manual_target.update()
        self._warn_on_overlapping_rules()

    def _warn_on_overlapping_rules(self):
        """ Not a hard error: more than one non-fallback rule currently matching usually means
        overlapping conditions, worth flagging, but the first-match-wins evaluation order
        still resolves to a single, well-defined target.

        Short-circuits without calling evaluate() at all when fewer than two non-fallback
        rules exist (ChoiceElt's fixed case: exactly one) - overlap is structurally
        impossible there, and evaluate() can have real side effects (grabbing live detector
        data, popping a user_input dialog) that ChoiceElt's check_set_is_valid must not grow
        as an incidental side effect of this SwitchElt-only diagnostic.
        """
        non_fallback = [rule for rule in self._rules if not rule.is_fallback]
        if len(non_fallback) < 2:
            return
        matching = [rule for rule in non_fallback if rule.condition.model.evaluate(None)]
        if len(matching) > 1:
            names = ', '.join(rule.label for rule in matching)
            logger.warning(f'Element {self}: rules {names} currently all match at the same '
                           'time - check for overlapping conditions')

    def to_dict_custom(self) -> dict[str, Any]:
        return {
            'manual_override_enabled': self._manual_enabled,
            'manual_override_target': self._manual_target.go_to,
            'rules': [rule.to_dict() for rule in self._rules if not rule.is_fallback],
            'fallback': self._fallback.to_dict(),
        }

    def from_dict_custom(self, dict_config: dict[str, Any]):
        for rule_dict in dict_config.pop('rules'):
            self.add_rule().from_dict(dict(rule_dict))
        self._fallback.from_dict(dict_config.pop('fallback'))
        self.manual_override_target = dict_config.pop('manual_override_target')
        self.manual_override_enabled = dict_config.pop('manual_override_enabled')

    def _eq(self, other: 'SwitchElt') -> bool:
        if not hasattr(other, 'rules'):
            return False
        if len(self.rules) != len(other.rules):
            return False
        if self.manual_override_enabled != other.manual_override_enabled:
            return False
        if self.manual_override_target != other.manual_override_target:
            return False
        return all(rule.eq(other_rule) for rule, other_rule in zip(self.rules, other.rules))

    def __repr__(self):
        n_rules = len(self._rules) - 1
        return f'{super().__repr__()} - {n_rules} rule(s) + fallback'

    # -- widget -----------------------------------------------------------------------------

    def _combo_index_to_value(self, index: int) -> Union[int, str]:
        """ Resolve the target combo's own selected index (0 = the synthetic "Continue" entry,
        1+ = real elements) back into a go_to value. """
        if index == 0:
            return CONTINUE
        return self.get_ids(without_ids=(self.id,), without_types=(AddButtonPlaceholder,))[index - 1]

    def _create_target_combo(self, target: Target, tooltip: str) -> ComboBox:
        combo = ComboBox()
        with QtCore.QSignalBlocker(combo):
            combo.addItem('Continue')
            combo.addItems(self.get_elts_as_str(without_ids=(self.id,),
                                                without_types=(AddButtonPlaceholder,)))
            value = target.go_to
            if value == CONTINUE:
                combo.setCurrentIndex(0)
            elif value is not None:
                combo.setCurrentText(str(self.get_elt_from_id(value)))
            else:
                # Leave genuinely unset rather than showing Qt's default index-0 selection,
                # which would misleadingly look like a target is already configured.
                combo.setCurrentIndex(-1)
            combo.currentIndexChanged.connect(
                lambda index: setattr(target, 'go_to', self._combo_index_to_value(index)))
            combo.setToolTip(tooltip)
        return combo

    def _build_rule_row(self, rule: Rule) -> WidgetWithToolbar:
        """ One self-contained row per rule - its own small container, so
        ConditionHolder.create_widget's fixed-index insertion doesn't collide across rules. """
        row = WidgetWithToolbar()
        if rule.is_fallback:
            row.add_widget_top(LabelWithFont('Fallback', isitalic=True))
        else:
            rule.condition.create_widget(row)
        row.add_widget_top(self._create_target_combo(
            rule.target,
            f'Go to this elt if {rule.label} matches' if not rule.is_fallback else
            'Go to this elt if no other rule matched'))
        if not rule.is_fallback and not self.rules_locked:
            row.add_action('remove_rule', 'Remove Rule', 'remove', tip='Remove this rule',
                           toolbar=row.toolbar)
            row.connect_action('remove_rule', lambda: self.remove_rule(rule.id))
        return row

    def _refresh_live_widget(self):
        """ Keep an already-open editor's rule rows in sync with self._rules - without this,
        a rule added/removed while the editor stayed open would only show up after closing
        and reopening it. """
        widget = self._live_rows_widget() if self._live_rows_widget is not None else None
        if widget is None:
            return
        layout = widget.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for rule in self._rules:
            layout.addWidget(self._build_rule_row(rule))

    def _on_add_rule_clicked(self):
        self.add_rule()

    def _on_manual_override_toggled(self, checked: bool):
        self.manual_override_enabled = checked

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        rows_widget = QtWidgets.QWidget()
        rows_layout = QtWidgets.QVBoxLayout()
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_widget.setLayout(rows_layout)
        for rule in self._rules:
            rows_layout.addWidget(self._build_rule_row(rule))
        base_widget.insert_widget(rows_widget, 1)
        self._live_rows_widget = weakref.ref(rows_widget)

        if not self.rules_locked:
            base_widget.add_action('add_rule', 'Add Rule', 'add_circle', tip='Add a new rule',
                                   toolbar=base_widget.toolbar)
            base_widget.connect_action('add_rule', self._on_add_rule_clicked)

        override_checkbox = QtWidgets.QCheckBox('Manual override')
        with QtCore.QSignalBlocker(override_checkbox):
            override_checkbox.setChecked(self._manual_enabled)
        override_checkbox.toggled.connect(self._on_manual_override_toggled)
        base_widget.add_widget_top(override_checkbox)
        base_widget.add_widget_top(self._create_target_combo(
            self._manual_target, 'Target used when manual override is active'))
        return base_widget

    def size_hint(self) -> QtCore.QSize:
        total_rows = sum(ConditionHolderBase.count_settings_rows(rule.condition.model.settings)
                         for rule in self._rules if not rule.is_fallback)
        return QtCore.QSize(220, 150 + total_rows * 25 + 60 * len(self._rules))
