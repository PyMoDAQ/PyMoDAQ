from os import environ
environ['QT_API'] = 'pyside6'

from pymodaq_gui.utils.utils import mkQApp
from qtpy import QtWidgets, QtCore, QtGui

from qtpy.QtCore import QObject
from qtpy.QtWidgets import QWidget, QLabel, QPushButton
from qtpy.QtStateMachine import QStateMachine, QState, QFinalState


class QStatePrint(QState):

    def onEntry(self, event, /):
        print("I'm entering S3")

    def onExit(self, event, /):
        print("I'm exiting S3")


class App(QObject):

    def __init__(self):
        super().__init__()

        self.setup_ui()
        self.setup_machine()
        self.connect_things()

    def setup_ui(self):
        self.widget = QWidget()
        self.label = QLabel()
        self.push = QPushButton('Push Me')
        self.quit = QPushButton('Quit Me')

        self.widget.setLayout(QtWidgets.QVBoxLayout())
        self.widget.layout().addWidget(self.label)
        button_layout = QtWidgets.QHBoxLayout()
        self.widget.layout().addLayout(button_layout)

        button_layout.addWidget(self.push)
        button_layout.addWidget(self.quit)


    def setup_machine(self):
        self.machine = QStateMachine()
        self.grouped_state = QState()
        self.state_1 = QState(self.grouped_state)
        self.state_2 = QState(self.grouped_state)
        self.state_3 = QStatePrint(self.grouped_state)
        self.grouped_state.setInitialState(self.state_1)

        self.final_state = QFinalState()

        trans_s12 = self.state_1.addTransition(self.push.clicked, self.state_2)
        trans_s23 = self.state_2.addTransition(self.push.clicked, self.state_3)
        trans_s31 = self.state_3.addTransition(self.push.clicked, self.state_1)

        self.grouped_state.addTransition(self.quit.clicked, self.final_state)

        self.state_1.assignProperty(self.label, 'text', "I'm in State 1")
        self.state_2.assignProperty(self.label, 'text', "I'm in State 2")
        self.state_3.assignProperty(self.label, 'text', "I'm in State 3")

        self.state_1.assignProperty(self.label, "font", QtGui.QFont('Arial', pointSize=22))
        self.state_2.assignProperty(self.label, "font", QtGui.QFont('Calibri', pointSize=22))
        self.state_3.assignProperty(self.label, "font", QtGui.QFont('Comic Sans MS', pointSize=22))

        self.state_1.assignProperty(self.push, "geometry", QtCore.QRectF(0, 0, 200, 200))
        self.state_2.assignProperty(self.push, "geometry", QtCore.QRectF(0, 0, 100, 100))
        self.state_3.assignProperty(self.push, "geometry", QtCore.QRectF(0, 0, 300, 300))

        trans_s12.addAnimation(QtCore.QPropertyAnimation(self.push, b'geometry'))

        self.machine.addState(self.grouped_state)
        self.machine.addState(self.final_state)
        self.machine.setInitialState(self.grouped_state)

    def connect_things(self):
        self.state_3.entered.connect(self.push.showMaximized)
        self.state_3.exited.connect(self.push.showMinimized)

        self.machine.finished.connect(QtWidgets.QApplication.instance().quit)

    def start(self):
        self.machine.start()

    def show(self):
        self.widget.show()


def main():
    app = mkQApp('StateMachine')

    my_app = App()

    my_app.start()
    my_app.show()

    # Run application
    app.exec()


if __name__ == '__main__':
    main()


