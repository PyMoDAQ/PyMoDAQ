from PyQt5.QtCore import QObject, pyqtSignal
from enum import Enum
from threading import Thread
import time


Signal = pyqtSignal


class DummyScanner1D(QObject):

    done = Signal()

    def __init__(self, actuator_controller, actuator, n_points):
        super().__init__()
        self.actuator_controller = actuator_controller
        self.actuator = actuator
        self.n_points = n_points
        self.points = [i for i in range(n_points)]
        self.current = 0

    def perform_action(self, action):
        print("scanner:", action)
        if action == "advance":
            self.current += 1
            if self.current == self.n_points:
                print("Scanner: loop done")
                self.done.emit()
            else:
                print("Scanner: next point %d" % self.current)
                action = { self.actuator: '%d' % self.points[self.current] }
                self.actuator_controller.perform_actions(action)


class DummyDataProcessor(QObject): # some sort of data mixer

    acquisition_done = Signal()

    class State(Enum):
        IDLE = 0
        BACKGROUND = 1
        REFERENCE = 2
        ABSORPTION = 3

    def __init__(self):
        super().__init__()
        self.state = self.State.IDLE
        self.acquisition_counter = 0

    def perform_action(self, action):
        if action == 'dark':
            self.set_state('dark')
        elif action == 'reference':
            self.set_state('reference')
        elif action == 'absorption':
            self.set_state('absorption')

    def set_state(self, state: str):
        print("data processor: to state", state)
        self.acquisition_counter = 0
        self.state = state

    def take_data(self, data):
        if self.state != self.State.IDLE:
            # should process data in different ways according to state
            print("data processor: taking data", data)
            self.acquisition_counter += 1
            if self.acquisition_counter < 10:
                # could send some dte_temp signal to display preliminary data 
                return
            self.state = self.State.IDLE
            print("data processor: acquisition done")
            # send some dte signal to display and store definitive data 
            self.acquisition_done.emit()


class DummyCamera(QObject):

    data_ready = Signal(int)

    def __init__(self):
        super().__init__()
        self.data_counter = 0
        self.grab_thread = None

    def perform_action(self, action):
        if action == 'start-grabbing':
            self.start_grabbing()
        elif action == 'stop-grabbing':
            self.stop_grabbing()

    def start_grabbing(self):
        if self.grab_thread is not None:
            return
        self.grab_thread = Thread(target=self.grab_loop)
        self.stop = False
        self.grab_thread.start()
        
    def stop_grabbing(self):
        self.stop = True
        self.grab_thread.join()
        self.grab_thread = None

    def grab_loop(self):
        while not self.stop:
            self.data_ready.emit(self.data_counter)
            self.data_counter += 1
            time.sleep(0.01)


class DummyActuator(QObject):

    done = Signal(str)
    error = Signal(str)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def perform_action(self, action):
        print("actuator %s performing action %s" % (self.name, str(action)))
        self.done.emit(self.name)


class DummyShutter(DummyActuator):

    pass


class DummyDelayLine(DummyActuator):

    pass
