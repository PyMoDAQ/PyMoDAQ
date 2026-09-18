"""
DRAFT — not wired into CustomApp yet, for discussion.

The core engine, with zero knowledge of any particular workflow shape
(no IDLE/RUNNING/start/stop here at all -- see standard_workflow.py for
that). Two pieces:

* ``Workflow``: a generic finite-state-machine. States and transitions
  are DATA (add_state/add_transition), not hardcoded in the class.
  Triggering a transition (trigger()) runs whatever callbacks were
  registered on it (on()) plus state-entry/exit callbacks (on_enter/
  on_exit) -- each receiving (old_state, new_state) -- then emits the
  one generic `state_changed` signal. Nobody has to subclass or edit
  this module to add a new state or a new hook; they call
  add_state/add_transition/on on their own Workflow instance.

  A transition can also carry an optional `guard` callable
  (add_transition(..., guard=...)): consulted by can_trigger/trigger
  alongside state membership. Use this when a transition must be
  refused outright rather than attempted and rolled back -- e.g. a
  validated 'start' that must never actually reach RUNNING if real
  validation (hardware checks, etc.) fails, rather than blipping into
  RUNNING and back out.

* ``bind_transition()``: wires an already-existing QAction/QWidget (any
  signal_name, default 'triggered'; 'clicked' for a QPushButton/
  QToolButton) to a transition -- no ActionManager involved at all.
  Click -> trigger(transition) by default; enabled synced from
  can_trigger(transition) either way. Works for ANY widget/Workflow/
  transition name, whatever the widget's origin. Deliberately no
  separate "creates the action for you" wrapper -- the caller creates
  the widget itself (e.g. via
  `action_manager.add_action(action_name_for(workflow, transition), ...)`)
  and calls this on it.

  `click_slot`, if given, replaces the bare trigger(transition) -- for
  a transition gated behind real validation (daq_scan's 'start' running
  set_scan(), which has side effects and can veto entering RUNNING), so
  the click can't go straight to trigger(). The callback decides
  if/when to call trigger(transition) itself; the enabled-sync is
  identical either way. This is the *same* primitive for the
  fire-and-forget case and the "needs real work first" case, not two
  separate ones to pick between (an earlier version of this module
  split those into bind_transition() vs. hand-assembling
  connect_action()+bind_enabled_to_transition() -- collapsed back into
  one function once every real caller turned out to need the complex
  case for at least one of its transitions).
  `action_name_for()` computes the ActionManager short_name to create
  an action under (namespaced for non-default workflows) -- a plain
  helper, not tied to bind_transition() at all.

  The returned ``TransitionBinding`` holds the two connections it made
  (click -> trigger, state_changed -> resync) and offers ``.unbind()``
  to disconnect both -- for anything created/destroyed dynamically (a
  Sequencer adding/removing per-sequence actions, say), so neither side
  is kept alive forever by a live connection into the other. A
  permanent widget (daq_scan's Start/Stop/Pause) never needs to call it.
  It has no name/label field: `binding.widget` already *is* the
  object, and a human-readable identifier is Qt's own generic
  `widget.setObjectName(...)`/`.objectName()`, not something specific
  to this module.

* ``bind_enabled_to_states()``: the state-membership analog of
  bind_transition(), for a widget that doesn't itself trigger any
  transition but still needs graying out based on current state (e.g.
  daq_scan's 'ini_positions', only enabled while IDLE). No click side
  at all -- just widget.setEnabled() kept synced to
  `workflow.state in states`. Returns a ``StateBinding`` (same
  destroyed-triggered auto-unbind idiom as TransitionBinding, but
  without a click connection to hold, so it's its own small class
  rather than reusing TransitionBinding with unused fields).

* ``bind_enabled_to_transition()``: the transition-legality counterpart
  to bind_enabled_to_states() -- widget.setEnabled() kept synced to
  `workflow.can_trigger(transition)`, no click side, for a widget whose
  click can't go straight to trigger(transition) via bind_transition()
  (e.g. daq_scan's 'start', which must run side-effecting validation
  first and only call trigger('start') itself once that succeeds).
  Together with bind_transition() (click + this same sync, for the
  common no-extra-requirements case), that rounds out the 2x2 of
  {transition legality, state membership} x {with a click, sync only}.
  Returns a ``TransitionEnabledBinding``.

* ``Workflow.revalidate()``: emits a second signal, `revalidated`
  (distinct from `state_changed` -- nothing actually transitioned, so
  there's no old_state/new_state to report), that every bind_*
  primitive above also resyncs on. For when a guard's external input
  changes without a workflow transition (daq_scan's 'start' guard reads
  experiment_manager.entry_applied, which the workflow has no way to
  know changed on its own): call workflow.revalidate() once from
  wherever that external event is already handled, and every binding on
  the workflow resyncs -- not just the one guarded transition's, so a
  second guarded transition added later needs no extra wiring at the
  call site that changed the external condition. TransitionBinding,
  StateBinding and TransitionEnabledBinding also each offer their own
  ``.resync()``, for resyncing just one binding without touching the
  rest of the workflow.

``WorkflowManager`` is just a named registry of Workflow instances, no
Qt-action dependency.

Considered pyqtgraph.flowchart for the engine: it's a dataflow graph
(nodes with input/output terminals, wired together, each running a
process() that transforms data -- closer to a lightweight
visual-programming/pipeline editor). Different problem (data
transformation, not lifecycle state), and would drag in a whole
node-library/terminal-wiring UI system for something expressible in a
couple dozen lines. Not reused.

Not using QStateMachine either: ties transitions to the Qt event loop
(QSignalTransition fires through Qt's event system, not a plain
synchronous call), which we don't want for headless, event-loop-free
testability, and a guard there means digging into event.arguments()
rather than a plain predicate callable. (Its own QtStateMachine module
being a separate PySide6 wheel -- pyside6-addons, not pyside6-essentials
-- is a packaging detail, not a real availability gap: pymodaq's own
pyproject.toml already depends on the full `pyside6` metapackage, so
this was never actually a blocker for real installs, only for a sandbox
that happened to have only PySide6-Essentials.)

What QStateMachine *does* give up front that this module doesn't:
composite/hierarchical states (a state containing its own sub-states,
used by sequencer/utilities/states.py to model nested per-element
execution) and native signal-to-transition wiring
(QState.addTransition(signal, target), generic over any Qt signal, not
just widget clicks). Neither has an equivalent here yet -- a workflow
needing real hierarchy (sequencer, maybe) is not automatically a good
fit for this module as-is.
"""
import contextlib
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Iterator
from typing import NamedTuple

