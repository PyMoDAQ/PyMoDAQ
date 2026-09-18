"""
DRAFT — not wired into CustomApp yet, for discussion.

The example/template built on top of workflow_manager.py's generic
engine: the IDLE/RUNNING/PAUSED/STOPPING graph with start/pause/resume/
stop/finished transitions that daq_scan/daq_logger/sequencer actually
need, plus its UI counterpart.

* ``standard_workflow()``: just a function that returns a Workflow
  already populated with that graph. Callers never see
  add_state/add_transition. One needing more (e.g. an ERROR state)
  takes the returned object and extends its graph with a couple more
  add_state/add_transition calls directly -- no subclassing.

* UI binding is composed from three pieces, each usable on its own:
  - `start`/`stop`: plain `action_manager.add_action(...)` +
    `bind_transition()`, the latter now taking an optional `click_slot`
    (see workflow_manager.py) for a caller with extra requirements on
    one of them -- e.g. daq_scan.py, where 'start' must run set_scan()
    (real side effects, can veto entering RUNNING) before it's safe to
    enter RUNNING, so its click can't go straight to
    `workflow.trigger('start')`.
  - `bind_pause_action()`: the one piece that can't be done with
    `bind_transition()` alone -- merging PAUSE+RESUME into a single
    checkable toggle button, a UI convention tied to this particular
    3-button pattern (nothing generic could infer that two transitions
    should collapse into one control; that's a choice only this
    template's author can make). Exposed separately so a caller with
    its own `on_start`/`on_stop` can still reuse this piece instead of
    duplicating it.
  - `bind_standard_workflow_actions()`: convenience composing all
    three, now for the general case, not just the fire-and-forget one
    -- `on_start`/`on_stop` forward straight to bind_transition()'s
    `click_slot`, so a caller whose start/stop need real work no longer
    has to hand-assemble action creation + bind_enabled_to_transition()
    by hand; it only has to when it wants a *different* action-creation
    shape than this one (a different toolbar/menu split per action,
    say). Returns a dict of the three TransitionBindings ({'start':
    ..., 'stop': ..., 'pause': ...}), e.g. to pass to a
    WorkflowInspector or to unbind() individually later.

Still open:
* LOG is not modeled here (config flag, not lifecycle) -- deferred.
* For multi-workflow apps, is one shared "Actions" menu right, or one
  submenu per workflow?
"""

from collections.abc import Callable

from qtpy import QtGui, QtWidgets

from pymodaq_utils.enums import StrEnum

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.workflow_manager import (
    Workflow,
    DEFAULT_WORKFLOW_NAME,
    TransitionBinding,
    action_name_for,
    bind_transition,
    finalize_binding,
)


class StandardTransitions(StrEnum):
    """Naming convention shared between standard_workflow() and this
    module's binders."""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    FINISHED = "finished"


def standard_workflow(name: str = DEFAULT_WORKFLOW_NAME) -> Workflow:
    """The IDLE/RUNNING/PAUSED/STOPPING graph that daq_scan/daq_logger/
    sequencer all need, ready to use as-is.

    STOPPING exists to model a real async gap: 'stop' only *requests* a
    stop, it doesn't confirm one happened. Whoever wires this up MUST
    call trigger('finished') once that confirmation actually arrives
    (e.g. daq_scan's thread_status on "Scan_done") -- if nothing ever
    does, the workflow is stuck in STOPPING forever, START stays
    illegal, and there's no timeout or other self-correction. If a given
    workflow's stop is genuinely synchronous (no worker thread to wait
    on), trigger('stop') immediately followed by trigger('finished') is
    fine -- but don't skip 'finished' and expect 'stop' to reach IDLE by
    itself; it doesn't, on purpose."""
    IDLE, RUNNING, PAUSED, STOPPING = "IDLE", "RUNNING", "PAUSED", "STOPPING"

    workflow = Workflow(name)
    workflow.add_state(IDLE, default=True)
    workflow.add_transition(StandardTransitions.START, [IDLE], RUNNING)
    workflow.add_transition(StandardTransitions.PAUSE, [RUNNING], PAUSED)
    workflow.add_transition(StandardTransitions.RESUME, [PAUSED], RUNNING)
    workflow.add_transition(StandardTransitions.STOP, [RUNNING, PAUSED], STOPPING)
    # Legal from RUNNING too, not just STOPPING: a worker finishing on its own (all steps
    # done, a timeout, a step failure) never goes through 'stop' at all -- it confirms
    # completion directly from RUNNING, with no stop request on the app side. Generic to any
    # acquisition-style workflow, not daq_scan-specific (found by porting daq_scan, which had
    # to extend this itself before this became the template default).
    workflow.add_transition(StandardTransitions.FINISHED, [STOPPING, RUNNING], IDLE)
    return workflow


