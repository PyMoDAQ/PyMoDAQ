"""
DRAFT — not wired into CustomApp yet.

Generic finite-state-machine engine, no knowledge of any particular
workflow shape (see standard_workflow.py for the concrete IDLE/RUNNING/...
template).

* ``Workflow``: states/transitions are data (add_state/add_transition),
  not hardcoded. trigger() runs hooks (on/on_enter/on_exit) then emits
  `state_changed`. A transition's optional `guard` can refuse it outright
  (checked by can_trigger/trigger); on_enter/on_exit run unconditionally
  once a transition has already happened -- they can't veto.
* ``bind_sync(widget, workflow, sync_slot, ..., signal_name=, click_slot=)``:
  runs `sync_slot` on every state_changed/revalidated (plus once now),
  optionally wired to a click. ``bind_transition()``/``bind_enabled()``
  (+ ``bind_enabled_to_states()``/``bind_enabled_to_transition()``) are
  canned `sync_slot`s (setEnabled) over the same primitive. All return a
  ``Binding`` (``.resync()``/``.unbind()``).
* ``Workflow.revalidate()``: resyncs every binding without an actual
  transition -- for when a guard's external input changes on its own.

``WorkflowManager`` is just a named registry of Workflow instances.
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
        """ Every registered state (read-only), for introspection/UI
        tooling -- build the graph through add_state/add_transition. """
        return frozenset(self._states)

    @property
    def transitions(self) -> dict[str, Transition]:
        """ The transition table (read-only), name -> Transition. """
        return dict(self._transitions)

    def add_state(self, state: Hashable, default: bool = False):
        """ Register a state. The first one added becomes the default
        (starting) state, unless `default=True` on a later one.
        `state` may not be None (reserved as the "no state yet"
        sentinel -- see __init__). """
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
        landing on `to_state`. Implicitly registers any new state.
        `guard`, if given, is an extra precondition (checked by
        can_trigger/trigger) that can refuse the transition outright. """
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
        """ OR: at least one of `names` is legal from the current state
        (e.g. what a pause/resume toggle wants for its enabled state). """
        return any(self._is_legal(name) for name in names)

    def can_trigger_all(self, *names: str) -> bool:
        """ AND: every one of `names` is legal from the current state. """
        return all(self._is_legal(name) for name in names)

    def can_trigger(self, *names: str, how: str = 'any') -> bool:
        """ can_trigger_any (how='any', default) or can_trigger_all
        (how='all') -- for when the combinator is itself a variable. """
        if how == 'any':
            return self.can_trigger_any(*names)
        if how == 'all':
            return self.can_trigger_all(*names)
        raise ValueError(f"how must be 'any' or 'all', got {how!r}")

    def trigger(self, name: str) -> bool:
        """ Attempt the named transition; returns False (and logs) if
        illegal -- never raises. Runs, in order: the transition's own
        hooks, old state's exit hooks, commits `self.state`, new state's
        enter hooks, then emits state_changed -- so exit/transition
        hooks still see the state being left if they read `self.state`
        directly, and a hook that raises never leaves `self.state`
        pointing past a transition whose later hooks never ran. """
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
        """ Trigger the first of `names` that's currently legal; False if
        none are (e.g. a pause/resume toggle:
        `workflow.trigger_any('resume', 'pause')`). """
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
        """ Read-only snapshot of on(transition_name, ...) callbacks, for
        introspection/UI tooling -- use on/off to drive hooks. """
        return list(self._transition_hooks.get(transition_name, ()))

    def enter_hooks(self, state: Hashable) -> list[Callable]:
        """ Read-only snapshot of on_enter(state, ...) callbacks. """
        return list(self._enter_hooks.get(state, ()))

    def exit_hooks(self, state: Hashable) -> list[Callable]:
        """ Read-only snapshot of on_exit(state, ...) callbacks. """
        return list(self._exit_hooks.get(state, ()))

    def revalidate(self):
        """ Resync every binding on this workflow without an actual
        transition -- for when a guard's external input changed on its
        own (e.g. a 'start' guard reading some flag state_changed knows
        nothing about). Emits `revalidated`, not `state_changed`. """
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
    """ ActionManager short_name for `transition` on `workflow`: plain
    ('start'/'stop'/...) for the default workflow, namespaced
    ('seq1_start'...) otherwise so several can share one ActionManager. """
    if workflow.name == DEFAULT_WORKFLOW_NAME:
        return str(transition)
    return f'{workflow.name}_{transition}'