from qtpy import QtCore

from pymodaq_utils.logger import get_module_name, set_logger

logger = set_logger(get_module_name(__file__))

DEFAULT_WORKFLOW_NAME = 'main'


class Transition(NamedTuple):
    from_states: frozenset[Hashable]
    to_state: Hashable
    guard: Callable[[], bool] | None = None


class Workflow(QtCore.QObject):
    """ Generic state-machine engine: states/transitions are data, hooks
    are registered, nothing is hardcoded. See module docstring. """

    state_changed = QtCore.Signal(object, object)  # old_state, new_state
    revalidated = QtCore.Signal()  # no transition occurred; a guard's external input may have

    def __init__(self, name: str = DEFAULT_WORKFLOW_NAME):
        super().__init__()
        self.name = name
        self._states: set[Hashable] = set()
        self._state: Hashable | None = None
        self._transitions: dict[str, Transition] = {}
        self._transition_hooks: dict[str, list[Callable]] = defaultdict(list)
        self._enter_hooks: dict[Hashable, list[Callable]] = defaultdict(list)
        self._exit_hooks: dict[Hashable, list[Callable]] = defaultdict(list)

    @property
    def state(self) -> Hashable | None:
        return self._state

    @property
    def states(self) -> frozenset[Hashable]:
        """ Read-only view of every registered state, for introspection/
        UI tooling (e.g. a debug inspector) -- not meant for building the
        graph through, use add_state/add_transition for that. """
        return frozenset(self._states)

    @property
    def transitions(self) -> dict[str, Transition]:
        """ Read-only view of the transition table (name -> Transition),
        for introspection/UI tooling -- same caveat as `states`. """
        return dict(self._transitions)

    def add_state(self, state: Hashable, default: bool = False):
        """ Register a state. The first state ever added becomes the
        default state unless `default=True` is passed explicitly for a
        later one -- i.e. the state the workflow starts in, and the one
        a caller can fall back to (e.g. after an error) by re-adding it
        with `default=True`.

        `state` may not be None: None is the sentinel this class uses
        internally for "no state assigned yet" (see __init__), so
        allowing it as a real state would break that check as well as
        the from_states membership test in _is_legal. """
        if state is None:
            raise ValueError("None cannot be used as a state (reserved as the "
                             "'no state yet' sentinel)")
        is_new = state not in self._states
        self._states.add(state)
        if self._state is None or default:
            self._state = state
        return is_new

    def add_transition(self, name: str, from_states: Iterable[Hashable], to_state: Hashable,
                       guard: Callable[[], bool] | None = None):
        """ Define a named transition: legal from any of `from_states`,
        always landing on `to_state`. Adding a transition implicitly
        registers any state in it that wasn't added yet.

        `guard`, if given, is an extra precondition consulted by
        can_trigger/trigger alongside state membership -- e.g. real
        validation that must pass before the transition is allowed, not
        just "are we in the right state". Use this when a transition
        must be refused outright rather than merely attempted and rolled
        back (a validated 'start' should never actually reach RUNNING if
        the validation fails, not blip into RUNNING and back out). """
        if not name:
            raise ValueError(f"Transition name must be non-empty, got {name!r}")
        from_states = frozenset(from_states)
        for state in (*from_states, to_state):
            self.add_state(state)
        self._transitions[name] = Transition(from_states, to_state, guard)

    def _is_legal(self, name: str) -> bool:
        transition = self._transitions.get(name)
        if transition is None or self._state not in transition.from_states:
            return False
        return transition.guard is None or transition.guard()

    def can_trigger_any(self, *names: str) -> bool:
        """ OR: whether at least one of `names` is a legal transition from
        the current state. A single name asks about that one transition;
        several ask "can any of these happen right now" -- e.g. what a
        control covering more than one transition (a pause/resume toggle)
        wants for its enabled state, without spelling out the `or`. """
        return any(self._is_legal(name) for name in names)

    def can_trigger_all(self, *names: str) -> bool:
        """ AND: whether every one of `names` is a legal transition from
        the current state. Rarely what you want for a single button tied
        to one of several transitions (that's can_trigger_any's OR) --
        this is for a condition that genuinely needs several transitions
        simultaneously available, not "any one of these will do". """
        return all(self._is_legal(name) for name in names)

    def can_trigger(self, *names: str, how: str = 'any') -> bool:
        """ General entry point for when the combinator itself is a
        variable rather than known at the call site: how='any' (default)
        delegates to can_trigger_any, how='all' to can_trigger_all. Also
        the natural spelling for the common single-name check, where the
        combinator is moot. Prefer calling can_trigger_any/can_trigger_all
        directly whenever you already know which one you mean. """
        if how == 'any':
            return self.can_trigger_any(*names)
        if how == 'all':
            return self.can_trigger_all(*names)
        raise ValueError(f"how must be 'any' or 'all', got {how!r}")

    def trigger(self, name: str) -> bool:
        """ Attempt the named transition. Returns False (and logs) if
        `name` is unknown or illegal from the current state -- never
        raises, so a stray double-click can't crash anything. Runs, in
        order: the transition's own hooks, the old state's exit hooks,
        the new state's enter hooks, then emits state_changed. Every
        hook receives (old_state, new_state), same as state_changed --
        e.g. a 'stop' hook can tell whether it's leaving RUNNING or
        PAUSED, instead of only knowing "stop happened".

        `self.state` is only committed to `new_state` right before the
        enter hooks run -- i.e. after the transition and exit hooks --
        so a transition/exit hook that reads `self.state` directly
        (instead of using the old_state/new_state it's handed) still
        sees the state it's actually leaving, not the one it's headed
        to. It also means a hook that raises never leaves `self.state`
        pointing at a transition whose enter hooks/state_changed never
        ran. """
        if not self.can_trigger(name):
            logger.warning(f"Workflow '{self.name}': transition '{name}' not "
                           f"available from state {self._state!r}, ignored")
            return False

        old_state = self._state
        new_state = self._transitions[name].to_state

        for callback in self._transition_hooks.get(name, ()):
            callback(old_state, new_state)
        for callback in self._exit_hooks.get(old_state, ()):
            callback(old_state, new_state)

        self._state = new_state

        for callback in self._enter_hooks.get(new_state, ()):
            callback(old_state, new_state)

        self.state_changed.emit(old_state, new_state)
        return True

    def trigger_any(self, *names: str) -> bool:
        """ Attempt each of `names` in order, triggering (and returning
        True for) the first one that's currently legal; False if none
        are. The natural counterpart to can_trigger_any() for "one
        control, several candidate transitions, do whichever applies"
        -- e.g. a pause/resume toggle button:
        `workflow.trigger_any('resume', 'pause')` instead of spelling
        out `trigger('resume' if can_trigger('resume') else 'pause')`. """
        for name in names:
            if self.can_trigger(name):
                return self.trigger(name)
        return False

    def on(self, transition_name: str, callback: Callable):
        """ Run `callback(old_state, new_state)` whenever `transition_name`
        is successfully triggered (before state_changed is emitted). """
        self._transition_hooks[transition_name].append(callback)

    def on_enter(self, state: Hashable, callback: Callable):
        """ Run `callback(old_state, new_state)` whenever `state` is
        entered, from any transition. """
        self._enter_hooks[state].append(callback)

    def on_exit(self, state: Hashable, callback: Callable):
        """ Run `callback(old_state, new_state)` whenever `state` is left,
        via any transition. """
        self._exit_hooks[state].append(callback)

    def off(self, transition_name: str, callback: Callable):
        """ Undo a prior on(transition_name, callback). Raises ValueError
        if that exact callback isn't currently registered on that
        transition -- same contract as list.remove(). """
        self._transition_hooks[transition_name].remove(callback)

    def off_enter(self, state: Hashable, callback: Callable):
        """ Undo a prior on_enter(state, callback). Raises ValueError if
        that exact callback isn't currently registered on that state. """
        self._enter_hooks[state].remove(callback)

    def off_exit(self, state: Hashable, callback: Callable):
        """ Undo a prior on_exit(state, callback). Raises ValueError if
        that exact callback isn't currently registered on that state. """
        self._exit_hooks[state].remove(callback)

    def transition_hooks(self, transition_name: str) -> list[Callable]:
        """ Read-only snapshot of the callbacks registered via
        on(transition_name, ...), for introspection/UI tooling (e.g. a
        debug inspector) -- not meant for driving hooks through, use
        on/off for that. """
        return list(self._transition_hooks.get(transition_name, ()))

    def enter_hooks(self, state: Hashable) -> list[Callable]:
        """ Read-only snapshot of the callbacks registered via
        on_enter(state, ...) -- same caveat as transition_hooks(). """
        return list(self._enter_hooks.get(state, ()))

    def exit_hooks(self, state: Hashable) -> list[Callable]:
        """ Read-only snapshot of the callbacks registered via
        on_exit(state, ...) -- same caveat as transition_hooks(). """
        return list(self._exit_hooks.get(state, ()))

    def revalidate(self):
        """ Ask every bind_transition()/bind_enabled_to_states()/
        bind_enabled_to_transition() binding on this workflow to
        recompute its sync right now, even though no transition
        happened -- for when a guard's external input changed on its
        own (e.g. daq_scan's 'start' guard reads
        experiment_manager.entry_applied, which state_changed knows
        nothing about). Emits `revalidated`, never `state_changed` --
        nothing here actually transitioned, so old_state/new_state
        would be meaningless (and misleading to anything logging
        "transitioned from X to Y" off state_changed). """
        self.revalidated.emit()