def bind_pause_action(action_manager: ActionManager, workflow: Workflow,
                      toolbar: QtWidgets.QToolBar = None,
                      menu: QtWidgets.QMenu = None) -> TransitionBinding:
    """ The one piece of the standard 3-button pattern that
    bind_transition() alone can't express: PAUSE+RESUME merged into a
    single checkable toggle button. Exposed separately (not just
    inlined in bind_standard_workflow_actions()) so a caller that needs
    to hand-wire 'start' itself can still reuse this piece for pause,
    without duplicating the toggle logic. """
    pause_name = action_name_for(workflow, StandardTransitions.PAUSE)
    action = action_manager.add_action(pause_name, f"Pause {workflow.name}", "pause_circle",
                                       f"Pause/resume {workflow.name}", checkable=True,
                                       toolbar=toolbar, menu=menu)
    action.setObjectName(pause_name)

    def click_slot(*_):
        workflow.trigger_any(StandardTransitions.RESUME, StandardTransitions.PAUSE)

    action.triggered.connect(click_slot)

    def sync_slot(*_):
        # If can resume or pause, then pause is enabled
        action_manager.set_action_enabled(
            pause_name, workflow.can_trigger_any(StandardTransitions.PAUSE, StandardTransitions.RESUME)
        )
        # If can resume, then pause is checked
        action_manager.set_action_checked(pause_name, workflow.can_trigger(StandardTransitions.RESUME))

    workflow.state_changed.connect(sync_slot)
    workflow.revalidated.connect(sync_slot)
    sync_slot()

    return finalize_binding(action, workflow, 'pause/resume', 'triggered', click_slot, sync_slot)


def bind_standard_workflow_actions(action_manager: ActionManager, workflow: Workflow,
                                   toolbar: QtWidgets.QToolBar = None,
                                   menu: QtWidgets.QMenu = None,
                                   on_start: Callable | None = None,
                                   on_stop: Callable | None = None,
                                   start_icon_color: QtGui.QColor | bytes | str | None = None,
                                   stop_icon_color: QtGui.QColor | bytes | str | None = None,
                                   ) -> dict[str, TransitionBinding]:
    """ Convenience composing the three pieces above: creates the Start/
    Stop/Pause actions and binds all three. `on_start`/`on_stop`, if
    given, replace the bare trigger('start')/trigger('stop') on click
    (bind_transition()'s `click_slot` -- see its docstring) for a
    workflow whose start/stop need real work first, not just a bare
    trigger(). Omit them for the fire-and-forget case (nothing to run
    besides the transition itself). Returns {'start': ..., 'stop': ...,
    'pause': ...}. """
    start_name = action_name_for(workflow, StandardTransitions.START)
    start_action = action_manager.add_action(start_name, f"Start {workflow.name}", "motion_play",
                                             f"Start {workflow.name}", toolbar=toolbar, menu=menu,
                                             icon_color=start_icon_color)
    start_action.setObjectName(start_name)
    start_binding = bind_transition(start_action, workflow, StandardTransitions.START,
                                    click_slot=on_start)

    stop_name = action_name_for(workflow, StandardTransitions.STOP)
    stop_action = action_manager.add_action(stop_name, f"Stop {workflow.name}", "stop_circle",
                                            f"Stop {workflow.name}", toolbar=toolbar, menu=menu,
                                            icon_color=stop_icon_color)
    stop_action.setObjectName(stop_name)
    stop_binding = bind_transition(stop_action, workflow, StandardTransitions.STOP,
                                   click_slot=on_stop)

    pause_binding = bind_pause_action(action_manager, workflow, toolbar=toolbar, menu=menu)

    return {'start': start_binding, 'stop': stop_binding, 'pause': pause_binding}
