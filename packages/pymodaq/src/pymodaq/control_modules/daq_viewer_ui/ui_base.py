# -*- coding: utf-8 -*-
"""
Created the 05/09/2022

@author: Sebastien Weber
"""


from typing import List, Union
import sys

from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QVBoxLayout,  QWidget, QComboBox

import qt_themes

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.control_modules.ui_utils import ControlModuleUI

from pymodaq_gui.utils.widgets import PushButtonIcon, LabelWithFont, QLED
from pymodaq_gui.utils import Dock, DockArea
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.enums import StrEnum
from pymodaq.control_modules.instruments import DET_TYPES, DAQTypesEnum
from pymodaq_gui.plotting.data_viewers.viewer import ViewerFactory, ViewerDispatcher
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_gui.utils.styling import create_icon
from pymodaq_utils.enums import enum_checker
from pymodaq.control_modules.thread_commands import UiToMainViewer
from pymodaq.control_modules.control_module_selector import add_category_layers
from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule, ViewerSelector

viewer_factory = ViewerFactory()
config = Config()


options = {
    'DAQ0D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ0D']]],
    'DAQ1D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ1D']]],
    'DAQ2D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ2D']]],
    'DAQND': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQND']]],
}
add_menu_entries = add_category_layers(options)


class ActionIconNames(StrEnum):
    SNAP = 'looks_one'
    GRAB = 'repeat'
    GRAB_STOP = 'repeat_on'
    INI = 'cable'