class WorkflowManager:
    """ A named registry of Workflow instances. No Qt-action dependency. """

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}

    def add_workflow(self, workflow: Workflow) -> Workflow:
        """ Register `workflow` under its own .name. """
        if workflow.name in self._workflows:
            raise ValueError(f"A workflow named '{workflow.name}' already exists")
        self._workflows[workflow.name] = workflow
        return workflow

    def __getitem__(self, name: str) -> Workflow:
        return self._workflows[name]

    def __iter__(self) -> Iterator[Workflow]:
        return iter(self._workflows.values())

    def __len__(self) -> int:
        return len(self._workflows)

    @property
    def main(self) -> Workflow | None:
        """ Convenience accessor for the single-workflow case. """
        return self._workflows.get(DEFAULT_WORKFLOW_NAME)


def action_name_for(workflow: Workflow, transition: str) -> str:
    """ The short_name an action for `transition` on `workflow` is/should
    be registered under on an ActionManager. The default-named workflow
    keeps plain names ('start'/'stop'/...) so single-workflow call sites
    read naturally; any other workflow gets namespaced ones
    ('seq1_start'...) so several can share one ActionManager without
    collisions. """
    if workflow.name == DEFAULT_WORKFLOW_NAME:
        return str(transition)
    return f'{workflow.name}_{transition}'


