import numpy as np

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt

from pymodaq_gui.managers.runner_thread_manager import DataForProcessor
from pymodaq_gui.messenger import messagebox
from pymodaq_data.h5modules.backends import NodeError
from pymodaq_gui.plotting.data_viewers import ViewerDispatcher
from pymodaq_gui.utils.widgets.window import make_window
from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand

from pymodaq_data import DataRaw
from pymodaq_data import DataToExport
from pymodaq_data.h5modules.data_saving import DataToExportTimedSaver, GROUP, DataBundle, DataToExportSaver

from pymodaq_gui import utils as gutils
from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.utils import DockArea, Dock
from pymodaq_gui.utils.shared_ui import SharedUI
from pymodaq_gui.utils.enums import MenuToolbarNames
from pymodaq_gui.utils.custom_app import CustomApp, WorkFlowActions

from pymodaq_gui.utils.app_worker import ProcessorWorker, ExtensionWorker, SaverWorker

logger = set_logger(get_module_name(__file__))
config = GlobalConfig()


class DataGenerator(QtCore.QObject):
    data_signal = QtCore.Signal(DataToExport)
    stopped = QtCore.Signal()
    command_signal = QtCore.Signal(ThreadCommand)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.timer:  QtCore.QTimer = None


        self._refresh_time: int = None  # ms
        self.refresh_time = 100  #ms
        self._show_thread = True

        self.command_signal.connect(self.queue_command, Qt.ConnectionType.QueuedConnection)

    def queue_command(self, command: ThreadCommand):
        if self.timer is None:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(self._refresh_time)
            self.timer.timeout.connect(self.generate_data)

        if command.command == 'start':
            self.start()
        elif command.command == 'stop':
            self.stop()
        elif command.command == 'refresh_time':
            self.refresh_time = command.attribute

    def start(self):
        if self.timer is not None:
            self.timer.start()

    def stop(self):
        if self.timer is not None:
            self.timer.stop()
            self.stopped.emit()

    @property
    def refresh_time(self) -> int:
        return self._refresh_time

    @refresh_time.setter
    def refresh_time(self, value: int):
        self._refresh_time = value
        if self.timer is not None:
            is_active = self.timer.isActive()
            self.timer.stop()
            self.timer.setInterval(value)
            if is_active:
                self.timer.start()

    @QtCore.Slot()
    def generate_data(self) -> DataToExport:
        if self._show_thread:
            print(f'Generating data in Qthread{self.thread()}')
            self._show_thread = False
        dte = DataToExport('data', data=[
            DataRaw('data_random_0', data=[np.atleast_1d(np.random.random())], origin='generator'),
            DataRaw('data_random_1', data=[np.atleast_1d(np.random.random())], origin='generator')
        ])
        self.data_signal.emit(dte)
        return dte


class DataProcessor(ProcessorWorker):

    def __init__(self, h5saver: H5Saver, parent=None):
        super().__init__(h5saver, parent)

    @QtCore.Slot(DataForProcessor)
    def do_process_data(self, info: DataForProcessor):
        """ Process data here, Be aware that load_all try to load multiple nodes from the h5file but not at the same
        time (sequentially). In this multithreaded application, the saving could add data to a node in between the
        reading. What you expect to be data with same shape/size may not be True!

        If you want to avoid that effect, do the reading in the same thread that is saving the data, eventually sending
        then the loaded dte to this processor
        """
        try:
            print(f'Processing data')
            dte = self._data_loader.load_all(info.node_path)
            if dte is not None and len(dte) == 2:
                QtCore.QThread.msleep(2000) # simulate heavy-duty calculation
                self.data_processed_signal.emit(dte)
            self._n_jobs_done += 1
            self.n_jobs_done_signal.emit(self.name, self._n_jobs_done)
        except NodeError as e:
            print(e)


