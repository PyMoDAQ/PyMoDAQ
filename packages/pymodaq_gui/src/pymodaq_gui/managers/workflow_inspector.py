"""
DRAFT — small debug/inspection widget for Workflow. Not wired into
CustomApp or any extension yet.

Live state, plus three tables: states (color-coded green=active/
blue=accessible/red=unallowed), transitions (one row per
(transition, from_state) pair, so a transition legal from several
states never needs one cell to cover two statuses), and whatever
Bindings the caller hands it (Workflow doesn't track its own bindings,
so this widget can't discover them itself -- see set_bindings()).

Cheap tier: tables, no graph/flowchart drawing.
"""
from collections.abc import Hashable, Iterable

from qtpy import QtGui, QtWidgets

from pymodaq_gui.managers.workflow_manager import Binding, Workflow

# Light tints, always paired with COLOR_TEXT below -- the app's own default text color can't
# be relied on (it's white in dark mode, unreadable on a light tint), so every colored cell
# gets an explicit foreground, not just a background.
COLOR_ACTIVE = QtGui.QColor(190, 255, 190)      # the current state
COLOR_ACCESSIBLE = QtGui.QColor(195, 220, 255)  # reachable via a currently-legal transition
COLOR_UNALLOWED = QtGui.QColor(255, 200, 200)   # not reachable/legal right now
COLOR_TEXT = QtGui.QColor('black')


def _colorize(item: QtWidgets.QTableWidgetItem, color: QtGui.QColor):
    """ Set both background and a legible foreground -- COLOR_TEXT stays right against every
    color above since they're all light tints by design, unlike the app's default text color,
    which flips light/dark with the theme. """
    item.setBackground(color)
    item.setForeground(COLOR_TEXT)


class WorkflowInspector(QtWidgets.QWidget):
    """ Read-only debug view of a Workflow's graph and (optionally) the
    Bindings currently wired to it. """

    def __init__(self, workflow: Workflow, bindings: Iterable[Binding] = (),
                parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.workflow = workflow
        self._bindings: list[Binding] = list(bindings)

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

    def set_bindings(self, bindings: Iterable[Binding]):
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
        """ One (label, color) per state, shared between the States and
        Transitions tables so both agree. """
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
            _colorize(state_item, color)
            _colorize(status_item, color)
            table.setItem(row, 0, state_item)
            table.setItem(row, 1, status_item)

    def _refresh_transitions(self, statuses: dict[Hashable, tuple[str, QtGui.QColor]]):
        """ One row per (transition, from_state) pair -- see module
        docstring for why. """
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
                _colorize(from_item, COLOR_ACTIVE)
            # 'To': same status color as that state gets in the States table.
            _colorize(to_item, statuses[transition.to_state][1])
            _colorize(legal_item, COLOR_ACCESSIBLE if legal_here else COLOR_UNALLOWED)

            table.setItem(row, 0, name_item)
            table.setItem(row, 1, from_item)
            table.setItem(row, 2, to_item)
            table.setItem(row, 3, guard_item)
            table.setItem(row, 4, legal_item)

    def _refresh_bindings(self):
        table = self._bindings_table
        table.setRowCount(len(self._bindings))
        for row, binding in enumerate(self._bindings):
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(binding.label)))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(type(binding.widget).__name__))
            # No dedicated name field on Binding -- objectName() is Qt's
            # own generic identifier, set by whoever created the widget
            # (e.g. action_manager.add_action(...).setObjectName(...)).
            table.setItem(row, 2, QtWidgets.QTableWidgetItem(binding.widget.objectName()))

            bound_item = QtWidgets.QTableWidgetItem('bound' if binding.is_bound else 'unbound')
            _colorize(bound_item, COLOR_ACTIVE if binding.is_bound else COLOR_UNALLOWED)
            table.setItem(row, 3, bound_item)
