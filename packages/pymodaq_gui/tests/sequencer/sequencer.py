from PyQt5.QtCore import QObject, pyqtSignal

Signal = pyqtSignal

class ActuatorController(QObject):
    """A class to coordinate actuator operations.

    When multiple actuators have to perform operations at the same time, a
    racing condition may accur when one device signals success before others
    are even started (i.e. a translation stage which doesn't need to move
    because already is at the target asked for). This class is used in the
    current test framework. It may be not needed when performing actuator
    operations via the dashboad.
    """

    devices_ready = Signal()

    def __init__(self, actuators: dict):
        self.actuators = actuators
        super().__init__()
        for actuator in self.actuators.values():
            actuator.done.connect(self.actuator_done)

    def perform_actions(self, actions):
        self.pending_actuators = []
        for target, action in actions.items():
            print("sequencer: action on actuator %s" % target)
            self.pending_actuators.append(target)
        for target, action in actions.items():
            self.actuators[target].perform_action(action)

    def check_pending_actuators(self):
        if not len(self.pending_actuators):
            print("actuator controller: all devices ready")
            self.devices_ready.emit()
        else:
            print("actuator controller: devices %s still pending"
                  % self.pending_actuators)

    def actuator_done(self, actuator):
        print("actuator controller: got device ready from %s" % actuator)
        try:
            self.pending_actuators.remove(actuator)
        except Exception as e:
            print(e)
            breakpoint()
        self.check_pending_actuators()


class Sequencer(QObject):

    def __init__(self, yaml_states, actuator_controller, detectors: dict,
                 data_processors: dict=None, scanners: dict=None):
        super().__init__()
        self.actuator_controller = actuator_controller
        self.actuators = self.actuator_controller.actuators.copy()
        self.detectors = detectors
        self.data_processors = data_processors
        self.scanners = scanners
        self.targets = self.actuators.copy()
        self.targets.update(detectors)
        self.targets.update(data_processors)
        self.targets.update(scanners)
        self.detector_actions = {}
        self.actuator_actions = {}
        self.software_actions = {}
        self._connect_things(yaml_states)

    def perform_detector_actions(self, detector: str, action: str):
        print("sequencer: detector %s, action %s" % (detector, action))

    def perform_actuator_actions(self, actions: dict):
        for action in actions:
            print("sequencer: actuator %s, action %s"
                  % (action['actuator'], action['action']))
        self.devices_ready.emit()

    def add_action(self, signal: str, target: str, action: dict):
        if target in self.actuators:
            if signal in self.actuator_actions:
                self.actuator_actions[signal][target] = action
            else:
                self.actuator_actions[signal] = { target: action }
        elif target in self.detectors:
            if signal in self.detector_actions:
                self.detector_actions[signal][target] = action
            else:
                self.detector_actions[signal] = { target: action }
        elif target in self.data_processors or target in self.scanners \
             or target == 'gui':
            if signal in self.software_actions:
                self.software_actions[signal][target] = action
            else:
                self.software_actions[signal] = { target: action }
        else:
            raise RuntimeError("Target '%s' not defined" % target)

    def _connect_things(self, states):
        for state_data in states:
            if 'actions' in state_data:
                for action in state_data['actions']:
                    self.add_action(state_data['name'], action['unit'],
                                    action['action'])
            if 'states' in state_data:
                self._connect_things(state_data['states'])
        
    def event(self, event):
        print("sequencer got event %s" % event)
        if event in self.software_actions:
            for target, action in self.software_actions[event].items():
                print("sequencer: software action on %s" % target)
                if target in self.data_processors:
                   self.data_processors[target].perform_action(action)
                elif target in self.scanners:
                   self.scanners[target].perform_action(action)
                elif target == 'gui':
                   self.gui.perform_action(action)
                else:
                    breakpoint()
        if event in self.detector_actions:
            for target, action in self.detector_actions[event].items():
                print("sequencer: action on detector %s" % target)
                self.detectors[target].perform_action(action)
        if event in self.actuator_actions:
            self.actuator_controller\
                .perform_actions(self.actuator_actions[event])