class Binding:
    """ Handle returned by bind_sync() and friends: `.resync()`/`.unbind()`,
    auto-unbound on the widget's `destroyed` signal too. `label` is for
    introspection/UI tooling (WorkflowInspector) only, not load-bearing;
    use `widget.objectName()` for a human-readable widget identity. """

    def __init__(self, widget: QtCore.QObject, workflow: Workflow, label: str, sync_slot: Callable,
                signal_name: str | None = None, click_slot: Callable | None = None):
        self.widget = widget
        self.workflow = workflow
        self.label = label
        self._sync_slot = sync_slot
        self._signal_name = signal_name
        self._click_slot = click_slot
        self._bound = True

    @property
    def is_bound(self) -> bool:
        return self._bound

    def resync(self):
        """ Recompute the enabled sync right now, rather than waiting for
        the next state_changed -- for a guard whose external input can
        change without a transition. No-op once unbound. """
        if self._bound:
            self._sync_slot()

    def unbind(self):
        """ Disconnect all connections (click, if any; state_changed;
        revalidated). Safe to call more than once. """
        if not self._bound:
            return
        if self._signal_name is not None:
            with contextlib.suppress(TypeError, RuntimeError):
                getattr(self.widget, self._signal_name).disconnect(self._click_slot)
        with contextlib.suppress(TypeError, RuntimeError):
            self.workflow.state_changed.disconnect(self._sync_slot)
        with contextlib.suppress(TypeError, RuntimeError):
            self.workflow.revalidated.disconnect(self._sync_slot)
        self._bound = False


def bind_sync(widget: QtCore.QObject, workflow: Workflow, sync_slot: Callable,
             label: str = '', signal_name: str | None = None,
             click_slot: Callable | None = None) -> Binding:
    """ Run `sync_slot(*_)` on every state_changed/revalidated (plus once
    now); if `signal_name`/`click_slot` are given, also connect
    `click_slot` on that signal first. `sync_slot` can do anything, e.g.
    standard_workflow.bind_pause_action():
    ``bind_sync(action, workflow, sync_slot, 'pause/resume', 'triggered', click_slot)``. """
    if signal_name is not None:
        getattr(widget, signal_name).connect(click_slot)
    workflow.state_changed.connect(sync_slot)
    workflow.revalidated.connect(sync_slot)
    sync_slot()

    binding = Binding(widget, workflow, label, sync_slot, signal_name, click_slot)
    destroyed_signal = getattr(widget, 'destroyed', None)
    if destroyed_signal is not None:
        destroyed_signal.connect(binding.unbind)
    return binding


def bind_transition(widget: QtCore.QObject, workflow: Workflow, transition: str,
                    signal_name: str = 'triggered', click_slot: Callable | None = None) -> Binding:
    """ Click -> trigger(transition) by default; enabled kept synced to
    can_trigger(transition). `signal_name`: 'triggered' for QAction,
    'clicked' for QPushButton/... `click_slot`, if given, runs first (e.g.
    daq_scan's 'start' running set_scan()) and trigger(transition) is then
    called automatically -- unless `click_slot` returns exactly `False`, in
    which case the transition is skipped (e.g. set_scan() validation
    failed). """
    if click_slot is None:
        click_slot = lambda *_: workflow.trigger(transition)
    else:
        user_slot = click_slot

        def click_slot(*args):
            if user_slot(*args) is not False:
                workflow.trigger(transition)

    def sync_slot(*_):
        widget.setEnabled(workflow.can_trigger(transition))

    return bind_sync(widget, workflow, sync_slot, transition, signal_name, click_slot)


def bind_enabled(widget: QtCore.QObject, workflow: Workflow, predicate: Callable[[], bool],
                 label: str = '') -> Binding:
    """ widget.setEnabled() kept synced to `predicate()`, no click. E.g.
    daq_scan's 'ini_positions': `lambda: workflow.state == IDLE and
    scanner.actuators == modules_manager.actuators`. If `predicate`
    depends on something external, call workflow.revalidate() when it
    changes. """
    def sync_slot(*_):
        widget.setEnabled(predicate())

    return bind_sync(widget, workflow, sync_slot, label)


def bind_enabled_to_states(widget: QtCore.QObject, workflow: Workflow,
                           states: Iterable[Hashable]) -> Binding:
    """ bind_enabled() with `workflow.state in states` as the predicate. """
    states = frozenset(states)
    return bind_enabled(widget, workflow, lambda: workflow.state in states,
                        '|'.join(str(s) for s in states))


def bind_enabled_to_transition(widget: QtCore.QObject, workflow: Workflow, transition: str) -> Binding:
    """ bind_enabled() with `workflow.can_trigger(transition)` as the predicate. """
    return bind_enabled(widget, workflow, lambda: workflow.can_trigger(transition), transition)