class TransitionBinding:
    """ Handle returned by bind_transition(), letting the wiring be
    undone later: disconnects both the widget's click signal and the
    workflow's state_changed sync, so neither side keeps the other
    reachable forever through a live connection. Needed for anything
    created/destroyed dynamically (e.g. Sequencer adding/removing
    per-sequence actions) -- a permanent widget (daq_scan's Start/Stop/
    Pause, say) never needs to call unbind() at all.

    No name/label field on purpose: `widget` already *is* the object;
    use `widget.objectName()` (set it via `widget.setObjectName(...)`
    when you create the widget) if you want a human-readable identifier
    -- that's Qt's own generic mechanism, not something bind_transition()
    should reinvent. """

    def __init__(self, widget: QtCore.QObject, workflow: Workflow, transition: str,
                signal_name: str, click_slot: Callable, sync_slot: Callable):
        self.widget = widget
        self.workflow = workflow
        self.transition = transition
        self._signal_name = signal_name
        self._click_slot = click_slot
        self._sync_slot = sync_slot
        self._bound = True

    @property
    def is_bound(self) -> bool:
        return self._bound

    def resync(self):
        """ Recompute the enabled sync right now, rather than waiting for the
        next state_changed. Needed when the widget's correct enabled state
        can change for a reason the workflow itself doesn't emit a signal
        for -- e.g. a transition's guard depending on some external
        condition (daq_scan's 'start', gated on an experiment entry being
        applied) that can flip without any workflow transition happening at
        all. No-op once unbound. """
        if self._bound:
            self._sync_slot()

    def unbind(self):
        """ Disconnect all connections (click, state_changed sync,
        revalidated sync). Safe to call more than once. """
        if not self._bound:
            return
        with contextlib.suppress(TypeError, RuntimeError):
            getattr(self.widget, self._signal_name).disconnect(self._click_slot)
        with contextlib.suppress(TypeError, RuntimeError):
            self.workflow.state_changed.disconnect(self._sync_slot)
        with contextlib.suppress(TypeError, RuntimeError):
            self.workflow.revalidated.disconnect(self._sync_slot)
        self._bound = False


