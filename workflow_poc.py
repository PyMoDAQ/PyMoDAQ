"""
Proof of principle for workflow_manager.py / standard_workflow.py --
NOT part of the codebase, a throwaway demo to see the whole thing work
end to end against something shaped like daq_scan's actual usage:

  - start / pause / resume / stop wired through the standard template
  - the STOPPING-vs-IDLE race fix: clicking Stop must NOT immediately
    re-enable Start -- only the worker actually finishing should.
  - stop_requested-style hook (via workflow.on('stop', ...)) firing
    separately from the final finished() re-enabling Start.
  - extending the graph beyond the template (an ERROR state) still
    binds fine with the generic bind_transition() primitive (two-line
    pattern: add_action + bind_transition, no dedicated wrapper).

Run: QT_QPA_PLATFORM=offscreen python3 workflow_poc.py
"""
import sys

sys.path.insert(0, '/mnt/c/Users/constant.schouder/Documents/PyMoDAQ/PyMoDAQ/packages/pymodaq_utils/src')
sys.path.insert(0, '/mnt/c/Users/constant.schouder/Documents/PyMoDAQ/PyMoDAQ/packages/pymodaq_gui/src')

from qtpy.QtWidgets import QApplication, QToolBar, QMenu

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.workflow_manager import bind_transition, action_name_for
from pymodaq_gui.managers.standard_workflow import (
    standard_workflow, bind_standard_workflow_actions, StandardTransitions)

app = QApplication.instance() or QApplication([])


def report(label, names=('scan_start', 'scan_stop', 'scan_pause')):
    a = action_manager
    print(f"\n-- {label} -- state={workflow.state}")
    for name in names:
        act = a.get_action(name)
        flags = []
        if act.isEnabled():
            flags.append('enabled')
        else:
            flags.append('disabled')
        if act.isCheckable():
            flags.append('checked' if act.isChecked() else 'unchecked')
        print(f"   {name:6s}: {', '.join(flags)}")


# ---- set up a minimal "app": one ActionManager, standing in for CustomApp ----
action_manager = ActionManager(toolbar=QToolBar(), menu=QMenu())
workflow = standard_workflow('scan')
bind_standard_workflow_actions(action_manager, workflow)

# ---- hooks a real extension would register, standing in for daq_scan's
#      start_scan/stop_scan logic -----------------------------------------
workflow.on(StandardTransitions.START, lambda old, new: print("  [hook] worker: starting acquisition"))
workflow.on(StandardTransitions.STOP, lambda old, new: print(f"  [hook] worker: told to stop (was {old})"))
workflow.on(StandardTransitions.PAUSE, lambda old, new: print("  [hook] worker: pausing"))
workflow.on(StandardTransitions.RESUME, lambda old, new: print("  [hook] worker: resuming"))
workflow.on(StandardTransitions.FINISHED, lambda old, new: print("  [hook] worker: fully wound down"))

report("initial")

print("\n>>> user clicks Start")
action_manager.get_action('scan_start').trigger()
report("after Start clicked")

print("\n>>> user clicks Pause")
action_manager.get_action('scan_pause').trigger()
report("after Pause clicked")

print("\n>>> user clicks Pause again (now resumes)")
action_manager.get_action('scan_pause').trigger()
report("after Resume clicked")

print("\n>>> user clicks Stop")
action_manager.get_action('scan_stop').trigger()
report("after Stop clicked -- Start must STILL be disabled, worker isn't done yet")

print("\n>>> ...later, the (simulated) worker thread actually reports done...")
workflow.trigger(StandardTransitions.FINISHED)
report("after worker reported finished -- NOW Start is re-enabled")

# ---- extending the graph beyond the template: an ERROR state ------------
print("\n\n=== extending beyond the template: an ERROR state ===")
workflow.add_transition('fail', ['RUNNING'], 'ERROR')
fail_action = action_manager.add_action(action_name_for(workflow, 'fail'), 'Mark failed')
bind_transition(fail_action, workflow, 'fail')
workflow.on('fail', lambda old, new: print("  [hook] worker: something went wrong!"))

action_manager.get_action('scan_start').trigger()
report("after Start (again)")

print("\n>>> a hardware error fires 'fail' (nobody edited workflow_manager.py for this)")
action_manager.get_action('scan_fail').trigger()
report("after fail -- start/stop/pause all correctly disabled from ERROR",
      names=('scan_start', 'scan_stop', 'scan_pause', 'scan_fail'))
