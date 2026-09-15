from typing import Callable

from pathlib import Path

from pymodaq_gui.utils.widgets.window import make_window
from pymodaq_plugins_sequencer.utilities.states import (
    QStateMachine, MyQFinalState, QHistoryState, QState, QAbstractTransition, TrackedTransition, InterruptState,
    ValueTransition)

from qtpy import QtWidgets, QtCore


from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, ElementError
from pymodaq_plugins_sequencer.utilities.sequencer.model_view import SequenceTreeView, SequenceTreeModel, \
    SequenceWidgetDelegate
from pymodaq_plugins_sequencer.utilities.elements.root import RootElt
from pymodaq_plugins_sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq_utils.config import Config, GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq.extensions.utils import CustomExt

logger = set_logger(get_module_name(__file__))

main_config = GlobalConfig()


class Sequence(CustomExt):
    sequence_finished = QtCore.Signal()
    params = []

    def __init__(self, title: str, parent: QtWidgets.QWidget, dashboard):
        super().__init__(parent, dashboard, add_toolbar_break=False,
                         title=title)

        self.view: SequenceTreeView = None
        self._model: SequenceTreeModel = None

        self.log_callback: Callable = None

        self.machine = QStateMachine()
        self.done_state = MyQFinalState()
        self.interrupt_state = InterruptState()

        self.setup_ui()
        self.setup_machine()

    def setup_docks_and_widgets(self):
        """Mandatory method to be subclassed to setup the docks layout

        See Also
        --------
        pyqtgraph.dockarea.Dock
        """

        self.parent.setLayout(QtWidgets.QVBoxLayout())

        self.view = SequenceTreeView(parent_sequence=self,
                                     parent=self.parent,
                                     dashboard=self.dashboard)
        self._model = SequenceTreeModel(parent_sequence=self,
                                        dashboard=self.dashboard)
        self.view.setModel(self._model)

        self.delegate = SequenceWidgetDelegate()
        self.view.setItemDelegate(self.delegate)

        self.view.setSelectionMode(self.view.SelectionMode.SingleSelection)
        self.view.setDragEnabled(True)
        self.view.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.view.setAcceptDrops(True)
        self.view.setDragDropMode(self.view.DragDropMode.DragDrop)
        self.view.expandAll()
        self.view.setHeaderHidden(True)

        self.label = QtWidgets.QLabel('')
        self.statusbar.addPermanentWidget(self.label)

        self.parent.layout().addWidget(self.view)
        self.parent.layout().addWidget(self.statusbar)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar

        create menu for actions contained into the self._actions, for instance:

        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        self.parent.layout().insertWidget(0, self.toolbar)

    def do_things_after_ui_setup(self):
        self.create_dashboard_toolbar(add_break=False)

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        pass

    def setup_actions(self):
        """Method where to create actions to be subclassed. Mandatory

        Examples
        --------
        >>> self.add_action('quit', 'Quit', 'close2', "Quit program")
        >>> self.add_action('grab', 'Grab', 'camera', "Grab from camera", checkable=True)
        >>> self.add_action('load', 'Load', 'Open', "Load target file (.h5, .png, .jpg) or data from camera"
            , checkable=False)
        >>> self.add_action('save', 'Save', 'SaveAs', "Save current data", checkable=False)

        See Also
        --------
        ActionManager.add_action
        """
        self.add_widget('name', QtWidgets.QLineEdit(self.title), toolbar=self.toolbar,
                        tip='Set the name of this Sequence')
        self._toolbar.addSeparator()
        self.add_action('start', 'Start', 'motion_play', "Start the Sequence",
                        icon_color=self.get_theme().green, toolbar=self.toolbar)
        self.add_action('stop', 'Stop', 'stop_circle', "Stop the Sequence",
                        icon_color=self.get_theme().red, toolbar=self.toolbar)
        self.add_action('pause', 'Pause', 'pause_circle',
                        tip="Pause/resume the sequence",
                        checkable=True, toolbar=self.toolbar,
                        icon_checked_color=self.get_theme().orange)
        self._toolbar.addSeparator()

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action('start', self.start_sequence)
        self.interrupt_state.entered.connect(self.pause_sequence)

        self.root_elt.mstate.addTransition(self.get_action('stop').triggered, self.done_state)
        self.machine.finished.connect(self.sequence_stopped)

    def value_changed(self, param):
        """ Actions to perform when one of the param's value in self.settings is changed from the
        user interface

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        """
        pass

    @property
    def root_elt(self) -> RootElt:
        return self._model.root_elt

    def setup_machine(self):
        for child in self.machine.children():
            if isinstance(child, QAbstractTransition):
                self.machine.removeTransition(child)
            elif isinstance(child, QState | MyQFinalState):
                self.machine.removeState(child)

        self.machine.addState(self.root_elt.mstate)
        self.machine.addState(self.done_state)
        self.machine.addState(self.interrupt_state)
        self.machine.setInitialState(self.root_elt.mstate)
        self.root_elt.mstate.addTransition(self.root_elt.mstate.finished, self.done_state)

    def recursive_disconnect_elts(self, elt: SeqEltBase=None):
        if elt is None:
            elt = self.root_elt

        for ind_child, child in enumerate(elt.children_without_add):
            try:
                child.data_to_log_signal.disconnect()
            except AttributeError:
                pass
            try:
                child.mstate.entered.disconnect()
            except AttributeError:
                pass
            child.mstate.clear_state_and_transitions()
            if child.children_allowed:
                self.recursive_disconnect_elts(child)

    def selected_index_from_entered_state(self, child: SeqEltBase) -> Callable:
        return lambda: self.view.setCurrentIndex(self._model.index_from_element(child))

    def recursive_connect_elts(self, elt: SeqEltBase = None):
        if elt is None:
            elt = self.root_elt

        for ind_child, child in enumerate(elt.children_without_add):
            if self.log_callback is not None:
                child.data_to_log_signal.connect(self.log_callback)
            child.mstate.setParent(elt.mstate.children_state)
            child.mstate.entered.connect(self.selected_index_from_entered_state(child))
            child.mstate.addTransition(
                ValueTransition(self.get_action('pause').triggered,
                                True,
                                child.mstate,
                                self.interrupt_state, ))
            child.mstate.addTransition(self.get_action('stop').triggered, self.done_state)
            if ind_child == 0:
                elt.mstate.children_state.setInitialState(child.mstate)
            if ind_child == len(elt.children_without_add) - 1:
                child.mstate.add_external_transition(child.mstate.finished, elt.mstate.execute_state)
            else:
                child.mstate.add_external_transition(child.mstate.finished, elt.children[ind_child+1].mstate)
            child.mstate.assignProperty(self.label, 'text', repr(child))
            if child.children_allowed:
                self.recursive_connect_elts(child)

    def is_valid(self):
        res = True
        for elt in self.root_elt.get_elts(without_types=(AddButtonPlaceholder,)):
            try:
                elt.check_set_is_valid()
            except ElementError as e:
                res = False
                logger.error(str(e))
        return res

    def set_log_callback(self, log_callback: Callable):
        """ Set a Callback for all element to log (if any) their data into the log h5 file"""
        self.log_callback = log_callback

    def start_sequence(self,):
        self.set_action_enabled('start', False)
        self.recursive_disconnect_elts()
        self.label.setText('Machine starting')
        self.recursive_connect_elts()
        self.setup_machine()
        if not self.is_valid():
            self.label.setText('Some elements are not valid, check the log')
            return

        self.machine.start()

    def sequence_stopped(self):

        self.set_action_enabled('start', True)
        self.label.setText('Machine finished')
        self.sequence_finished.emit()

    def pause_sequence(self):
        # clear previsously set transition
        for transition in self.interrupt_state.transitions():
            self.interrupt_state.removeTransition(transition)

        # add a transition to the composite state the machine was in
        # before the user pressed the pause button (restart the composite state entirely...)!
        self.interrupt_state.addTransition(ValueTransition(
            self.get_action('pause').triggered,
            False,
            self.interrupt_state,
            self.interrupt_state.source_state))

    def load_sequence(self, path: Path | dict | str):
        self._model.load_elements(path)


def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import create_load_dashboard
    from pymodaq.utils.shared_ui import SharedUI

    app = mkQApp('Custom Ext')

    win, dashboard = create_load_dashboard()
    win.mainwindow.setVisible(True)
    window, dockarea = make_window(area=False, title=Sequence.__name__)

    parent_widget = QtWidgets.QWidget()
    sequence = Sequence('Main', parent_widget, dashboard)
    window.setCentralWidget(parent_widget)
    shared_ui = SharedUI(window, show=True)
    shared_ui.affect_application(sequence)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
