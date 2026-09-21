from pathlib import Path
import yaml

from pymodaq_gui.utils.app_worker import ExtensionWorker, SaverWorker
from pymodaq.utils.h5modules.module_saving import LoggerSaver
from pymodaq_data.h5modules.data_saving import DataBundle
from pymodaq_data import DataToExport
from pymodaq_gui.managers.h5manager import FileAction
from pymodaq_gui.messenger import messagebox
from pymodaq_gui.utils import select_file
from pymodaq.extensions.sequencer.utilities.sequencer.sequence import Sequence

from qtpy import QtWidgets

from pymodaq_gui import utils as gutils
from pymodaq_gui.utils.custom_app import WorkFlowActions
from pymodaq_gui.utils.enums import MenuToolbarNames

from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq.extensions.utils import CustomExt
from pymodaq_gui.utils.widgets import QLED
from pymodaq.extensions.sequencer.utilities.elements.sequence import SequenceElt
from pymodaq.extensions.sequencer import get_set_sequencer_path
from pymodaq.extensions.sequencer.utilities.yaml_utils import PrettyListDumper

logger = set_logger(get_module_name(__file__))

main_config = GlobalConfig()


EXTENSION_NAME = 'Sequencer'
CLASS_NAME = 'Sequencer'


class StatusBarManager:
    def __init__(self, app: 'Sequencer'):
        self.app = app

        self._running_led: QLED = None

    @property
    def statusbar(self):
        return self.app.statusbar

    def set_permanent_status(self, status: str):
        self.app.set_permanent_status(status)

    def create_permanent_widgets(self):
        # self._running_led = QLED()
        # self._running_led.setToolTip('logging status: green (running), red (idle)')
        # self._running_led.clickable = False
        # self.statusbar.addPermanentWidget(self._running_led)
        pass


class Sequencer(CustomExt):
    show_h5file_statusbar_widgets = True
    show_workflow_actions = True

    params = [] + SaverWorker.params

    def __init__(self, parent: gutils.DockArea, dashboard):

        self.sequence_worker = SequenceWorker(self)
        super().__init__(parent, dashboard, add_toolbar_break=False)

        self.sequences: dict[str, Sequence] = {}
        self.sequence_names: list[str] = []
        self.sequence_container: QtWidgets.QWidget = None
        self.status_manager = StatusBarManager(self)

        self._module_and_data_saver = LoggerSaver(self)
        self.setup_ui()

        self._current_path: Path = get_set_sequencer_path()

    def do_things_after_ui_setup(self):
        self.add_sequence('Main')

    @property
    def module_and_data_saver(self) -> LoggerSaver:
        return super().module_and_data_saver

    def setup_docks_and_widgets(self):
        """Mandatory method to be subclassed to setup the docks layout

        See Also
        --------
        pyqtgraph.dockarea.Dock
        """
        self.hor_widget = QtWidgets.QWidget()
        self.hor_widget.setLayout(QtWidgets.QHBoxLayout())
        self.sequence_container = QtWidgets.QWidget()
        self.sequence_container.setLayout(QtWidgets.QHBoxLayout())
        self.hor_widget.layout().addWidget(self.sequence_container)

        settings_widget = QtWidgets.QWidget()
        settings_widget.setLayout(QtWidgets.QVBoxLayout())

        self.hor_widget.layout().addWidget(settings_widget)
        settings_widget.layout().addWidget(self.settings_tree)
        settings_widget.layout().addWidget(self.h5_manager.h5saver.settings_tree)

        self.mainwindow.setCentralWidget(self.hor_widget)
        self.h5_manager.h5saver.settings_tree.setVisible(False)
        self.settings_tree.setVisible(False)
        self.settings_tree.setMinimumHeight(150)

        self.populate_status_bar()

    def populate_status_bar(self):
        super().populate_status_bar()
        self.status_manager.create_permanent_widgets()
        self.status_manager.set_permanent_status('')

    def add_sequence(self, name: str = 'main'):

        widget = QtWidgets.QWidget()
        self.sequence_names.append(name.lower())
        self.sequences[name.lower()] = Sequence(name.lower(), widget, self.dashboard)
        self.sequence_container.layout().addWidget(widget)
        SequenceElt.register_sequence(self.sequences[name.lower()])
        self.set_action_enabled('remove_sequence', len(self.sequences) > 1)

    def remove_sequence(self, name: str = None):
        if name is None:
            name = list(self.sequences.keys())[-1]

        seq = self.sequences.pop(name.lower())
        self.sequence_container.layout().removeWidget(seq.parent)
        seq.parent.setParent(None)
        seq.parent.deleteLater()
        self.set_action_enabled('remove_sequence', len(self.sequences) > 1)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar

        create menu for actions contained into the self._actions, for instance:

        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        self.add_toolbar(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), self.mainwindow,
                         toolbar=self.h5_manager.toolbar, add_break=False)
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)

        self.create_dashboard_toolbar(add_break=False)

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        super().do_things_after_experiment_set(experiment_name, show_dashboard)

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


        self.toolbar.addSeparator()
        self.add_action('add_sequence', 'Add Sequence', 'add_circle',
                        tip='Add a sequence',
                        )
        self.add_action('remove_sequence', 'Remove Sequence', 'remove',
                        tip='Remove last sequence', enabled=False,
                        )
        self.toolbar.addSeparator()
        self.add_action('load_sequence', 'Load Sequence', 'file_open',
                        tip='Load a sequence file',
                        )
        self.add_action('save_sequence', 'Save Sequence', 'file_save',
                        tip='Save as a sequence file',
                        )

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action('add_sequence',
                            lambda: self.add_sequence(f'Sequence{len(self.sequences):03.0f}'),)
        self.connect_action('remove_sequence', lambda: self.remove_sequence(),)
        self.connect_action('load_sequence', lambda: self.load_sequence())
        self.connect_action('save_sequence', lambda: self.save_sequence())

        self.connect_action(WorkFlowActions.START, self.sequence_worker.start)
        self.connect_action(WorkFlowActions.STOP, self.sequence_worker.stop)
        self.connect_action(WorkFlowActions.PAUSE, self.sequence_worker.pause)

        self.h5_manager.connect_action(FileAction.SHOW_SETTINGS, self.show_settings)

    def show_settings(self, show=True):
        self.settings_tree.setVisible(show)

    def load_sequence(self, path: Path = None):
        if path is None:
            path = select_file(self._current_path,
                               filter='Sequence file (*.seq)',
                               save=False, ext='seq', force_save_extension=True)
        if path is not None and path != '':
            self._current_path = path.parent

            with open(path, 'r') as file:
                sequence_dict = yaml.safe_load(file)
        if 'sequences' in sequence_dict:
            while len(self.sequences) > 0:
                self.remove_sequence()
            for seq_name in sequence_dict['sequences']:
                # first, creates all the Sequence objects
                self.add_sequence(seq_name)
            for seq_name, seq_dict in sequence_dict['sequences'].items():
                # then load the sequence content (eventually containing other sequences references,
                # hence creating all of them first
                self.sequences[seq_name].load_sequence(seq_dict)
        else:
            while len(self.sequences) > 1:
                self.remove_sequence()
            self.sequences[list(self.sequences.keys())[0]].load_sequence(sequence_dict)

    def save_sequence(self, path: Path = None):
        if path is None:
            path = select_file(self._current_path,
                               filter='Sequence file (*.seq)',
                               save=True, ext='seq', force_save_extension=True)
        if path is not None and path != '':
            self._current_path = path.parent
            sequence_dict = {'sequences': {}}
            for sequence_name, sequence in self.sequences.items():
                sequence_dict['sequences'][sequence_name] = sequence.root_elt.to_dict()

            with open(path, 'w') as file:
                yaml.dump(
                    sequence_dict,
                    file,
                    Dumper=PrettyListDumper,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )
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
    def main_sequence(self) -> Sequence:
        return self.sequences[self.sequence_names[0]]

    def _quit_fun(self) -> bool:
        if self.sequence_worker.is_running:
            messagebox(title='Running',
                       text='The Sequencer is running, first stop it')
            return False
        elif self.settings[SaverWorker.worker_setting_name, 'worker_tasks'] > 0:
            messagebox(title='Running',
                       text='The Saver is finishing the savings')
            self.sequence_worker.stop("User prompted a quit of the Application, Stopping the Acquisition")
            return False

        return True


