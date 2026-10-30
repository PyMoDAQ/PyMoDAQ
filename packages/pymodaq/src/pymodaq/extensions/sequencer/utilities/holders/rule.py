from typing import Any, Optional, TYPE_CHECKING, Union

from pymodaq.extensions.sequencer.utilities.element_factory import ElementError
from pymodaq.extensions.sequencer.utilities.holders.condition_holder import ConditionHolder
from pymodaq.extensions.sequencer.utilities.states import ValueTransition

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase

#: target sentinel meaning "wherever this element would go next anyway" - resolved against
#: elt.mstate.next_state (Sequence.recursive_connect_elts() sets it on every run), not a
#: specific id. A plain string, not an int, so it can never collide with a real element id or
#: a rule id, and round-trips through to_dict/from_dict with no special-casing needed.
CONTINUE = 'continue'

#: go_to_signal value reserved for a SwitchElt's manual override - never collides with a real
#: Rule id, which is always >= 0.
MANUAL_OVERRIDE_ID = -1


class Target:
    """ One resolvable branch target (an element id, or CONTINUE) backed by one
    ValueTransition - the single piece of behavior shared by every Rule's target and a
    SwitchElt's element-level manual override target: resolving CONTINUE against
    owner_elt.mstate.next_state, tolerating a not-yet-resolvable id, and re-resolving a
    not-yet-resolved target lazily (but always re-resolving CONTINUE, since what "continue"
    points at can change if the tree is restructured between runs).
    """

    def __init__(self, owner_elt: 'SeqEltBase', transition: ValueTransition):
        self.owner_elt = owner_elt
        self.transition = transition
        self._go_to: Union[int, str, None] = None

    @property
    def go_to(self) -> Union[int, str, None]:
        return self._go_to

    @go_to.setter
    def go_to(self, value: Union[int, str]):
        self._go_to = value
        self.update()

    def update(self):
        """ Re-resolve against the current tree - call whenever the tree may have changed
        since this target was last set (a fresh element construction, a restart, a tree
        edit...). """
        if self._go_to == CONTINUE:
            self.transition.setTargetState(self.owner_elt.mstate.next_state)
        elif self.transition.targetState() is None and self._go_to is not None:
            target_elt = self.owner_elt.get_elt_from_id(self._go_to)
            if target_elt is not None:
                self.transition.setTargetState(target_elt.mstate)

    def check_is_valid(self, label: str):
        """ Raises ElementError naming `label` if this target doesn't currently resolve. """
        self.update()
        if self.transition.targetState() is None:
            raise ElementError(
                f'Element {self.owner_elt}: has no existing {label} value target state')


class Rule:
    """ One (condition, target) pair in a SwitchElt's rule list: a Condition (a ConditionHolder
    -managed ChoiceModelBase instance, exactly the family ChoiceElt already uses) plus a
    Target, under a stable id assigned at construction and used as this rule's
    go_to_signal/ValueTransition discriminant.

    Presents itself as the `elt` a ConditionHolder/ChoiceModelBase expects (`.dashboard`,
    `.modules_manager`, `__repr__`) rather than sharing the owning SwitchElt across every
    rule's ConditionHolder: ConditionHolderBase.__init__ publishes a fresh ModulesManager onto
    whatever `elt` it's given (`elt.modules_manager = ...`), so sharing one `elt` across N
    rules would make each rule's lazily-constructed model capture whichever sibling's
    ModulesManager happened to be the current one on the shared owner at that moment, instead
    of its own.
    """

    def __init__(self, owner_elt: 'SeqEltBase', rule_id: int, is_fallback: bool = False,
                label: Optional[str] = None):
        self.owner_elt = owner_elt
        self.id = rule_id
        self.is_fallback = is_fallback
        #: used in error/tooltip text; ChoiceElt overrides this to 'True'/'False' on its two
        #: fixed rules to keep its existing error-message wording unaffected by this redesign.
        self.label = label or ('fallback' if is_fallback else f'rule {rule_id}')

        self.condition = ConditionHolder(
            self, combo_tooltip='Always matches (fallback)' if is_fallback else 'Rule condition')
        if is_fallback:
            # Pinned, not just defaulted: guarantees every SwitchElt evaluation resolves to
            # exactly one target (the fallback always matches), independent of
            # ConditionHolder.default_model_name.
            self.condition.model = 'true'

        transition = ValueTransition(owner_elt.go_to_signal, rule_id, source_state=owner_elt.mstate)
        owner_elt.mstate.addTransition(transition)
        self.target = Target(owner_elt, transition)

    @property
    def dashboard(self) -> 'DashBoard':
        return self.owner_elt.dashboard

    @property
    def transition(self) -> ValueTransition:
        return self.target.transition

    @property
    def go_to(self) -> Union[int, str, None]:
        return self.target.go_to

    @go_to.setter
    def go_to(self, value: Union[int, str]):
        self.target.go_to = value

    def update_target_state(self):
        self.target.update()

    def check_set_is_valid(self):
        self.target.check_is_valid(self.label)
        self.condition.check_set_is_valid()

    def to_dict(self) -> dict[str, Any]:
        dict_config = {'go_to': self.go_to}
        dict_config.update(self.condition.to_dict())
        return dict_config

    def from_dict(self, dict_config: dict[str, Any]):
        self.go_to = dict_config.pop('go_to')
        self.condition.from_dict(dict_config)

    def eq(self, other: 'Rule') -> bool:
        if self.is_fallback != other.is_fallback:
            return False
        if self.go_to != other.go_to:
            return False
        return self.condition.eq(other.condition)

    def __repr__(self):
        return f'{self.owner_elt} - {self.label}'
