from PyQt5.QtCore import QSignalMapper, pyqtSignal
from PyQt5.QtCore import QStateMachine, QState, QFinalState, QSignalTransition


Signal = pyqtSignal


class StateMachine(QStateMachine):
    """Sequencer state machine.

    Maps the flux diagram of the sequence of operations of an experiment onto
    a QStateMachine. Each state represents an operation or a set of operations
    to be performed at the corresponding step of the experiment. Transitions
    between states are triggered by events from different sources, each
    signalling some kind of 'next step' or 'operation completed' or
    'operation failed'. The state machine is configured from a definition file
    in yaml format and set up through a StateMachineFactory.
    """

    state_entered = Signal(str)
    transition_triggered = Signal(str) # not used yet

    def __init__(self):
        super().__init__()
        self.setObjectName("state-machine")
        self.states = {}
        self.signals = []
        self.entered_mapper = QSignalMapper()
        self.entered_mapper.mappedString.connect(self.state_entered)
        self.entered_mapper.setMapping(self, self.objectName())
        self.entered.connect(self.entered_mapper.map)
        self.entered.connect(self._log_entered)
        self.exited.connect(self._log_left)
        self.active_state = None

    def _add_signal(self, name, *args):
        # adds a signal for the internal use to trigger transitions
        if name not in self.signals:
            cls = self.__class__
            new_cls = type(cls.__name__, cls.__bases__,
                           { **cls.__dict__, name: Signal(*args) })
            self.__class__ = new_cls
            self.signals.append(name)
        return getattr(self, name)

    def add_state(self, name, is_initial=False, is_final=False,
                  parent=None) -> QState:
        """Adds a new state to the state machine.

        When parent is None, the state is added to the state machine as top
        level child, otherwise as child state to parent.
        Upon entering any state which is not a final one, the state machine's
        state_entered(str) signal will be emitted with the state's name as
        argument.

        The _log methods should eventually be replaced by proper PyMoDAQ
        logging / debugging calls.
        """
        assert name not in self.states
        new_state = QFinalState(parent) if is_final else QState(parent)
        self.states[name] = new_state
        new_state.setObjectName(name)
        if is_final:
            assert not is_initial
        else:
            new_state.entered.connect(self._log_entered)
            new_state.exited.connect(self._log_left)
            self.entered_mapper.setMapping(new_state, name)
            new_state.entered.connect(self.entered_mapper.map)
            if is_initial:
                assert not is_final
                parent.setInitialState(new_state)
        return new_state

    @classmethod
    def _get_event_signal_name(cls, event: str):
        return '_sig_%s' % event.replace('-', '_')

    def add_transition(self, source: str, target: str,
                       event: str) -> QSignalTransition:
        """A transition from state source to state target is added.

        The transisition will be triggered upon receiving event if source is
        an active state.
        """
        event_signal_name = self._get_event_signal_name(event)
        event_signal = self._add_signal(event_signal_name)
        target = self.states[target]
        print("adding transition %s from %s to %s"
              % (event_signal_name, source, target.objectName()))
        return self.states[source].addTransition(event_signal, target)

    def take_event(self, event: str):
        """Take an event which should trigger a transisition.

        The event string is transformed into the corresponding internal
        Qt signal name and the signal is emitted to trigger any matching
        transition.
        """
        print("state machine: got event %s" % event)
        if self.active_state is not None:
            print("state machine: active state is %s" % self.active_state)

        event_sig_name = self._get_event_signal_name(event)
        try:
            signal = getattr(self, event_sig_name)
        except:
            raise RuntimeError("Event '%s' has not been defined" % event)
        signal.emit()

    def _log_entered(self):
        self.active_state = self.sender().objectName()
        print("state machine entered state %s" % self.sender().objectName())

    def _log_left(self):
        self.active_state = None
        print("state machine left state %s" % self.sender().objectName())
