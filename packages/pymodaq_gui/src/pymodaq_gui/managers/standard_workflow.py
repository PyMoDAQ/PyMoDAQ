"""
DRAFT — not wired into CustomApp yet.

The concrete IDLE/RUNNING/PAUSED/STOPPING template built on
workflow_manager.py's generic engine, for daq_scan/daq_logger/sequencer.

* ``standard_workflow()``: returns a Workflow already populated with
  that graph. Extend it (add_state/add_transition) for more, e.g. ERROR.
* UI binding, three composable pieces: `bind_transition()` for start/stop
  (optional `click_slot` for a caller with extra work, e.g. daq_scan's
  'start' running set_scan()); `bind_pause_action()` merges PAUSE+RESUME
  into one checkable toggle (can't be expressed with bind_transition()
  alone); `bind_standard_workflow_actions()` composes all three,
  returning {'start', 'stop', 'pause'} Bindings.

Still open: LOG isn't modeled (config flag, not lifecycle); multi-workflow
apps -- one shared Actions menu, or one submenu per workflow?
"""

from collections.abc import Callable

from qtpy import QtGui, QtWidgets

from pymodaq_utils.enums import StrEnum

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.workflow_manager import (
    Workflow,
    DEFAULT_WORKFLOW_NAME,
    Binding,
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


class StandardStates(StrEnum):
    """The four lifecycle states standard_workflow() builds."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"


def standard_workflow(name: str = DEFAULT_WORKFLOW_NAME) -> Workflow:
    """The IDLE/RUNNING/PAUSED/STOPPING graph that daq_scan/daq_logger/
    sequencer all need, ready to use as-is."""
    IDLE, RUNNING, PAUSED, STOPPING = StandardStates.IDLE, StandardStates.RUNNING, \
        StandardStates.PAUSED, StandardStates.STOPPING

    workflow = Workflow(name)
    workflow.add_state(IDLE, default=True)
    workflow.add_transition(StandardTransitions.START, [IDLE], RUNNING)
    workflow.add_transition(StandardTransitions.PAUSE, [RUNNING], PAUSED)
    workflow.add_transition(StandardTransitions.RESUME, [PAUSED], RUNNING)
    workflow.add_transition(StandardTransitions.STOP, [RUNNING, PAUSED], STOPPING)
    workflow.add_transition(StandardTransitions.FINISHED, [STOPPING, RUNNING], IDLE)
    return workflow


def bind_pause_action(action_manager: ActionManager, workflow: Workflow,
                      toolbar: QtWidgets.QToolBar = None,
                      menu: QtWidgets.QMenu = None,
                      on_pause_resume: Callable | None = None) -> Binding:
    """ PAUSE+RESUME merged into one checkable toggle button. Exposed
    separately so a caller hand-wiring 'start' itself can still reuse
    this piece for pause. `on_pause_resume`, if given, replaces the bare
    trigger_any(RESUME, PAUSE) on click -- same idea as bind_transition()'s
    `click_slot`, so a caller's own pause_scan()-style method (used e.g.
    by a programmatic do_scan()) is the single place that logic lives,
    not duplicated between the button and that method. """
    pause_name = action_name_for(workflow, StandardTransitions.PAUSE)
    action = action_manager.add_action(pause_name, f"Pause {workflow.name}", "pause_circle",
                                       f"Pause/resume {workflow.name}", checkable=True,
                                       toolbar=toolbar, menu=menu)
    action.setObjectName(pause_name)

    def click_slot(*_):
        if on_pause_resume is not None:
            on_pause_resume()
        else:
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

    return finalize_binding(action, workflow, 'pause/resume', sync_slot, 'triggered', click_slot)


def bind_standard_workflow_actions(action_manager: ActionManager, workflow: Workflow,
                                   toolbar: QtWidgets.QToolBar = None,
                                   menu: QtWidgets.QMenu = None,
                                   on_start: Callable | None = None,
                                   on_stop: Callable | None = None,
                                   on_pause_resume: Callable | None = None,
                                   start_icon_color: QtGui.QColor | bytes | str | None = None,
                                   stop_icon_color: QtGui.QColor | bytes | str | None = None,
                                   ) -> dict[str, Binding]:
    """ Creates the Start/Stop/Pause actions and binds all three.
    `on_start`/`on_stop` replace the bare trigger() on click (see
    bind_transition()'s `click_slot`) -- omit for the fire-and-forget
    case. Returns {'start': ..., 'stop': ..., 'pause': ...}. """
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

    pause_binding = bind_pause_action(action_manager, workflow, toolbar=toolbar, menu=menu,
                                      on_pause_resume=on_pause_resume)

    return {'start': start_binding, 'stop': stop_binding, 'pause': pause_binding}
