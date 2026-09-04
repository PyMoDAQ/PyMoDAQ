import numpy as np
from pathlib import Path
from time import perf_counter
from typing import Iterable, TYPE_CHECKING, Union, Mapping

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt

from messenger import messagebox
from pymodaq_data.h5modules.backends import NodeError
from pymodaq_gui.plotting.data_viewers import ViewerDispatcher, ViewersEnum
from pymodaq_gui.utils.widgets.window import make_window
from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand

from pymodaq_data import Q_, DataDim, DataSource, DataRaw
from pymodaq_data import DataToExport, DataWithAxes
from pymodaq_data.h5modules.data_saving import DataToExportTimedSaver, Node, GROUP, DataLoader

from pymodaq_gui import utils as gutils
from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.utils import DockArea, Dock
from pymodaq_gui.utils.shared_ui import SharedUI
from pymodaq_gui.utils.enums import MenuToolbarNames
from pymodaq_gui.utils.custom_app import CustomApp


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


class SaverWorker(QtCore.QObject):
    """ Worker in separated thread receiving the data from a DataGenerator
    and adding them into the enlargeable arrays with the H5file using the
     DataToExportTimedSaver """

    n_saved = QtCore.Signal(int)

    def __init__(self, saver: DataToExportTimedSaver,
                 where: str | Node = '/RawData'):
        super().__init__()
        self.saver: DataToExportTimedSaver  = saver
        self._n_saved = 0
        self._show_thread = True
        self.where = where

    @QtCore.Slot(DataToExport)
    def save_data(self, dte: DataToExport):
        if self._show_thread:
            print(f'Saving data in Qthread{self.thread()}')
            self._show_thread = False
        self.saver.add_data(self.where, dte)
        self._n_saved += 1
        self.n_saved.emit(self._n_saved)


class DataProcessor(QtCore.QObject):
    data_processed = QtCore.Signal(DataToExport)
    process_data = QtCore.Signal(str)

    def __init__(self, h5saver: H5Saver, parent=None):
        super().__init__(parent)
        self.h5saver = h5saver
        self.data_loader = DataLoader(self.h5saver, swmr_mode=True)
        self.process_data.connect(self._do_process_data, Qt.ConnectionType.QueuedConnection)
        self._show_thread = True

    @QtCore.Slot(str)
    def _do_process_data(self, where: str):
        """ Process data here, Be aware that load_all try to load multiple nodes from the h5file but not at the same
        time (sequentially). In this multithreaded application, the saving could add data to a node in between the
        reading. What you expect to be data with same shape/size may not be True!

        If you want to avoid that effect, do the reading in the same thread that is saving the data, eventually sending
        then the loaded dte to this processor
        """
        try:
            if self._show_thread:
                print(f'Processing data in Qthread{self.thread()}')
                self._show_thread = False
            print(f'Processing data')
            dte = self.data_loader.load_all(where)
            if dte is not None and len(dte) == 2:
                QtCore.QThread.msleep(2000) # simulate heavy-duty calculation
                self.data_processed.emit(dte)
        except NodeError:
            pass