def finalize_binding(widget: QtCore.QObject, workflow: Workflow, transition: str,
                     signal_name: str, click_slot: Callable, sync_slot: Callable) -> TransitionBinding:
    """ Shared tail end of building a TransitionBinding: wrap the
    connections already made (`click_slot` on `signal_name`, `sync_slot`
    on `workflow.state_changed`) into a TransitionBinding, and auto-
    unbind if `widget` is destroyed without an explicit unbind() call --
    otherwise the next state_changed would call setEnabled() on a dead
    C++ object (mirrors pymodaq_gui.utils.widget_sync.core's
    widget.destroyed-based cleanup). Used by bind_transition() below and
    by standard_workflow.bind_pause_action(), which can't use
    bind_transition() itself (its click behavior picks between two
    transitions at click time, not one fixed one) but still needs this
    same bookkeeping rather than reimplementing it by hand. """
    binding = TransitionBinding(widget, workflow, transition, signal_name, click_slot, sync_slot)
    destroyed_signal = getattr(widget, 'destroyed', None)
    if destroyed_signal is not None:
        destroyed_signal.connect(binding.unbind)
    return binding


def bind_transition(widget: QtCore.QObject, workflow: Workflow, transition: str,
                    signal_name: str = 'triggered', click_slot: Callable | None = None) -> TransitionBinding:
    """ Wire an already-existing QAction/QWidget/anything directly to
    `transition` on `workflow` -- no ActionManager involved at all.
    `signal_name` (default 'triggered', right for QAction) is the
    click-like signal to connect -- 'clicked' for QPushButton/
    QToolButton, or whatever else exposes a no-argument-friendly signal
    and setEnabled(). widget.setEnabled() kept synced to
    workflow.can_trigger(transition) for as long as both objects live,
    or until the returned TransitionBinding.unbind() is called -- on
    every state_changed, and on every revalidate() too (for a guard
    whose external input can change without a transition).

    `click_slot`, if given, replaces the default bare `trigger(transition)`
    on click -- use this when the transition's real behavior needs more
    than a bare trigger(), e.g. validation that can veto entering the
    target state (daq_scan's 'start', which runs set_scan() -- real side
    effects -- before it's safe to enter RUNNING, so the click can't go
    straight to trigger('start')). The callback is then responsible for
    calling workflow.trigger(transition) itself, if/when it decides to;
    the enabled-sync (can_trigger(transition), on state_changed/
    revalidated) is exactly the same either way -- this is the same
    single primitive for both the simple and the complex case, not two
    different ones to choose between.

    Create the widget yourself first -- e.g.
    `action_manager.add_action(action_name_for(workflow, transition), ...)`
    for an ActionManager-owned action, or plain `QPushButton(...)` for
    anything else -- then call this on it. """
    if click_slot is None:
        click_slot = lambda *_: workflow.trigger(transition)
    getattr(widget, signal_name).connect(click_slot)

    def sync_slot(*_):
        widget.setEnabled(workflow.can_trigger(transition))

    workflow.state_changed.connect(sync_slot)
    workflow.revalidated.connect(sync_slot)
    sync_slot()

    return finalize_binding(widget, workflow, transition, signal_name, click_slot, sync_slot)