class DAQ_Viewer_UI(ControlModuleUI, ViewerDispatcher):
    """DAQ_Viewer user interface.

    This class manages the UI and emit dedicated signals depending on actions from the user

    Attributes
    ----------
    command_sig: Signal[Threadcommand]
        This signal is emitted whenever some actions done by the user has to be
        applied on the main module. Possible commands are:
            * init
            * grab
            * snap
            * detector_changed
            * daq_type_changed
            * save_current

    Methods
    -------
    display_value(value: float)
        Update the display of the actuator's value on the UI
    do_init()
        Programmatic init

    See Also
    --------
    pymodaq.utils.daq_utils.ThreadCommand
    """

    command_sig = Signal(ThreadCommand)

    def __init__(self, parent: QtWidgets.QWidget, title="DAQ_Viewer", **kwargs):
        ControlModuleUI.__init__(self, parent)

        self.dockarea = DockArea()

        ViewerDispatcher.__init__(self, self.dockarea, title=title)

        self.title = title

        self._ini_state = False
        self._data_ready = False

        self._detector_widget = None
        self._settings_widget = None

        self.selector = ViewerSelector(add_menu_entries=add_menu_entries)

        self.setup_docks()

        self.setup_actions()  # see ActionManager MixIn class
        self.update_viewers([self.selector.selected_module.daq_type.to_viewer_type()])
        self.connect_things()

        self.enable_actions(False, all_except=('ini_detector', 'selector', 'show_settings', 'show_graphs'))
        self._settings_widget.setVisible(False)

    @property
    def detector(self) -> SelectedModule:
        return self.selector.selected_module

    @detector.setter
    def detector(self, det: SelectedModule):
        self.selector.selected_module = det

    def close(self):
        for dock in self.viewer_docks:
            dock.close()
        self._settings_widget.close()

    def setup_docks(self):
        widget = self.parent

        layout = QVBoxLayout()
        widget.setLayout(layout)
        layout.setContentsMargins(2, 2, 2, 2)
        self._settings_widget = QWidget()
        self._settings_widget.setLayout(QtWidgets.QVBoxLayout())

        layout.addWidget(self.dockarea)

    def add_setting_tree(self, tree):
        self._settings_widget.layout().addWidget(tree)

    def setup_actions(self):
        # Common actions from ControlModuleUI
        self._setup_name_widget(toolbar=self.toolbar)
        self.add_widget('selector', self.selector.add_widget)
        self._setup_init_action(action_name='ini_detector', display_name='Ini. Detector',
                                tip='Connect to selected detector')
        self._setup_settings_action()
        self.toolbar.addSeparator()

        # Detector-specific actions
        self.add_action('snap', 'Snap', ActionIconNames.SNAP, "Take a snapshot from the detector")
        self.add_action('grab', 'Grab', ActionIconNames.GRAB, "Grab data from the detector", checkable=True,
                        icon_checked=ActionIconNames.GRAB_STOP,
                        icon_checked_color=self.get_theme().green)
        self.add_action('show_graphs', 'ShowGraphs', 'bid_landscape', 'Show/Hide the Graphs Area',
                        checkable=True, icon_checked='bid_landscape_disabled',
                        icon_color=self.get_theme().green, icon_checked_color=self.get_theme().red)
        self.add_action('save_current', 'Save Current Data', 'save_as', "Save Current Data")
        self.toolbar.addSeparator()
        self.add_action('background_snap', 'Snap Background', 'background_replace',
                        tip='Take a snapshot a set it as background')
        self.add_action('background_subtract', 'Subtract Background', 'texture_minus', checkable=True,
                        tip='If checked, apply background substraction',
                        icon_checked_color=self.get_theme().green)

    def connect_things(self):
        self.connect_action('show_settings', self._show_settings)

        self.connect_action('grab', self._grab)
        self.connect_action('snap', lambda: self.command_sig.emit(ThreadCommand(UiToMainViewer.SNAP, )))

        self.connect_action('save_current', lambda: self.command_sig.emit(ThreadCommand(UiToMainViewer.SAVE_CURRENT, )))
        self.connect_action('ini_detector', self.send_init)

        self.selector.module_changed.connect(self._detector_changed)
        self.connect_action('background_subtract',
                            lambda checked: self.command_sig.emit(ThreadCommand(UiToMainViewer.DO_BKG, checked)))
        self.connect_action('background_snap',
                            lambda: self.command_sig.emit(ThreadCommand(UiToMainViewer.TAKE_BKG)))
        self.connect_action('show_graphs', lambda checked: self.show_graphs(not checked))

    def show_graphs(self, show: bool = True):
        self.parent.setVisible(show)
        self.parent.closeEvent = lambda event: self.set_action_checked('show_graphs', False)

    def _show_settings(self, show: bool = True):
        self._settings_widget.setVisible(show)
        self._settings_widget.closeEvent = lambda event: self.set_action_checked('show_settings', False)

    def update_viewers(self, viewers_type: List[Union[str, ViewersEnum]],
                       viewers_name: List[str] = None, force=False):
        super().update_viewers(viewers_type)
        self.command_sig.emit(ThreadCommand(UiToMainViewer.VIEWERS_CHANGED,
                                            attribute=dict(viewer_types=self.viewer_types,
                                                           viewers=self.viewers)))

    @property
    def data_ready(self):
        return self._data_ready

    @data_ready.setter
    def data_ready(self, status):
        self._data_ready = status
        if status:
            icon = create_icon(ActionIconNames.SNAP,
                               icon_color=self.get_theme().green,)
        else:
            icon = create_icon(ActionIconNames.SNAP,
                               icon_color=self.get_theme().red,)
        self.get_action('snap').set_icon(icon)

    def _detector_changed(self, sel_mod: SelectedModule):
        try:
            self.command_sig.emit(ThreadCommand(UiToMainViewer.DETECTOR_CHANGED, sel_mod))
            if self.viewer_types != [sel_mod.daq_type.to_viewer_type()]:
                self.update_viewers([sel_mod.daq_type.to_viewer_type()])
        except ValueError as e:
            pass

    def show_settings(self, show=True):
        if (self.is_action_checked('show_settings') and not show) or \
                (not self.is_action_checked('show_settings') and show):
            self.get_action('show_settings').trigger()

    def _grab(self):
        """Slot from the *grab* action"""
        self.command_sig.emit(ThreadCommand(UiToMainViewer.GRAB, attribute=self.is_action_checked('grab')))
        self.enable_actions(not self.is_action_checked('grab'),
                            all_except=('grab', 'selector', 'show_settings', 'show_graphs'))

        if not self.config('pymodaq', 'viewer', 'allow_settings_edition'):
            self._settings_widget.setEnabled(not self.is_action_checked('grab'))

    def do_init(self, do_init=True):
        """Programmatically press the Init button
        API entry
        Parameters
        ----------
        do_init: bool
            will fire the Init button depending on the argument value and the button check state
        """
        if do_init is not self.is_action_checked('ini_detector'):
            self.get_action('ini_detector').trigger()

    def do_grab(self, do_grab=True):
        """Programmatically press the Grab button
        API entry
        Parameters
        ----------
        do_grab: bool
            will fire the Init button depending on the argument value and the button check state
        """
        if (do_grab and not self.is_action_checked('grab')) or ((not do_grab) and self.is_action_checked('grab')):
            self.get_action('grab').trigger()

    def do_snap(self):
        """Programmatically press the Snap button
        API entry
        """
        self.get_action('snap').trigger()

    def do_stop(self):
        """Programmatically uncheck the grab button
        API entry
        """
        if self.is_action_checked('grab'):
            self.get_action('grab').trigger()

    def send_init(self, checked: bool):
        self._enable_detchoices(not checked)
        if not checked and self.is_action_checked('background_subtract'):
            self.get_action('background_subtract').trigger()
        QtWidgets.QApplication.processEvents()
        self.command_sig.emit(ThreadCommand(UiToMainViewer.INIT,
                                            [checked,
                                             self.selector.selected_module]))

    def _enable_detchoices(self, enable=True):
        self.get_action('selector').widget.setEnabled(enable)

    @property
    def detector_init(self):
        """bool: the internal init status."""
        return self._ini_state

    @detector_init.setter
    def detector_init(self, status):
        self._ini_state = status
        self.enable_actions(status, all_except=('ini_detector', 'selector', 'show_settings', 'show_graphs'))
        self.set_action_enabled('selector', not status)
        self.update_init_icon(status, action_name='ini_detector')

    def enable_actions(self, status=True, all_except=()):
        for action in self.actions_names:
            if action not in all_except:
                self.set_action_enabled(action, status)


