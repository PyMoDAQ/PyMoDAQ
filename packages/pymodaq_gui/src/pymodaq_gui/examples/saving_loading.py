import numpy as np
from pathlib import Path
from time import perf_counter
from typing import Iterable, TYPE_CHECKING, Union, Mapping

from qtpy import QtWidgets, QtCore

from pymodaq_gui.plotting.data_viewers import ViewerDispatcher
from pymodaq_gui.utils.widgets.window import make_window
from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand

from pymodaq_data import Q_, DataDim, DataSource, DataRaw
from pymodaq_data import DataToExport, DataWithAxes
from pymodaq_data.h5modules.data_saving import DataToExportTimedSaver, Node, GROUP

from pymodaq_gui import utils as gutils
from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.utils import DockArea, Dock
from pymodaq_gui.utils.shared_ui import MenuToolbarNames, SharedUI
from pymodaq_gui.utils.custom_app import CustomApp


logger = set_logger(get_module_name(__file__))
config = GlobalConfig()


class DataGenerator(QtCore.QObject):
    data_signal = QtCore.Signal(DataToExport)
    stopped = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.generate_data)

        self._refresh_time: int = None  # ms
        self.refresh_time = 100  #ms

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self.stopped.emit()

    @property
    def refresh_time(self) -> int:
        return self._refresh_time

    @refresh_time.setter
    def refresh_time(self, value: int):
        self._refresh_time = value
        is_active = self.timer.isActive()
        self.timer.stop()
        self.timer.setInterval(value)
        if is_active:
            self.timer.start()

    def generate_data(self) -> DataToExport:
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

        self.where = where

    @QtCore.Slot(DataToExport)
    def save_data(self, dte: DataToExport):

        self.saver.add_data(self.where, dte)
        self._n_saved += 1
        self.n_saved.emit(self._n_saved)


class MySaverLoader(CustomApp):
    send_data_signal = QtCore.Signal(DataToExport)
    _worker_done = QtCore.Signal()

    _h5_base_group_name = 'SaverExample'
    _show_h5file_statusbar_widgets = True
    params = [
        {'title': 'Refresh Grab:', 'name': 'refresh_grab', 'type': 'int', 'value': 50, 'suffix': 'ms',
         'siPrefix': False},
        {'title': 'Refresh Plot:', 'name': 'refresh_plot', 'type': 'int', 'value': 500, 'suffix': 'ms',
         'siPrefix': False},
        {'title': 'Worker:', 'name': 'worker', 'type': 'group', 'children': [
            {'title': 'Worker Running:', 'name': 'worker_running', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Worker tasks:', 'name': 'worker_tasks', 'type': 'int', 'value': 0, 'readonly': True},
        ]},
    ]

    def __init__(self, parent: gutils.DockArea):
        self.plotter = ViewerDispatcher(dockarea=parent)

        super().__init__(parent, add_toolbar_break=False)

        self.data_generator = DataGenerator()
        self.data_generator.refresh_time = self.settings['refresh_grab']

        self._n_emitted = 0

        self.plotter_timer = QtCore.QTimer()
        self.plotter_timer.timeout.connect(self.update_plotter)

        self._saver = DataToExportTimedSaver(self.h5saver)

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

        self.dockarea.addDock(self.settings_dock, 'left')
        self.dockarea.addDock(self.saving_dock, 'right', self.settings_dock)
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
        self.add_action('save', 'Save', 'save', toolbar=self.toolbar, checkable=True,
                        tip='Save data', checked=True, icon_checked_color=self.get_theme().green,
                        icon_color=self.get_theme().red)

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

    def update_plotter(self):
        pass
        #self.plotter.compute_plot()

    def start(self):

        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass

        if self.is_action_checked('save'):
            self.setup_saving()

            self.plotter_timer.setInterval(int(self.settings['refresh_plot']))

        self._n_emitted = 0

        if self.runner_thread is not None and self.runner_thread.isRunning():
            self.exit_runner_thread()

        if self.is_action_checked('save'):
            self.open_file()
            self.current_node: GROUP | str = self.h5saver.get_set_group('/RawData', 'mydata')
            self.runner_thread = QtCore.QThread()
            self.worker = SaverWorker(saver=self._saver, where=self.current_node)
            self.worker.n_saved.connect(self.update_worker_ntask)
            self.send_data_signal.connect(self.worker.save_data)
            self.worker.moveToThread(self.runner_thread)

        self.runner_thread.start()
        self.settings['worker', 'worker_running'] = True

        # connect data signals to the event loop of the worker thread
        self.data_generator.data_signal.connect(self.send_data)

        self.data_generator.start()

        if self.is_action_checked('save'):
            pass
            #self.histogramer_timer.start()
        self.enable_runflow_actions(False, excepted=('pause', 'stop'))

    def enable_runflow_actions(self, enable=True, excepted: Iterable[str] = ()):
        for action in ('start', 'pause', 'stop', 'save'):
            if action not in excepted:
                self.set_action_enabled(action, enable)

    def stop(self):
        """ Stop the timers and the data generation,
        stops/deletes also the saver worker when it saved all the data
        (_worker_done signal connect to terminate_worker)

        """
        self.data_generator.stop()

        if self.settings['worker', 'worker_tasks'] == 0:
            self.terminate_worker()
        else:
            self._worker_done.connect(self.terminate_worker)

    def terminate_worker(self):
        """ Will terminete/close/stops a few things when the worker is done working"""
        # stopping the plotting before flushing/closing the file
        self.plotter_timer.stop()

        # delete the worker and quit/delete the thread
        self.worker.deleteLater()
        self.exit_runner_thread() # stopping deleting the thread

        # flushing/closing the file to be able to create new groups...
        self.h5saver.flush()
        self.h5saver.close_file()
        self.update_file_status_led()

        # updating GUI info
        self.enable_runflow_actions(True)
        self.settings['worker', 'worker_running'] = False

    def pause(self, do_pause=True):
        if do_pause:
            self.data_generator.stop()
            self.plotter_timer.stop()

        else:
            self.data_generator.start()
            if self.is_action_checked('save'):
                self.plotter_timer.start()
                pass

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

    def send_data(self, dte: DataToExport):
        if self.is_action_checked('save'):

            self.send_data_signal.emit(dte)
            self._n_emitted += 1

    @QtCore.Slot(int)
    def update_worker_ntask(self, n_saved: int):
        n_tasks = self._n_emitted - n_saved
        self.settings['worker', 'worker_tasks'] = n_tasks

        if n_tasks == 0:
            self._worker_done.emit()

    def quit_fun(self):
        self.h5saver.flush()
        self.h5saver.close()
        self.plotter_timer.stop()

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
    area = DockArea()
    shared_ui = SharedUI(widget=area, title='SaverLoader')
    my_app = MySaverLoader(parent=area)
    shared_ui.affect_application(my_app)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
