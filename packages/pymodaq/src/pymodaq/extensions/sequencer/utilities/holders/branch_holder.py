from typing import TYPE_CHECKING

from qtpy import QtCore

from pymodaq_gui.utils.widgets.combo import ComboBox

from pymodaq.extensions.sequencer.utilities.element_factory import ElementError
from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq.extensions.sequencer.utilities.states import ValueTransition
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar

if TYPE_CHECKING:
    from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase

#: branch target sentinel meaning "wherever this element would go next anyway" - resolved
#: against elt.mstate.next_state (Sequence.recursive_connect_elts() sets it on every run), not
#: a specific id. A plain string, not an int, so it can never collide with a real element id
#: and round-trips through to_dict/from_dict with no special-casing needed.
CONTINUE = 'continue'


class BranchHolder:
    """ Holds N labeled branch targets (element ids) and N ValueTransitions wired into the
    owning element's mstate, one per declared outcome - generalizes ChoiceElt's True/False
    branching to an arbitrary outcome set.

    A holder: the owning element builds itself up by constructing one of these and keeping it
    as an attribute - `self.branches = BranchHolder(elt, branch_labels)` - whenever it chooses
    to, rather than inheriting this behavior. `branch_labels` (outcome value -> display label)
    is fixed for ChoiceElt's binary choice ({True: 'True', False: 'False'}) today; `rebuild()`
    lets it be resynced whenever an owner's outcome set can itself change shape.
    """

    def __init__(self, elt: 'SeqEltBase', branch_labels: dict):
        self.elt = elt
        self.branch_labels: dict = {}
        self._go_to: dict = {}
        self.value_transitions: dict = {}
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

        for branch in new_branches:
            # Give every branch a _go_to entry (even a None placeholder) as soon as it's
            # created, so go_to_true/go_to_false/to_dict_custom can always index it directly.
            self._go_to.setdefault(branch, None)
            transition = ValueTransition(self.elt.go_to_signal, branch, source_state=self.elt.mstate)
            # Plain addTransition(), not track_transition(): this is the element's own
            # permanent behavior, not per-run tree wiring, so it must survive
            # Sequence.recursive_disconnect_elts()'s per-run clear - which is exactly what
            # a transition added outside track_transition()/add_external_transition() does.
            self.elt.mstate.addTransition(transition)
            self.value_transitions[branch] = transition

    def set_go_to(self, branch, value: int | str):
        self._go_to[branch] = value
        if value == CONTINUE:
            self.value_transitions[branch].setTargetState(self.elt.mstate.next_state)
            return
        target_elt = self.elt.get_elt_from_id(value)
        if target_elt is not None:
            self.value_transitions[branch].update_target(target_elt.mstate)

    def _index_to_id(self, index: int) -> int:
        """ Resolve a combo box's selected index back into the corresponding element id """
        return self.elt.get_ids(without_ids=(self.elt.id,),
                                without_types=(AddButtonPlaceholder,))[index]

    def _combo_index_to_value(self, index: int) -> int | str:
        """ Resolve the target combo's own selected index (0 = the synthetic "Continue" entry,
        1+ = real elements) - not the same numbering as _index_to_id's, which the deprecated
        set_go_to_true/set_go_to_false still document as a plain index into get_ids(...), with
        no Continue offset. """
        if index == 0:
            return CONTINUE
        return self._index_to_id(index - 1)

    def _create_combo(self, branch, style_hook=None) -> ComboBox:
        combo = ComboBox()
        with QtCore.QSignalBlocker(combo):
            combo.addItem('Continue')
            combo.addItems(self.elt.get_elts_as_str(without_ids=(self.elt.id,),
                                                     without_types=(AddButtonPlaceholder,)))
            target_id = self._go_to.get(branch)
            if target_id == CONTINUE:
                combo.setCurrentIndex(0)
            elif target_id is not None:
                combo.setCurrentText(str(self.elt.get_elt_from_id(target_id)))
            else:
                # Leave genuinely unset rather than showing Qt's default index-0 selection,
                # which would misleadingly look like a target is already configured.
                combo.setCurrentIndex(-1)
            combo.currentIndexChanged.connect(
                lambda index, b=branch: self.set_go_to(b, self._combo_index_to_value(index)))
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

        A CONTINUE branch is always re-resolved, not just when still unset: what "continue"
        points at can change across runs if the tree was restructured, unlike a real element's
        target which doesn't move once resolved.

        Leaves a transition's target as None if the id doesn't resolve to a real element
        (e.g. never set, or its target was since removed) - check_set_is_valid's own
        targetState() is None check is what reports that as a proper ElementError.
        """
        for branch, transition in self.value_transitions.items():
            target_id = self._go_to.get(branch)
            if target_id == CONTINUE:
                transition.setTargetState(self.elt.mstate.next_state)
            elif transition.targetState() is None and target_id is not None:
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