class StateBinding:
    """ Handle returned by bind_enabled_to_states(). The state-membership
    analog of TransitionBinding, for a widget that doesn't trigger any
    transition -- so there's no click connection to hold, only
    widget.setEnabled() kept synced to `workflow.state in states`.
    Same ``.unbind()``/auto-unbind-on-destroyed contract as
    TransitionBinding, just without the click half. """

    def __init__(self, widget: QtCore.QObject, workflow: Workflow, states: frozenset[Hashable],
                sync_slot: Callable):
        self.widget = widget
        self.workflow = workflow
        self.states = states
        self._sync_slot = sync_slot
        self._bound = True

    @property
    def is_bound(self) -> bool:
        return self._bound

    def resync(self):
        """ Recompute the enabled sync right now -- see TransitionBinding.resync()
        for why this exists. No-op once unbound. """
        if self._bound:
            self._sync_slot()

    def unbind(self):
        """ Disconnect the state_changed and revalidated syncs. Safe to call
        more than once. """
        if not self._bound:
            return
        with contextlib.suppress(TypeError, RuntimeError):
            self.workflow.state_changed.disconnect(self._sync_slot)
        with contextlib.suppress(TypeError, RuntimeError):
            self.workflow.revalidated.disconnect(self._sync_slot)
        self._bound = False


