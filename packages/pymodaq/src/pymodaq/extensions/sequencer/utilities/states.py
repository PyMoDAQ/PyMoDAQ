import weakref
from typing import Callable, Optional, TYPE_CHECKING, Any, Union
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

        # Static fallback only (e.g. InterruptState, which has no owning elt to describe it
        # lazily - see `name_fn` below). Elements of the sequencer tree get their name computed
        # on demand instead.
        if name is not None:
            self.setObjectName(name)

        self.incoming_transition: TrackedTransition | None = None  # This will hold the transition object
        self.source_state: MyState | CompositeState | None = None
        #: when set, overrides objectName() with a value computed at call time rather than one
        #: frozen in at construction - see CompositeState.setup_states() for why that matters.
        #: Safe to do here only because objectName()/setObjectName() in this module are read
        #: solely by the onEntry/onExit debug logs below - nothing Qt-internal or outside this
        #: module depends on the native QObject value.
        self.name_fn: Optional[Callable[[], str]] = None

    def objectName(self) -> str:
        if self.name_fn is not None:
            return self.name_fn()
        return super().objectName()

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
        self.name_fn: Optional[Callable[[], str]] = None

    def objectName(self) -> str:
        if self.name_fn is not None:
            return self.name_fn()
        return super().objectName()

    def onEntry(self, event, /):
        logger.debug(f'Entering  {self.objectName()}')

    def onExit(self, event, /):
        logger.debug(f'Exiting {self.objectName()}')


class _SignalRelay(QtCore.QObject):
    """ Forwards the signals of a sequence element to transitions owned by a state

    A transition built directly on the signal of an element holds a reference to it. As the states are kept alive by
    their C++ parent, this creates a reference cycle (state -> element -> sequence -> state) going through C++ that
    the garbage collector cannot see, and the whole sequence (and its widgets) is never freed. Building the
    transitions on the signals of this relay, which belongs to the state, keeps the element out of the cycle.
    """
    children_signal = QtCore.Signal()
    done_signal = QtCore.Signal()


class CompositeState(MyState):
    def __init__(self, elt: 'SeqEltBase', *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.execute_state: MyState | None = None
        self.done_state: MyQFinalState | None = None
        self.children_state: MyState | None = None
        self._external_transitions = []

        #: whatever Sequence.recursive_connect_elts() wires this element's own forward
        #: progress to (next sibling, or the parent's execute_state if it's last) - stashed
        #: there each run so anything else that needs "what comes after me" (BranchHolder's
        #: CONTINUE branches) doesn't have to recompute sibling/parent lookups itself.
        self.next_state: Union['CompositeState', MyQFinalState, None] = None

        self._elt_ref = weakref.ref(elt)  # the states are held by C++ (their parent): a strong reference to the
        # element, that refers to the sequence, would be a cycle the garbage collector can not see

        self.setup_states()

        self.execute_state.entered.connect(elt.execute)
        # the transitions listen to relays owned by this state: a transition holding a signal of the element
        # would keep the element (and this state, held by it) alive
        self._relay = _SignalRelay(self)
        elt.children_signal.connect(self._relay.children_signal)
        elt.done_signal.connect(self._relay.done_signal)
        self.execute_state.addTransition(self._relay.children_signal, self.children_state)

        self.addTransition(self._relay.done_signal, self.done_state)  # apply to all substates

    @property
    def _elt(self) -> 'SeqEltBase':
        return self._elt_ref()

    def set_do_init(self, value: bool) -> None:
        if value and hasattr(self._elt, 'initialize_element'):
            self._elt.initialize_element()

    def setup_states(self):
        # Deferred, not `setObjectName(f'...{self._elt}')`: `self._elt`'s __repr__ (ChoiceElt's,
        # for instance) can read attributes other holders of the same element set up later in
        # its __init__ - condition before branches, say. Evaluating the name only when a state
        # is actually entered (debug logging, below) means that by construction the whole
        # element already exists, so no such ordering constraint is needed between holders.
        self.name_fn = lambda: f'State of the elt: {self._elt}'

        self.execute_state = MyState(self)
        self.execute_state.name_fn = lambda: f'ExecuteState of the elt: {self._elt}'
        self.done_state = MyQFinalState(self)
        self.done_state.name_fn = lambda: f'FinalState of the elt: {self._elt}'
        self.children_state = MyState(self)
        self.children_state.name_fn = lambda: f'ChildrenState of the elt: {self._elt}'
        self.setInitialState(self.execute_state)

    def track_transition(self, transition: QAbstractTransition) -> QAbstractTransition:
        """ Add an already-built transition and track it as ephemeral/per-run: anything
        registered here is torn down by clear_transitions() (Sequence.recursive_disconnect_elts,
        before every run - tree order may have changed since the last one) and must be rebuilt
        by whoever set it up in the first place (Sequence.recursive_connect_elts).

        Everything *not* routed through here - any transition an element or a composed holder
        (BranchHolder...) adds directly via addTransition() - is permanent by construction: it
        survives clear_transitions() with no extra bookkeeping needed, because clear_transitions()
        only ever touches what was registered here.
        """
        # addTransition() returns None (not the transition) when passed an already-built
        # transition object rather than a (signal, target) pair - track `transition` itself.
        self.addTransition(transition)
        self._external_transitions.append(transition)
        return transition

    def add_external_transition(self, signal: QtCore.Signal,
                                target: Union['CompositeState', MyState, MyQFinalState]):
        self.track_transition(TrackedTransition(signal, self, target))

    @property
    def external_transitions(self) -> list[QAbstractTransition]:
        return self._external_transitions

    def clear_transitions(self):
        for trans in self._external_transitions:
            self.removeTransition(trans)
        self._external_transitions = []

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
