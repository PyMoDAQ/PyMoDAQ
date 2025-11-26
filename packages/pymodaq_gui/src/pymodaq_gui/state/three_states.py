from hatch.cli import self

from pymodaq_gui.utils.utils import mkQApp
from qtpy import QtWidgets, QtCore

from qtpy.QtCore import QObject
from qtpy.QtWidgets import QWidget, QLabel, QPushButton
from qtpy.QtStateMachine import QStateMachine, QState, QFinalState


class App(QObject):

    def __init__(self):
        super().__init__()

        self.setup_ui()
        self.setup_machine()
        self.start()
        self.show()

    def setup_ui(self):
        self.widget = QWidget()
        self.label = QLabel()
        self.push = QPushButton('Push Me')

        self.widget.setLayout(QtWidgets.QVBoxLayout())
        self.widget.layout().addWidget(self.label)
        self.widget.layout().addWidget(self.push)

    def setup_machine(self):
        self.machine = QStateMachine()
        state_1 = QState()
        state_2 = QState()
        state_3 = QState()

        state_1.addTransition(self.push, 'clicked', state_2)
        state_2.addTransition(self.push, 'clicked', state_3)
        state_3.addTransition(self.push, 'clicked', state_1)

        self.machine.addState(state_1)
        self.machine.addState(state_2)
        self.machine.addState(state_3)
        self.machine.setInitialState(state_1)

    def start(self):
        self.machine.start()
        
    def show(self):
        self.widget.show()


def main():
    app = mkQApp('StateMachine')