def main(init_qt=True):
    from pymodaq_gui.parameter import Parameter, ParameterTree
    from pymodaq.control_modules.viewer_utility_classes import params as daq_viewer_params
    from pymodaq.utils.shared_ui import SharedUI
    from pymodaq_gui.qt_utils import mkQApp

    if init_qt:  # used for the test suite
        app = mkQApp("PyMoDAQ UI Viewer")

    param = Parameter.create(name='settings', type='group', children=daq_viewer_params)
    tree = ParameterTree()
    tree.setParameters(param, showTop=False)



    widget = QtWidgets.QWidget()
    prog = DAQ_Viewer_UI(widget, title='myViewer')
    shared_ui = SharedUI(widget)

    timer = QtCore.QTimer(shared_ui)

    def set_data_ready(ready=True):
        prog.data_ready = True

    def set_data_ready_loop(ready=True):
        prog.data_ready = True
        app.processEvents()
        QtCore.QThread.msleep(100)
        prog.data_ready = False
        app.processEvents()

    def print_command_sig(cmd_sig):
        print(cmd_sig)
        prog.display_status(str(cmd_sig))
        if cmd_sig.command == UiToMainViewer.INIT:
            prog.detector_init = cmd_sig.attribute[0]
        elif cmd_sig.command == UiToMainViewer.SNAP:
            prog.data_ready = False
            timer.timeout.connect(set_data_ready)
            timer.setSingleShot(True)
            timer.start(500)

        elif cmd_sig.command == UiToMainViewer.GRAB:
            prog.data_ready = False
            if cmd_sig.attribute:
                timer.timeout.connect(set_data_ready_loop)
                timer.setSingleShot(False)
                timer.start(500)
            else:
                timer.stop()


    # prog.detectors = detectors
    prog.command_sig.connect(print_command_sig)

    prog.add_setting_tree(tree)

    #prog.update_viewers([prog.selector.selected_module.daq_type.to_viewer_type()])

    shared_ui.add_toolbar('viewer', 'Viewer', toolbar=prog.toolbar, add_break=True)

    shared_ui.show()


    if init_qt:
        sys.exit(app.exec())


if __name__ == '__main__':
    main()
