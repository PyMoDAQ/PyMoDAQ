from typing import TYPE_CHECKING, Any, Union
import qtpy
from qtpy import QtCore

from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase


logger = set_logger(get_module_name(__file__))

if qtpy.PYQT6:
    from PyQt6.QtStateMachine import QStateMachine, QState, QFinalState, QSignalTransition, QAbstractTransition, QHistoryState
elif qtpy.PYSIDE6:
    from qtpy.QtStateMachine import QStateMachine, QState, QFinalState, QSignalTransition, QAbstractTransition, QHistoryState
elif qtpy.PYQT5:
    from PyQt5.QtCore import QStateMachine, QState, QFinalState, QSignalTransition, QAbstractTransition, QHistoryState


class MyState(QState):
    def __init__(self, parent=None, name: str = None):
        super().__init__(parent)

        if name is not None:
            self.setObjectName(name)

        self.incoming_transition: TrackedTransition | None = None  # This will hold the transition object
        self.source_state: MyState | CompositeState | None = None

    def onEntry(self, event, /):
        logger.debug(f'Entering {self.objectName()}')
        super().onEntry(event, )

    def onExit(self, event, /):
        logger.debug(f'Exiting {self.objectName()}')
        super().onExit(event, )

class MyQFinalState(QFinalState):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.incoming_transition: TrackedTransition | None = None  # This will hold the transition object
        self.source_state: MyState | CompositeState | None = None

    def onEntry(self, event, /):
        logger.debug(f'Entering  {self.objectName()}')

    def onExit(self, event, /):
        logger.debug(f'Exiting {self.objectName()}')


class CompositeState(MyState):
    def __init__(self, elt: 'SeqEltBase', *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.execute_state: MyState | None = None
        self.done_state: MyQFinalState | None = None
        self.children_state: MyState | None = None
        self._external_transitions = []

        self.transitions_to_keep = []

        self._elt = elt

        self.setup_states()

        self.execute_state.entered.connect(elt.execute)
        self.transitions_to_keep.append(
            self.execute_state.addTransition(elt.children_signal, self.children_state))

        self.transitions_to_keep.append(
            self.addTransition(elt.done_signal, self.done_state))  # apply to all substates)

    def set_do_init(self, value: bool) -> None:
        if value and hasattr(self._elt, 'initialize_element'):
            self._elt.initialize_element()

    def setup_states(self):
        self.setObjectName(f'State of the elt: {self._elt}')

        self.execute_state = MyState(self)
        self.execute_state.setObjectName(f'ExecuteState of the elt: {self._elt}')
        self.done_state = MyQFinalState(self)
        self.done_state.setObjectName(f'FinalState of the elt: {self._elt}')
        self.children_state = MyState(self)
        self.children_state.setObjectName(f'ChildrenState of the elt: {self._elt}')
        self.setInitialState(self.execute_state)

    def add_external_transition(self, signal: QtCore.Signal,
                                target: Union['CompositeState', MyState, MyQFinalState]):
        self._external_transitions.append(
            self.addTransition(TrackedTransition(signal, self, target)))

    @property
    def external_transitions(self) -> list[QAbstractTransition]:
        return self._external_transitions

    def clear_transitions(self):
        for trans in list(self.external_transitions):
            self.removeTransition(trans)
        for trans in self.transitions():
            if trans not in self.transitions_to_keep:
                self.removeTransition(trans)

    def clear_state_and_transitions(self):
        self.clear_transitions()
        self.setParent(None)


class TrackedTransition(QSignalTransition):
    def __init__(self, signal: QtCore.Signal,
                 source_state: CompositeState | MyState,
                 target_state: CompositeState | MyState = None, ):
        super().__init__(signal)
        self.source_state = source_state
        if target_state is not None:
            self.setTargetState(target_state)

    def update_target(self, state: CompositeState):
        self.setTargetState(state)

    def onTransition(self, event: QtCore.QEvent):
        # This runs right before the target state's onEntry()
        super().onTransition(event)

        # Save a reference to this transition in the target state
        target: MyState = self.targetState()
        if target:
            target.source_state = self.source_state

    @staticmethod
    def is_child_of(child_state, target_parent):
        """Walks up the parent chain to see if target_parent is an ancestor."""
        current = child_state.parentState()
        while current is not None:
            if current == target_parent:
                return True
            current = current.parentState()  # Go up one more level
        return False

    def targetState(self) -> CompositeState:
        return super().targetState()

    def eventTest(self, event: QStateMachine.SignalEvent) -> bool:
        if (isinstance(self.targetState(), CompositeState) and
            not self.is_child_of(self.source_state, self.targetState())):
                self.targetState().set_do_init(True)

        return super().eventTest(event)


class InterruptState(MyState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender_state: QState | CompositeState = None
        self.setObjectName('InterruptState of the Sequencer')

    def onEntry(self, event: QtCore.QEvent):
        # Always call the base class implementation first
        logger.debug(f'Entering {self.objectName()}')
        super().onEntry(event)

        if event is not None:
            # Check if the event came from a transition signal
            if event.type() == QtCore.QEvent.Type.StateMachineSignal:
                # Cast or treat as SignalEvent
                sig_event: QStateMachine.SignalEvent = event
                # Get the object that sent the signal
                self.sender_state = sig_event.sender()


class ValueTransition(TrackedTransition):
    def __init__(self, signal: QtCore.Signal,
                 value: Any,
                 source_state: CompositeState | QState,
                 target_state: CompositeState | QState = None, ):
        super().__init__(signal, source_state, target_state)
        self.value = value

    def eventTest(self, event: QStateMachine.SignalEvent) -> bool:
        if not super().eventTest(event):
            return False

        arguments = event.arguments()
        if arguments:
            value = arguments[0]
            return value == self.value
        return False