def bind_enabled_to_states(widget: QtCore.QObject, workflow: Workflow,
                           states: Iterable[Hashable]) -> StateBinding:
    """ Keep widget.setEnabled() synced to `workflow.state in states`, for a
    widget that doesn't itself trigger a transition -- e.g. daq_scan's
    'ini_positions' action, which should just be enabled while IDLE
    rather than being wired to any particular transition. The
    state-membership counterpart to bind_transition() (which syncs to
    can_trigger(transition) instead). Resynced on revalidate() too, same
    as every other bind_* primitive, even though state membership alone
    never actually depends on anything external -- so a single
    workflow.revalidate() call refreshes every binding on the workflow
    uniformly, not just the guard-dependent ones. """
    states = frozenset(states)

    def sync_slot(*_):
        widget.setEnabled(workflow.state in states)

    workflow.state_changed.connect(sync_slot)
    workflow.revalidated.connect(sync_slot)
    sync_slot()

    binding = StateBinding(widget, workflow, states, sync_slot)
    destroyed_signal = getattr(widget, 'destroyed', None)
    if destroyed_signal is not None:
        destroyed_signal.connect(binding.unbind)
    return binding


class TransitionEnabledBinding:
    """ Handle returned by bind_enabled_to_transition(). Same shape as
    StateBinding (no click side, just widget.setEnabled() kept synced --
    here to `workflow.can_trigger(transition)` instead of state
    membership) -- a separate class rather than reusing StateBinding with
    an unused/empty `.states`, same reasoning as TransitionBinding vs
    StateBinding not sharing one class despite both wrapping a widget +
    workflow + sync_slot. """

    def __init__(self, widget: QtCore.QObject, workflow: Workflow, transition: str,
                sync_slot: Callable):
        self.widget = widget
        self.workflow = workflow
        self.transition = transition
        self._sync_slot = sync_slot
        self._bound = True

    @property
    def is_bound(self) -> bool:
        return self._bound

    def resync(self):
        """ Recompute the enabled sync right now -- see TransitionBinding.resync()
        for why this exists. No-op once unbound. """
        if self._bound:
            self._sync_slot()

    def unbind(self):
        """ Disconnect the state_changed and revalidated syncs. Safe to call
        more than once. """
        if not self._bound:
            return
        with contextlib.suppress(TypeError, RuntimeError):
            self.workflow.state_changed.disconnect(self._sync_slot)
        with contextlib.suppress(TypeError, RuntimeError):
            self.workflow.revalidated.disconnect(self._sync_slot)
        self._bound = False


def bind_enabled_to_transition(widget: QtCore.QObject, workflow: Workflow,
                               transition: str) -> TransitionEnabledBinding:
    """ Keep widget.setEnabled() synced to `workflow.can_trigger(transition)`,
    for a widget whose click can't just go straight to trigger(transition)
    via bind_transition() -- e.g. daq_scan's 'start', which must run
    set_scan()'s (side-effecting) validation first, and only call
    workflow.trigger('start') itself once that succeeds. The
    transition-legality counterpart to bind_enabled_to_states() (which
    syncs to state membership instead) -- together with bind_transition()
    (click + this same sync, for the common case with no extra click
    requirements), that's the full 2x2: {transition legality, state
    membership} x {with a click, sync only}.

    A guard can depend on something external that doesn't itself fire
    state_changed (daq_scan's 'start' guard checks
    experiment_manager.entry_applied) -- resynced on the whole
    workflow's revalidate() as well as state_changed, so the usual way
    to handle that is workflow.revalidate() from wherever the external
    event is already handled, which refreshes every binding on the
    workflow at once. The returned binding's own .resync() is still
    there for resyncing just this one widget without touching the rest. """
    def sync_slot(*_):
        widget.setEnabled(workflow.can_trigger(transition))

    workflow.state_changed.connect(sync_slot)
    workflow.revalidated.connect(sync_slot)
    sync_slot()

    binding = TransitionEnabledBinding(widget, workflow, transition, sync_slot)
    destroyed_signal = getattr(widget, 'destroyed', None)
    if destroyed_signal is not None:
        destroyed_signal.connect(binding.unbind)
    return binding