class SequenceWorker(ExtensionWorker):

    def __init__(self, sequencer: Sequencer, parent=None):
        super().__init__(app=sequencer, parent=parent)

    @property
    def app(self) -> Sequencer:
        return self._app

    @property
    def status_manager(self) -> StatusBarManager:
        return self.app.status_manager

    def save_callback(self, dte: DataToExport):
        self.thread_manager.n_jobs[SaverWorker.name] += 1
        self.saver_worker.data_to_save_signal.emit(DataBundle(dte=dte))

    def _start(self):
        self.module_and_data_saver.get_set_node(new=True)
        for sequence in self.app.sequences.values():
            sequence.set_log_callback(self.save_callback if self.app.is_action_checked(WorkFlowActions.LOG)
                                      else None)


        self.app.enable_workflow_actions(False, excepted=(WorkFlowActions.PAUSE,
                                                          WorkFlowActions.STOP,
                                                          WorkFlowActions.LOG))

        self.app.main_sequence.sequence_finished.connect(self.stopped)
        self.app.main_sequence.get_action(WorkFlowActions.START).trigger()

    def _pause(self, do_pause: bool = True):
        for sequence in self.app.sequences.values():
            sequence.get_action(WorkFlowActions.PAUSE).trigger()


    def stop(self, msg: str = None):
        for sequence in self.app.sequences.values():
            sequence.get_action(WorkFlowActions.STOP).trigger()

    def stopped(self, msg: str = None):
        super().stop(msg)

    def _stop(self, msg: str = None):
        for sequence in self.app.sequences.values():
            sequence.recursive_disconnect_elts()

        self.app.enable_workflow_actions(True,
                                         opposite=WorkFlowActions.PAUSE)
        if msg is not None:
            self.app.update_status(msg)
            self.status_manager.set_permanent_status(msg)



def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import load_dashboard_with_arguments
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('Custom Ext')

    win, dashboard, ext = load_dashboard_with_arguments(show_dashboard=False,
                                                        load_extension=False,
                                                        )
    win.mainwindow.setVisible(False)

    win_ext, ext = create_extension(dashboard, Sequencer)
    win_ext.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
