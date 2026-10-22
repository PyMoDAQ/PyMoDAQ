from typing import TYPE_CHECKING

from qtpy import QtCore

from pymodaq_gui.utils.widgets.combo import ComboBox

from pymodaq.extensions.sequencer.utilities.element_factory import ElementError
from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq.extensions.sequencer.utilities.states import ValueTransition
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar

if TYPE_CHECKING:
    from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase


class BranchHolder:
    """ Holds N labeled branch targets (element ids) and N ValueTransitions wired into the
    owning element's mstate, one per declared outcome - generalizes ChoiceElt's True/False
    branching to an arbitrary outcome set.

    Plain composition - `self.branches = BranchHolder(elt, branch_labels)` - not a mixin:
    construct it explicitly, whenever the owning element chooses to (there's no __init__-order
    puzzle to get right, unlike the mixin version this replaced). `branch_labels` (outcome
    value -> display label) is fixed for ChoiceElt's binary choice ({True: 'True',
    False: 'False'}) today; `rebuild()` lets it be resynced whenever an owner's outcome set
    can itself change shape.
    """

    def __init__(self, elt: 'SeqEltBase', branch_labels: dict):
        self.elt = elt
        self.branch_labels: dict = {}
        self._go_to: dict = {}
        self.value_transitions: dict = {}
        # Register on elt before rebuild() can touch elt.mstate: its first-ever access lazily
        # builds a CompositeState that stringifies elt via __repr__, which reads elt.branches -
        # so elt.branches must already exist by then, regardless of whether the caller
        # constructs this one-step (`elt.branches = BranchHolder(elt, labels)`) or in two steps.
        elt.branches = self
        self.rebuild(branch_labels)

    def rebuild(self, branch_labels: dict):
        """ Sync _go_to/value_transitions to `branch_labels`.

        Safe to call more than once: a transition/target for an outcome that's still present
        is left untouched (so its configured target survives); transitions for outcomes no
        longer present are torn down; new ValueTransitions are created for newly added
        outcomes.
        """
        self.branch_labels = dict(branch_labels)
        current = set(self.branch_labels)
        existing = set(self.value_transitions)
        new_branches = current - existing

        for branch in existing - current:
            transition = self.value_transitions.pop(branch)
            self.elt.mstate.removeTransition(transition)
            self._go_to.pop(branch, None)

        # Populate _go_to for every new branch *before* constructing any ValueTransition: the
        # first-ever access to elt.mstate (right below) lazily builds a CompositeState, whose
        # setup stringifies the element via __repr__ - which for ChoiceElt reads
        # _go_to - so _go_to must already have an entry (even a None placeholder) for every
        # branch before that first .mstate touch, not filled in partway through this same loop.
        for branch in new_branches:
            self._go_to.setdefault(branch, None)

        for branch in new_branches:
            transition = ValueTransition(self.elt.go_to_signal, branch, source_state=self.elt.mstate)
            self.elt.mstate.addTransition(transition)
            self.value_transitions[branch] = transition

    def set_go_to(self, branch, value: int):
        self._go_to[branch] = value
        target_elt = self.elt.get_elt_from_id(value)
        if target_elt is not None:
            self.value_transitions[branch].update_target(target_elt.mstate)

    def _index_to_id(self, index: int) -> int:
        """ Resolve a combo box's selected index back into the corresponding element id """
        return self.elt.get_ids(without_ids=(self.elt.id,),
                                without_types=(AddButtonPlaceholder,))[index]

    def _create_combo(self, branch, style_hook=None) -> ComboBox:
        combo = ComboBox()
        with QtCore.QSignalBlocker(combo):
            combo.addItems(self.elt.get_elts_as_str(without_ids=(self.elt.id,),
                                                     without_types=(AddButtonPlaceholder,)))
            target_id = self._go_to.get(branch)
            if target_id is not None:
                combo.setCurrentText(str(self.elt.get_elt_from_id(target_id)))
            else:
                # Leave genuinely unset rather than showing Qt's default index-0 selection,
                # which would misleadingly look like a target is already configured.
                combo.setCurrentIndex(-1)
            combo.currentIndexChanged.connect(
                lambda index, b=branch: self.set_go_to(b, self._index_to_id(index)))
            combo.setToolTip(f'Go to this elt if {self.branch_labels[branch]}')
        if style_hook is not None:
            style_hook(combo, branch)
        return combo

    def create_widgets(self, base_widget: WidgetWithToolbar, style_hook=None):
        """ Add one target combo per current branch (in branch_labels' iteration order) to
        base_widget. `style_hook(combo, branch)`, if given, can style each combo (e.g.
        ChoiceElt's green/red). """
        for branch in self.branch_labels:
            base_widget.add_widget_top(self._create_combo(branch, style_hook))

    def update_target_states(self):
        """ Resolve any not-yet-resolved branch target now that the tree may have changed.

        Leaves a transition's target as None if the id doesn't resolve to a real element
        (e.g. never set, or its target was since removed) - check_set_is_valid's own
        targetState() is None check is what reports that as a proper ElementError.
        """
        for branch, transition in self.value_transitions.items():
            if transition.targetState() is None:
                target_id = self._go_to.get(branch)
                if target_id is not None:
                    target_elt = self.elt.get_elt_from_id(target_id)
                    if target_elt is not None:
                        transition.setTargetState(target_elt.mstate)

    def check_set_is_valid(self):
        """ Raises ElementError naming whichever branch(es) have no resolvable target. """
        self.update_target_states()
        for branch, transition in self.value_transitions.items():
            if transition.targetState() is None:
                raise ElementError(
                    f'Element {self.elt}: has no existing {self.branch_labels[branch]} value target state')
