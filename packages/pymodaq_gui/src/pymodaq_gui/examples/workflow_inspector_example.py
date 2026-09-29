"""
Example: WorkflowInspector live demo -- NOT part of the codebase.

Shows a real toolbar (Start/Stop/Pause + an extra 'Mark failed' action
bolted onto the standard template) next to a live WorkflowInspector.
Click the toolbar actions and watch the inspector's tables update.

Also binds the standard template's existing 'finished' transition
(STOPPING -> IDLE) to its own button -- without it, clicking Stop leaves
you stuck in STOPPING forever with no toolbar action able to bring you
back to IDLE, so Start would only ever work once.

Run (needs a real display -- no QT_QPA_PLATFORM=offscreen this time):
    python3 workflow_inspector_example.py
"""
import sys
from qtpy.QtWidgets import QApplication, QMainWindow, QToolBar, QWidget, QHBoxLayout, QLabel, QVBoxLayout

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.workflow_manager import bind_transition, action_name_for
from pymodaq_gui.managers.standard_workflow import (
    standard_workflow, bind_standard_workflow_actions, StandardTransitions)
from pymodaq_gui.managers.workflow_inspector import (
    WorkflowInspector, COLOR_ACTIVE, COLOR_ACCESSIBLE, COLOR_UNALLOWED)


def make_legend() -> QWidget:
    """ The inspector's tables are light tints with default (theme) text color on top --
    readable in light mode, but low-contrast if the theme's default text is light too (dark
    mode). Rather than hardcoding a text color into the widget itself (which would then fight
    the app's own theme the other way), spell out what each color means here instead. """
    legend = QWidget()
    layout = QHBoxLayout()
    layout.setContentsMargins(4, 4, 4, 4)
    for color, text in ((COLOR_ACTIVE, 'active state'),
                       (COLOR_ACCESSIBLE, 'accessible (legal transition available)'),
                       (COLOR_UNALLOWED, 'unallowed (not reachable right now)')):
        swatch = QLabel()
        swatch.setFixedSize(16, 16)
        swatch.setStyleSheet(f'background-color: {color.name()}; border: 1px solid gray;')
        layout.addWidget(swatch)
        layout.addWidget(QLabel(text))
        layout.addSpacing(12)
    layout.addStretch()
    legend.setLayout(layout)
    return legend


app = QApplication.instance() or QApplication(sys.argv)

mainwindow = QMainWindow()
mainwindow.setWindowTitle('Workflow inspector example')

toolbar = QToolBar('Scan')
mainwindow.addToolBar(toolbar)
action_manager = ActionManager(toolbar=toolbar)

workflow = standard_workflow('scan')
bindings = bind_standard_workflow_actions(action_manager, workflow)

# Extend the graph beyond the template, same as the earlier
# proof-of-principle -- bind_standard_workflow_actions never had to
# know this exists. Two-line pattern (add_action + bind_transition), no
# dedicated wrapper -- see workflow_manager.py's module docstring for why.
workflow.add_transition('fail', ['RUNNING'], 'ERROR')
fail_action = action_manager.add_action(action_name_for(workflow, 'fail'), 'Mark failed')
bindings['fail'] = bind_transition(fail_action, workflow, 'fail')

# The template already defines 'finished' (STOPPING -> IDLE) -- it's
# just never bound to a button by bind_standard_workflow_actions(),
# since nothing in the real app is expected to click it (it's meant to
# be triggered by a worker reporting completion, see the earlier
# workflow_poc.py). Bound here only so this toy example is actually
# usable interactively without writing code between runs.
toolbar.addSeparator()
finished_action = action_manager.add_action(action_name_for(workflow, StandardTransitions.FINISHED),
                                            'Finished (simulate worker done)')
bindings['finished'] = bind_transition(finished_action, workflow, StandardTransitions.FINISHED)

inspector = WorkflowInspector(workflow, bindings=list(bindings.values()))

central = QWidget()
central_layout = QVBoxLayout()
central_layout.addWidget(make_legend())
central_layout.addWidget(inspector)
central.setLayout(central_layout)

mainwindow.setCentralWidget(central)
mainwindow.resize(700, 460)
mainwindow.show()

sys.exit(app.exec())