class MySaverLoader(CustomApp):
    send_data_signal = QtCore.Signal(DataToExport)
    _worker_done = QtCore.Signal()

    h5_base_group_name = 'SaverExample'
    show_h5file_statusbar_widgets = True
    params = [
        {'title': 'Refresh Grab:', 'name': 'refresh_grab', 'type': 'int', 'value': 50, 'suffix': 'ms',
         'siPrefix': False},
        {'title': 'Refresh Plot:', 'name': 'refresh_plot', 'type': 'int', 'value': 1000, 'suffix': 'ms',
         'siPrefix': False},
        {'title': 'Worker:', 'name': 'worker', 'type': 'group', 'children': [
            {'title': 'Worker Running:', 'name': 'worker_running', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Worker tasks:', 'name': 'worker_tasks', 'type': 'int', 'value': 0, 'readonly': True},
        ]},
    ]

    def __init__(self, parent: gutils.DockArea):

        super().__init__(parent, add_toolbar_break=False)

        self._n_emitted = 0
        self._running = False

        self._saver = DataToExportTimedSaver(self.h5saver)

        self.viewer: ViewerDispatcher = None

        self.data_processor: DataProcessor = None
        self.saver_worker: SaverWorker = None
        self.data_generator: DataGenerator =None

        self.current_node: GROUP | str = None
        self.setup_ui()

        self.enable_runflow_actions(True)

    def setup_saving(self):
        self.update_file_status_led()

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
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)
        self.add_menu('actions', 'Actions', parent_menu=menubar)

    def do_things_after_ui_setup(self):
        pass

    def setup_actions(self):
        """Method where to create actions to be subclassed. Mandatory

        See Also
        --------
        ActionManager.add_action
        """
        self.add_action('start', 'Start', 'motion_play', "Start the Ramping",
                        menu='actions',
                        icon_color=self.get_theme().green, toolbar=self.toolbar)
        self.add_action('stop', 'Stop', 'stop_circle', "Stop the Ramping",
                        menu='actions',
                        icon_color=self.get_theme().red, toolbar=self.toolbar)
        self.add_action('pause', 'Pause', 'pause_circle',
                        menu='actions', tip="Pause/resume the Ramping",
                        checkable=True, toolbar=self.toolbar,
                        icon_checked_color=self.get_theme().orange)
        self._toolbar.addSeparator()
        self.add_action('show_file', 'Show file content', 'folder_data',
                        tip='Browse the content of the current HDF5 file')

        self.add_action('new_file', 'New file', 'add_circle', menu=MenuToolbarNames.FILE, auto_toolbar=False)
        self.add_action('load', 'Open file to append...', 'file_open', menu=MenuToolbarNames.FILE, auto_toolbar=False)
        self.get_menu(MenuToolbarNames.FILE).addSeparator()

        self.add_action('show_saving', 'Show Saving Options', 'settings',
                        menu=MenuToolbarNames.TOOLS, checkable=True,
                        toolbar=self.toolbar, tip='Display in a Dock the Saving Settings')

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action('start', self.start)
        self.connect_action('stop', self.stop)
        self.connect_action('pause', self.pause)

        self.connect_action('new_file', self.create_new_file)
        self.connect_action('load', lambda: self.load_file())

        self.connect_action('show_file', self.show_file_content)

        self.connect_action('show_saving', lambda show: self.saving_dock.setVisible(show))

    def process_data(self):
        self.data_processor.process_data.emit('/RawData/mydata')

    def start(self):
        self._running = True
        print(f'Main Qthread: {self.thread()}')
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass

        self.setup_saving()
        self._n_emitted = 0

        self.open_file()
        self.current_node: GROUP | str = self.h5saver.get_set_group('/RawData', 'mydata')

        self.data_generator = DataGenerator(parent=None)
        self.data_generator.refresh_time = self.settings['refresh_grab']

        self.data_processor = DataProcessor(self.h5saver, parent=None)

        # managing saver worker
        self.saver_worker = SaverWorker(saver=self._saver, where=self.current_node)
        self.thread_manager.create_thread_for_worker('saver', self.saver_worker)
        self.saver_worker.n_saved.connect(self.update_worker_ntask)
        self.send_data_signal.connect(self.saver_worker.save_data)
        self.thread_manager.start_thread('saver')


        # managing data generator worker
        self.thread_manager.create_thread_for_worker('data', self.data_generator)
        self.data_generator.data_signal.connect(self.send_data)
        self.thread_manager.start_thread('data')

        self.data_generator.command_signal.emit(ThreadCommand('start'))


        #managing processor worker
        self.thread_manager.create_thread_for_worker('processor', self.data_processor)
        self.data_processor.data_processed.connect(self.show_data)
        self.thread_manager.start_thread('processor')

        self.settings['worker', 'worker_running'] = True
        QtCore.QTimer.singleShot(int(self.settings['refresh_plot']), self.process_data)
        self.enable_runflow_actions(False, excepted=('pause', 'stop'))

    def show_data(self, dte: DataToExport):
        self.viewer.show_data(dte)
        if self._running:
            QtCore.QTimer.singleShot(int(self.settings['refresh_plot']), self.process_data)

    def enable_runflow_actions(self, enable=True, excepted: Iterable[str] = ()):
        for action in ('start', 'pause', 'stop'):
            if action not in excepted:
                self.set_action_enabled(action, enable)

    def stop(self):
        """ Stop the timers and the data generation,
        stops/deletes also the saver worker when it saved all the data
        (_worker_done signal connect to terminate_worker)

        """
        self._running = False
        self.data_generator.command_signal.emit(ThreadCommand('stop'))
        self.set_action_checked('pause', False)

        try:
            self.data_generator.data_signal.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.data_processor.data_processed.disconnect()
        except (TypeError, AttributeError):
            pass

        if self.settings['worker', 'worker_tasks'] == 0:
            self.terminate_worker()
        else:
            self._worker_done.connect(self.terminate_worker)

    def terminate_worker(self):
        """ Will terminete/close/stops a few things when the worker is done working"""
        # stopping the plotting before flushing/closing the file
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass

        self.thread_manager.exit_worker_thread('data', delete_worker=True)
        self.thread_manager.exit_worker_thread('processor', delete_worker=True)
        self.thread_manager.exit_worker_thread('saver', delete_worker=True)

        # flushing/closing the file to be able to create new groups...
        self.h5saver.flush()
        self.h5saver.close_file()
        self.update_file_status_led()

        # updating GUI info
        self.enable_runflow_actions(True)
        self.settings['worker', 'worker_running'] = False

    def pause(self, do_pause=True):
        if do_pause:
            self._running = False  # will stop the processing loop
            self.data_generator.command_signal.emit(ThreadCommand('stop'))

        else:
            self._running = True
            self.data_generator.command_signal.emit(ThreadCommand('start'))
            self.process_data() # restart the processing loop!

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
        elif param.name() == 'refresh_plot':
            self.processor_timer.stop()
            self.processor_timer.setInterval(int(self.settings['refresh_plot']))
            self.processor_timer.start()

    def send_data(self, dte: DataToExport):
        self.send_data_signal.emit(dte)
        self._n_emitted += 1

    @QtCore.Slot(int)
    def update_worker_ntask(self, n_saved: int):
        n_tasks = self._n_emitted - n_saved
        self.settings['worker', 'worker_tasks'] = n_tasks

        if n_tasks == 0:
            self._worker_done.emit()

    def quit_fun(self):
        """ Do things to clean your app and return True if ok or False (or None) if not.

        If your custom app is wrapped in a SharedUI,
        the sharedUI will handle the main window closing
        """

        if self._running:
            messagebox(title='Running',
                       text='The Acquisition is running, first stop it')
            return
        elif self.settings['worker', 'worker_tasks'] > 0:
            messagebox(title='Running',
                       text='The Saver is finishing the savings')
            self.stop()
            return

        self.h5saver.flush()
        self.h5saver.close()

        super().quit_fun()

    def get_app_toolbars(self) -> list[QtWidgets.QToolBar]:
        """ Get the main toolbars widget to be eventually added in the main window toolbararea

        Default is the default toolbar. To be reimplemented if needed
        """
        return [self.toolbar]


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