class MySaverLoader(CustomApp):

    h5_base_group_name = 'SaverExample'
    show_h5file_statusbar_widgets = True
    show_workflow_actions = True

    params = [
        {'title': 'Refresh Grab:', 'name': 'refresh_grab', 'type': 'int', 'value': 50, 'suffix': 'ms',
         'siPrefix': False},
        {'title': 'Refresh Plot:', 'name': 'refresh_plot', 'type': 'int', 'value': 1000, 'suffix': 'ms',
         'siPrefix': False},
    ] + SaverWorker.params + ProcessorWorker.params

    def __init__(self, parent: gutils.DockArea):

        self.worker = MySaverLoaderWorker(self)

        super().__init__(parent, add_toolbar_break=False)

        self.viewer: ViewerDispatcher = None

        self.data_generator: DataGenerator =None

        self.setup_ui()

        self.enable_workflow_actions(True)

    @property
    def module_and_data_saver(self) -> DataToExportTimedSaver:
        return DataToExportTimedSaver(self.h5_manager.h5saver)


    def setup_docks_and_widgets(self):
        """Mandatory method to be subclassed to setup the docks layout
        """
        self.settings_dock = Dock('Settings')
        self.settings_dock.addWidget(self.settings_tree)
        self.saving_dock = Dock('Saving')
        self.saving_dock.addWidget(self.h5saver.settings_tree)
        self.plotting_dock = Dock('Plots')
        self.rois_dock = Dock('Rois')
        self.area_plotter = DockArea()
        self.plotting_dock.addWidget(self.area_plotter)

        self.viewer = ViewerDispatcher(self.area_plotter, 'Plotter', rois_dock=self.rois_dock)

        self.dockarea.addDock(self.settings_dock, 'left')
        self.dockarea.addDock(self.saving_dock, 'right', self.settings_dock)
        self.dockarea.addDock(self.plotting_dock, 'right')
        self.dockarea.addDock(self.rois_dock, 'right')
        self.saving_dock.setVisible(False)
        self.populate_status_bar()

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar
        """
        self.add_toolbar(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), self.mainwindow,
                         toolbar=self.h5_manager.toolbar, add_break=False)
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)

    def do_things_after_ui_setup(self):
        pass

    def setup_actions(self):
        """Method where to create actions to be subclassed. Mandatory

        See Also
        --------
        ActionManager.add_action
        """
        pass

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action(WorkFlowActions.START, self.worker.start)
        self.connect_action(WorkFlowActions.STOP, self.worker.stop)
        self.connect_action(WorkFlowActions.PAUSE, self.worker.pause)


        self.connect_action(WorkFlowActions.LOG, lambda show: self.saving_dock.setVisible(show))

    def _quit_fun(self):
        """ Do things to clean your app and return True if ok or False (or None) if not.

        If your custom app is wrapped in a SharedUI,
        the sharedUI will handle the main window closing
        """

        if self.worker.is_running:
            messagebox(title='Running',
                       text='The Acquisition is running, first stop it')
            return
        elif self.settings[SaverWorker.worker_setting_name, 'worker_tasks'] > 0:
            messagebox(title='Running',
                       text='The Saver is finishing the savings')
            self.worker.stop()
            return

        self.h5saver.flush()
        self.h5saver.close()

    def get_app_toolbars(self) -> list[QtWidgets.QToolBar]:
        """ Get the main toolbars widget to be eventually added in the main window toolbararea

        Default is the default toolbar. To be reimplemented if needed
        """
        return [self.toolbar]

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
        if param.name() == 'refresh_grab':
            self.data_generator.refresh_time = param.value()


class MySaverLoaderWorker(ExtensionWorker):

    has_data_processor = True

    def __init__(self, app: MySaverLoader, parent=None):
        super().__init__(app=app, parent=parent)

        self._processor_worker_class = DataProcessor

    @property
    def processor_worker(self) -> DataProcessor:
        return self._processor_worker

    @property
    def app(self) -> MySaverLoader:
        return self._app

    def process_data(self):
        self.processor_worker.data_to_process_signal.emit(DataForProcessor(node_path='/RawData/mydata'))

    def _start(self):
        for worker_name in self.thread_manager.n_jobs:
            self.thread_manager.n_jobs[worker_name] = 0

        self.h5_manager.open_file()
        self.current_node: GROUP | str = self.app.h5saver.get_set_group('/RawData', 'mydata')

        self.data_generator = DataGenerator(parent=None)
        self.data_generator.refresh_time = self.settings['refresh_grab']

        # managing data generator worker
        self.thread_manager.create_thread_for_worker('data', self.data_generator)
        self.data_generator.data_signal.connect(self.send_data)
        self.thread_manager.start_thread('data')

        self.data_generator.command_signal.emit(ThreadCommand('start'))

        self.processor_worker.data_processed_signal.connect(self.show_data)

        QtCore.QTimer.singleShot(int(self.settings['refresh_plot']), self.process_data)
        self.app.enable_workflow_actions(False, excepted=('pause', 'stop'))

    def show_data(self, dte: DataToExport):
        self.thread_manager.n_jobs[ProcessorWorker.name] += 1
        self.app.viewer.show_data(dte)
        if self._running:
            QtCore.QTimer.singleShot(int(self.settings['refresh_plot']), self.process_data)

    def _stop(self, msg: str = None):
        """ Stop the timers and the data generation,
        stops/deletes also the saver worker when it saved all the data
        (_worker_done signal connect to terminate_worker)

        """
        self.data_generator.command_signal.emit(ThreadCommand('stop'))

        try:
            self.data_generator.data_signal.disconnect()
        except (TypeError, AttributeError):
            pass

    def _pause(self, do_pause=True):
        if do_pause:
            self.data_generator.command_signal.emit(ThreadCommand('stop'))

        else:
            self.data_generator.command_signal.emit(ThreadCommand('start'))
            self.process_data() # restart the processing loop!


    def send_data(self, dte: DataToExport):
        self.saver_worker.data_to_save_signal.emit(DataBundle(node=self.current_node, dte=dte))
        self.thread_manager.n_jobs[SaverWorker.name] += 1




def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('SaverLoader')
    win, area = make_window(title='SaverLoaderProcessor',)

    shared_ui = SharedUI(widget=win, title='SaverLoader')
    my_app = MySaverLoader(parent=area)
    shared_ui.affect_application(my_app)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
