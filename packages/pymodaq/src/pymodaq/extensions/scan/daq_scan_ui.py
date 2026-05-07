# -*- coding: utf-8 -*-
"""
Created the 06/12/2022

@author: Sebastien Weber
"""
from typing import List, TYPE_CHECKING

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal

from pymodaq.extensions.scan.scan_manager import ScanManager
from pymodaq_gui.utils.shared_ui import MenuToolbarNames
from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils import Dock
from pymodaq_gui.utils.widgets.spinbox import QSpinBox_ro
from pymodaq_gui.utils.widgets import QLED
from pymodaq_gui.plotting.data_viewers.viewer import ViewerDispatcher
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_gui.parameter import ParameterTree

if TYPE_CHECKING:

    from pymodaq.extensions.scan.daq_scan import DAQScan

logger = set_logger(get_module_name(__file__))


class DAQScanUI(CustomApp, ViewerDispatcher):
    """

    """
    command_sig = Signal(ThreadCommand)

    def __init__(self, parent, toolbar=None):
        CustomApp.__init__(self, parent, toolbar=toolbar)
        self.setup_docks_and_widgets()
        ViewerDispatcher.__init__(self, self.dockarea, title='Scanner',
                                  next_to_dock=self.dock_command)

        self.setup_menus_and_toolbars(self.menubar)
        self.setup_actions()
        self.connect_things()

    def enable_start_stop(self, enable=True):
        """If True enable main buttons to launch/stop scan"""
        self.set_action_enabled('start', enable)
        self.set_action_enabled('stop', enable)
        self.set_action_enabled('pause', enable)
        if enable:
            self.set_action_checked('pause', False)

    def setup_docks_and_widgets(self):
        self.dock_command = Dock('Scan Command')
        self.dockarea.addDock(self.dock_command)

        widget_command = QtWidgets.QWidget()
        widget_command.setLayout(QtWidgets.QVBoxLayout())
        self.dock_command.addWidget(widget_command)

        splitter_widget = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter_v_widget = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        widget_command.layout().addWidget(splitter_widget)
        splitter_widget.addWidget(splitter_v_widget)
        self.module_widget = QtWidgets.QWidget()
        self.module_widget.setLayout(QtWidgets.QVBoxLayout())
        self.module_widget.setMinimumWidth(220)
        self.module_widget.setMaximumWidth(400)

        self.plotting_widget = QtWidgets.QWidget()
        self.plotting_widget.setLayout(QtWidgets.QVBoxLayout())
        self.plotting_widget.setMinimumWidth(220)
        self.plotting_widget.setMaximumWidth(400)

        self.plotting_settings_tree = ParameterTree()
        self.plotting_widget.layout().addWidget(self.plotting_settings_tree)

        settings_widget = QtWidgets.QWidget()
        settings_widget.setLayout(QtWidgets.QVBoxLayout())
        settings_widget.setMinimumWidth(220)

        splitter_v_widget.addWidget(self.module_widget)
        splitter_v_widget.addWidget(self.plotting_widget)

        splitter_v_widget.setSizes([400, 400])
        splitter_widget.addWidget(settings_widget)

        self.populate_status_bar()

        self.settings_toolbox = QtWidgets.QToolBox()
        settings_widget.layout().addWidget(self.settings_toolbox)
        self.scanner_widget = QtWidgets.QWidget()
        self.scanner_widget.setLayout(QtWidgets.QVBoxLayout())
        self.settings_toolbox.addItem(self.scanner_widget, 'Scanner Settings')

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)
        self.add_menu('actions', 'Actions', parent_menu=menubar)

        self.add_toolbar('scan_manager', 'Scan Manager', parent=self.mainwindow,
                         add_break=False)
        self.add_menu('scan_manager', 'Scan Manager', MenuToolbarNames.TOOLS, icon_name=ScanManager.icon_name)

    def setup_actions(self):
        self.add_action('ini_positions', 'Init Positions', 'arrows_input', menu='actions')
        self.set_action_enabled('ini_positions', False)
        self.add_action('start', 'Start Scan', 'motion_play', "Start the scan",
                        menu='actions', icon_color=self.get_theme().green)
        self.add_action('start_batch', 'Start ScanBatches', 'run_all', "Start the batch of scans", menu='actions')
        self.add_action('stop', 'Stop Scan', 'stop_circle', "Stop the scan",
                        menu='actions', icon_color=self.get_theme().red)
        self.add_action('pause', 'Pause Scan', 'pause_circle', "Pause/resume the scan",
                        checkable=True, menu='actions',
                        icon_checked_color=self.get_theme().orange)
        self.add_action('move_at', 'Move at doubleClicked', 'moving',
                        "Move to positions where you double clicked", checkable=True, menu='actions')

        self._toolbar.addSeparator()
        self.add_action('show_file', 'Show file content', 'folder_data',
                        tip='Browse the content of the current HDF5 file')

        self.add_action('new_file', 'New file', 'new2', menu=MenuToolbarNames.FILE, auto_toolbar=False)
        self.add_action('load', 'Open file to append...', 'Open', menu=MenuToolbarNames.FILE, auto_toolbar=False)
        self.get_menu(MenuToolbarNames.FILE).addSeparator()
        self.add_action('save', 'Save copy as...', 'SaveAs', menu=MenuToolbarNames.FILE, auto_toolbar=False)
        # Debug-only actions: registered but not in any menu so they stay hidden from regular users.
        # A developer can access them programmatically or add them back to a menu as needed.
        self.add_action('open_file', 'Open current file', '', auto_toolbar=False)
        self.add_action('close_file', 'Close current file', '', auto_toolbar=False)

        self.add_action('navigator', 'Show Navigator', '', menu=MenuToolbarNames.TOOLS, auto_toolbar=False)
        self.add_action('batch', 'Show Batch Scanner', '', menu=MenuToolbarNames.TOOLS, auto_toolbar=False)
        self.set_action_visible('start_batch', False)

    def connect_things(self):
        self.connect_action('ini_positions', lambda: self.command_sig.emit(ThreadCommand('ini_positions')))
        self.connect_action('start', lambda: self.command_sig.emit(ThreadCommand('start')))
        self.connect_action('start_batch', lambda: self.command_sig.emit(ThreadCommand('start_batch')))
        self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand('stop')))
        self.connect_action('pause', lambda: self.command_sig.emit(ThreadCommand('pause')))
        self.connect_action('move_at', lambda: self.command_sig.emit(ThreadCommand('move_at')))

        self.connect_action('new_file', lambda: self.command_sig.emit(ThreadCommand('new_file')))
        self.connect_action('load', lambda: self.command_sig.emit(ThreadCommand('load')))
        self.connect_action('save', lambda: self.command_sig.emit(ThreadCommand('save')))
        self.connect_action('show_file', lambda: self.command_sig.emit(ThreadCommand('show_file')))
        self.connect_action('open_file', lambda: self.command_sig.emit(ThreadCommand('open_file')))
        self.connect_action('close_file', lambda: self.command_sig.emit(ThreadCommand('close_file')))
        self.connect_action('navigator', lambda: self.command_sig.emit(ThreadCommand('navigator')))
        self.connect_action('batch', lambda: self.command_sig.emit(ThreadCommand('batch')))

    def finalize_ui(self, app: 'DAQScan'):
        app.create_dashboard_toolbar()

        self.populate_toolbox_widget([app.settings_tree,
                                      app._h5saver.settings_tree],
                                     ['General Settings', 'Save Settings'])

        self.set_scanner_settings(app.scanner.parent_widget)
        self.set_modules_settings(app.modules_manager.settings_tree)

        self.plotting_settings_tree.setParameters(app.settings.child('plot_options'))

        for ind_menu, menu in enumerate(self.menus):
            app.reference_menu(self.menus_names[ind_menu], menu)

        for ind_toolbar, toolbar in enumerate(self.toolbars):
            app.reference_toolbar(self.toolbars_names[ind_toolbar], toolbar)

        self.enable_start_stop(False)

    def add_settings_toolbox_widget(self, widget: QtWidgets.QWidget, name: str):
        """Add a widget, usaually a ParameterTree to the SettingsToolbox"""
        self.settings_toolbox.addItem(widget, name)

    def add_scanner_settings(self, tree: 'ParameterTree'):
        """Adds a  ParameterTree to the Scanner settings widget"""
        self.scanner_widget.layout().addWidget(tree)

    def populate_toolbox_widget(self, widgets: List[QtWidgets.QWidget], names: List[str]):
        for widget, name in zip(widgets, names):
            self.settings_toolbox.addItem(widget, name)

    def set_scanner_settings(self, settings_tree: QtWidgets.QWidget):
        while True:
            child = self.scanner_widget.layout().takeAt(0)
            if not child:
                break
            child.widget().deleteLater()
            QtWidgets.QApplication.processEvents()

        self.scanner_widget.layout().addWidget(settings_tree)

    def set_modules_settings(self, settings_widget):
        self.module_widget.layout().addWidget(settings_widget)

    def populate_status_bar(self):
        self._status_message_label = QtWidgets.QLabel('Initializing')
        self._n_scan_steps_sb = QSpinBox_ro()
        self._n_scan_steps_sb.setToolTip('Total number of steps')
        self._indice_scan_sb = QSpinBox_ro()
        self._indice_scan_sb.setToolTip('Current step value')
        self._indice_average_sb = QSpinBox_ro()
        self._indice_average_sb.setToolTip('Current average value')
        
        self._scan_done_LED = QLED()
        self._scan_done_LED.set_as_false()
        self._scan_done_LED.clickable = False
        self._scan_done_LED.setToolTip('Scan done state')

        self._file_open_LED = QLED()
        self._file_open_LED.set_as_false()
        self._file_open_LED.clickable = False
        self._file_open_LED.setToolTip('H5 file open and accessible')

        self._swmr_label = QtWidgets.QLabel('')
        self._swmr_label.setToolTip('SWMR mode status')
        self._swmr_label.setVisible(False)

        self.statusbar.addPermanentWidget(self._status_message_label)

        self.statusbar.addPermanentWidget(self._n_scan_steps_sb)
        self.statusbar.addPermanentWidget(self._indice_scan_sb)
        self.statusbar.addPermanentWidget(self._indice_average_sb)
        self._indice_average_sb.setVisible(False)
        self.statusbar.addPermanentWidget(self._scan_done_LED)
        self.statusbar.addPermanentWidget(QtWidgets.QLabel('File:'))
        self.statusbar.addPermanentWidget(self._file_open_LED)
        self.statusbar.addPermanentWidget(self._swmr_label)

    @property
    def n_scan_steps(self):
        return self._n_scan_steps_sb.value()

    @n_scan_steps.setter
    def n_scan_steps(self, nsteps: int):
        self._n_scan_steps_sb.setValue(nsteps)

    def display_status(self, status: str, wait_time=1000):
        self.statusbar.showMessage(status, wait_time)
        
    def set_permanent_status(self, status: str):
        self._status_message_label.setText(status)

    def set_scan_step(self, step_ind: int):
        self._indice_scan_sb.setValue(step_ind)

    def show_average_step(self, show: bool = True):
        self._indice_average_sb.setVisible(show)

    def set_scan_step_average(self, step_ind: int):
        self._indice_average_sb.setValue(step_ind)

    def set_scan_done(self, done=True):
        self._scan_done_LED.set_as(done)

    def set_file_open(self, is_open: bool):
        """Update the file-open status LED.

        Parameters
        ----------
        is_open:
            True (green) if the h5 file is open and accessible, False (red) otherwise.
        """
        self._file_open_LED.set_as(is_open)

    def set_swmr_status(self, active: bool, compatible: bool = False):
        """Show or hide the SWMR mode indicator in the status bar.

        Parameters
        ----------
        active:
            True if SWMR mode is currently active on the file.
        compatible:
            True if the file was created with SWMR support.
        """
        if active:
            self._swmr_label.setText('SWMR')
            self._swmr_label.setToolTip('SWMR mode active')
            self._swmr_label.setVisible(True)
        elif compatible:
            self._swmr_label.setText('SWMR file')
            self._swmr_label.setToolTip('File created with SWMR support')
            self._swmr_label.setVisible(True)
        else:
            self._swmr_label.setText('')
            self._swmr_label.setToolTip('SWMR mode status')
            self._swmr_label.setVisible(False)

    def update_viewers(self, viewers_type: List[ViewersEnum], viewers_name: List[str] = None, force=False):
        super().update_viewers(viewers_type, viewers_name, force)
        self.command_sig.emit(ThreadCommand('viewers_changed', attribute=dict(viewer_types=self.viewer_types,
                                                                              viewers=self.viewers)))

