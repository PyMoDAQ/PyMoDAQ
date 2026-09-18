"""
DRAFT — small debug/inspection widget for Workflow. Not wired into
CustomApp or any extension yet.

Shows the workflow's name and current state (live, via the existing
state_changed signal), a table of every registered state (cell
background color-coded: green = the active state, blue = reachable via
one currently-legal transition, red = not reachable right now), a table
of every defined (transition, from_state) pair -- one row per pair, not
per transition, so a transition legal from several states (e.g. 'stop'
from both PAUSED and RUNNING) never needs one cell to represent two
different states' statuses at once ('From' green iff that row's single
state is where we are, 'To' colored with the same green/blue/red status
as the States table, 'Legal now?' blue/red) -- and a table of whatever
TransitionBindings the caller hands it.

Deliberately the "cheap tier": tables, no graph/flowchart drawing. For
our graph sizes (4-6 states) an actual node-and-arrow rendering would be
a separate, bigger piece of work (QGraphicsView + a layout) -- not
needed for a first debug view.

This widget does NOT go looking for bindings itself: Workflow
deliberately doesn't track its own bindings (staying decoupled from the
UI layer), so the caller supplies whatever TransitionBindings it
already has, via the constructor or set_bindings().
"""
from collections.abc import Hashable, Iterable

from qtpy import QtGui, QtWidgets

from pymodaq_gui.managers.workflow_manager import TransitionBinding, Workflow

# Light tints, not solid colors, so default (usually black) text stays legible.
COLOR_ACTIVE = QtGui.QColor(190, 255, 190)      # the current state
COLOR_ACCESSIBLE = QtGui.QColor(195, 220, 255)  # reachable via a currently-legal transition
COLOR_UNALLOWED = QtGui.QColor(255, 200, 200)   # not reachable/legal right now


class WorkflowInspector(QtWidgets.QWidget):
    """ Read-only debug view of a Workflow's graph and (optionally) the
    TransitionBindings currently wired to it. """

    def __init__(self, workflow: Workflow, bindings: Iterable[TransitionBinding] = (),
                parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.workflow = workflow
        self._bindings: list[TransitionBinding] = list(bindings)

        self.setWindowTitle(f"Workflow inspector -- {workflow.name}")

        self._state_label = QtWidgets.QLabel()
        self._state_label.setStyleSheet('font-weight: bold; font-size: 12pt;')

        self._states_table = self._make_table(['State', 'Status'])
        self._transitions_table = self._make_table(['Transition', 'From', 'To', 'Guard', 'Legal now?'])
        self._bindings_table = self._make_table(['Transition', 'Widget', 'Object name', 'Bound?'])

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._state_label)
        layout.addWidget(QtWidgets.QLabel('States'))
        layout.addWidget(self._states_table)
        layout.addWidget(QtWidgets.QLabel('Transitions'))
        layout.addWidget(self._transitions_table)
        layout.addWidget(QtWidgets.QLabel('Bound widgets'))
        layout.addWidget(self._bindings_table)
        self.setLayout(layout)

        self.workflow.state_changed.connect(self.refresh)
        self.refresh()

    @staticmethod
    def _make_table(headers: list[str]) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        return table

    def set_bindings(self, bindings: Iterable[TransitionBinding]):
        """ Replace the list of bindings shown. The inspector never
        discovers these on its own -- hand it whatever bindings you
        currently have (e.g. the ones your extension created). """
        self._bindings = list(bindings)
        self.refresh()

    def refresh(self, *_):
        self._state_label.setText(f"State: {self.workflow.state}")
        statuses = self._state_statuses()
        self._refresh_states(statuses)
        self._refresh_transitions(statuses)
        self._refresh_bindings()

    def _state_statuses(self) -> dict[Hashable, tuple[str, QtGui.QColor]]:
        """ One (label, color) per registered state -- computed once per
        refresh() and shared between the States and Transitions tables,
        so both agree on what "accessible"/"unallowed" means. """
        current = self.workflow.state
        accessible = {transition.to_state for name, transition in self.workflow.transitions.items()
                      if self.workflow.can_trigger(name)}
        statuses = {}
        for state in self.workflow.states:
            if state == current:
                statuses[state] = ('active', COLOR_ACTIVE)
            elif state in accessible:
                statuses[state] = ('accessible', COLOR_ACCESSIBLE)
            else:
                statuses[state] = ('unallowed', COLOR_UNALLOWED)
        return statuses

    def _refresh_states(self, statuses: dict[Hashable, tuple[str, QtGui.QColor]]):
        table = self._states_table
        states = sorted(self.workflow.states, key=str)
        table.setRowCount(len(states))
        for row, state in enumerate(states):
            label, color = statuses[state]
            state_item = QtWidgets.QTableWidgetItem(str(state))
            status_item = QtWidgets.QTableWidgetItem(label)
            state_item.setBackground(color)
            status_item.setBackground(color)
            table.setItem(row, 0, state_item)
            table.setItem(row, 1, status_item)

    def _refresh_transitions(self, statuses: dict[Hashable, tuple[str, QtGui.QColor]]):
        """ One row per (transition, from_state) pair -- not one row per
        transition. A transition with several from_states (e.g. 'stop'
        legal from both PAUSED and RUNNING) would otherwise need one
        cell to represent two states with two different statuses at
        once (RUNNING active, PAUSED merely accessible) -- a single flat
        color can't express that, so each from_state gets its own row
        and its own unambiguous color instead. """
        current = self.workflow.state
        rows = [(name, transition, from_state)
               for name, transition in self.workflow.transitions.items()
               for from_state in sorted(transition.from_states, key=str)]

        table = self._transitions_table
        table.setRowCount(len(rows))
        for row, (name, transition, from_state) in enumerate(rows):
            legal_here = from_state == current and (transition.guard is None or transition.guard())

            name_item = QtWidgets.QTableWidgetItem(str(name))
            from_item = QtWidgets.QTableWidgetItem(str(from_state))
            to_item = QtWidgets.QTableWidgetItem(str(transition.to_state))
            guard_item = QtWidgets.QTableWidgetItem('yes' if transition.guard else '')
            legal_item = QtWidgets.QTableWidgetItem('yes' if legal_here else 'no')

            # 'From': this row's single state, colored only if it's where we are.
            if from_state == current:
                from_item.setBackground(COLOR_ACTIVE)
            # 'To': same status color as that state gets in the States table.
            to_item.setBackground(statuses[transition.to_state][1])
            legal_item.setBackground(COLOR_ACCESSIBLE if legal_here else COLOR_UNALLOWED)

            table.setItem(row, 0, name_item)
            table.setItem(row, 1, from_item)
            table.setItem(row, 2, to_item)
            table.setItem(row, 3, guard_item)
            table.setItem(row, 4, legal_item)

    def _refresh_bindings(self):
        table = self._bindings_table
        table.setRowCount(len(self._bindings))
        for row, binding in enumerate(self._bindings):
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(binding.transition)))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(type(binding.widget).__name__))
            # No dedicated name field on TransitionBinding -- objectName()
            # is Qt's own generic identifier, set by whoever created the
            # widget (e.g. action_manager.add_action(...).setObjectName(...)).
            table.setItem(row, 2, QtWidgets.QTableWidgetItem(binding.widget.objectName()))

            bound_item = QtWidgets.QTableWidgetItem('bound' if binding.is_bound else 'unbound')
            bound_item.setBackground(COLOR_ACTIVE if binding.is_bound else COLOR_UNALLOWED)
            table.setItem(row, 3, bound_item)
