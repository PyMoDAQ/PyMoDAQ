# -*- coding: utf-8 -*-
"""
Created the 05/09/2022

@author: Sebastien Weber
"""


from typing import List
import sys

from qtpy import QtWidgets
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QVBoxLayout,  QWidget, QComboBox
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.control_modules.utils import ControlModuleUI

from pymodaq_gui.utils.widgets import PushButtonIcon, LabelWithFont, QLED
from pymodaq_gui.utils import Dock
from pymodaq_utils.config import Config
from pymodaq.control_modules.utils import DET_TYPES, DAQTypesEnum
from pymodaq_gui.plotting.data_viewers.viewer import ViewerFactory, ViewerDispatcher
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_utils.enums import enum_checker


viewer_factory = ViewerFactory()
config = Config()


class DAQ_Viewer_UI(ControlModuleUI, ViewerDispatcher):
    """DAQ_Viewer user interface.

    This class manages the UI and emit dedicated signals depending on actions from the user

    Attributes
    ----------
    command_sig: Signal[Threadcommand]
        This signal is emitted whenever some actions done by the user has to be
        applied on the main module. Possible commands are:
            * init
            * quit
            * grab
            * snap
            * stop
            * show_log
            * detector_changed
            * daq_type_changed
            * save_current
            * save_new

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

    def __init__(self, parent, title="DAQ_Viewer", daq_type='DAQ2D', dock_settings=None, dock_viewer=None):
        ControlModuleUI.__init__(self, parent)
        ViewerDispatcher.__init__(self, self.dockarea, title=title, next_to_dock=dock_settings)

        self.title = title

        self._detector_widget = None
        self._settings_widget = None
        self._info_detector = None
        self._daq_types_combo = None
        self._detectors_combo = None
        self._ini_det_pb = None
        self._ini_state_led = None
        self._do_bkg_cb = None
        self._take_bkg_pb = None
        self._settings_dock = dock_settings
        self.setup_docks()

        daq_type = enum_checker(DAQTypesEnum, daq_type)
        self.daq_types = daq_type.names()  # init the combobox through the daq_types attribute
        self.daq_type = daq_type

        self.detectors = [det['name'] for det in DET_TYPES[self.daq_type.name]]
        self.setup_actions()  # see ActionManager MixIn class
        self.add_viewer(self.daq_type.to_viewer_type(), dock_viewer=dock_viewer)
        self.connect_things()

        self._enable_grab_buttons(False)
        self._detector_widget.setVisible(False)
        self._settings_widget.setVisible(False)

    @property
    def detector(self):
        return self._detectors_combo.currentText()

    @detector.setter
    def detector(self, det_name: str):
        self._detectors_combo.setCurrentText(det_name)
    @property
    def detectors(self):
        return [self._detectors_combo.itemText(ind) for ind in range(self._detectors_combo.count())]

    @detectors.setter
    def detectors(self, detectors: List[str]):
        #self._detectors_combo.currentTextChanged.disconnect()
        self._detectors_combo.clear()
        self._detectors_combo.addItems(detectors)
        #self._detectors_combo.currentTextChanged.connect(
        #    lambda mod: self.command_sig.emit(ThreadCommand('detector_changed', mod)))
        #self.detector = detectors[0]

    @property
    def daq_type(self):
        return DAQTypesEnum[self._daq_types_combo.currentText()]

    @daq_type.setter
    def daq_type(self, dtype: DAQTypesEnum):
        dtype = enum_checker(DAQTypesEnum, dtype)
        self._daq_types_combo.setCurrentText(dtype.name)

    @property
    def daq_types(self):
        return self.daq_type.names()

    @daq_types.setter
    def daq_types(self, dtypes: List[str]):
        self._daq_types_combo.clear()
        self._daq_types_combo.addItems(dtypes)
        self.daq_type = DAQTypesEnum[dtypes[0]]

    def close(self):
        for dock in self.viewer_docks:
            dock.close()
        self._settings_dock.close()

    def setup_docks(self):
        if self._settings_dock is None:
            self._settings_dock = Dock(self.title + "_Settings", size=(150, 250))
            self.dockarea.addDock(self._settings_dock)

        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        #widget.layout().setSizeConstraint(QHBoxLayout.SetFixedSize)
        widget.layout().setContentsMargins(2, 2, 2, 2)
        self._settings_dock.addWidget(widget)

        info_ui = QWidget()
        self._detector_widget = QWidget()
        self._settings_widget = QWidget()
        self._settings_widget.setLayout(QtWidgets.QVBoxLayout())
        bkg_widget = QWidget()
        bkg_widget.setLayout(QtWidgets.QHBoxLayout())

        widget.layout().addWidget(info_ui)
        widget.layout().addWidget(self.toolbar)
        widget.layout().addWidget(self._detector_widget)
        widget.layout().addWidget(self._settings_widget)
        widget.layout().addStretch(0)

        info_ui.setLayout(QtWidgets.QHBoxLayout())
        info_ui.layout().addWidget(LabelWithFont(self.title, font_name="Tahoma", font_size=14, isbold=True,
                                                 isitalic=True))
        self._info_detector = LabelWithFont('', font_name="Tahoma", font_size=8, isbold=True, isitalic=True)
        info_ui.layout().addWidget(self._info_detector)

        self._detector_widget.setLayout(QtWidgets.QGridLayout())
        self._daq_types_combo = QComboBox()
        self._daq_types_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._detectors_combo = QComboBox()
        self._detectors_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._ini_det_pb = PushButtonIcon('ini', 'Init. Detector', True, 'Initialize selected detector')
        self._ini_state_led = QLED(readonly=True)
        self._do_bkg_cb = QtWidgets.QCheckBox('Do Bkg')
        self._take_bkg_pb = QtWidgets.QPushButton('Take Bkg')
        self._take_bkg_pb.setChecked(False)

        self._detector_widget.layout().addWidget(LabelWithFont('DAQ type:'), 0, 0)
        self._detector_widget.layout().addWidget(self._daq_types_combo, 0, 1)
        self._detector_widget.layout().addWidget(LabelWithFont('Detector:'), 1, 0)
        self._detector_widget.layout().addWidget(self._detectors_combo, 1, 1)
        self._detector_widget.layout().addWidget(self._ini_det_pb, 0, 2)
        self._detector_widget.layout().addWidget(self._ini_state_led, 1, 2)
        self._detector_widget.layout().addWidget(bkg_widget, 2, 0, 1, 3)

        bkg_widget.layout().addWidget(self._do_bkg_cb)
        bkg_widget.layout().addWidget(self._take_bkg_pb)

        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setMaximumHeight(30)
        widget.layout().addWidget(self.statusbar)

    def add_setting_tree(self, tree):
        self._settings_widget.layout().addWidget(tree)

    def setup_actions(self):
        self.add_action('grab', 'Grab', 'run2', "Grab data from the detector", checkable=True)
        self.add_action('snap', 'Snap', 'snap', "Take a snapshot from the detector")
        self.add_action('stop', 'Stop', 'stop', "Stop grabing")
        self.add_action('save_current', 'Save Current Data', 'SaveAs', "Save Current Data")
        self.add_action('save_new', 'Save New Data', 'Snap&Save', "Save New Data")
        self.add_action('open', 'Load Data', 'Open', "Load Saved Data")

        self.add_action('show_controls', 'Show Controls', 'Settings', "Show Controls to set DAQ and Detector type",
                        checkable=True)
        self.add_action('show_settings', 'Show Settings', 'tree', "Show Settings", checkable=True)

        self.add_action('quit', 'Quit the module', 'close2')
        self.add_action('show_config', 'Show Config', 'Settings', "Show PyMoDAQ Config", checkable=False,
                        toolbar=self.toolbar)
        self.add_action('log', 'Show Log file', 'information2')

        self._data_ready_led = QLED(readonly=True)
        self.toolbar.addWidget(self._data_ready_led)

    def connect_things(self):
        self.connect_action('show_controls', lambda show: self._detector_widget.setVisible(show))
        self.connect_action('show_settings', lambda show: self._settings_widget.setVisible(show))
        self.connect_action('quit', lambda: self.command_sig.emit(ThreadCommand('quit', )))
        self.connect_action('show_config', lambda: self.command_sig.emit(ThreadCommand('show_config', )))

        self.connect_action('log', lambda: self.command_sig.emit(ThreadCommand('show_log', )))
        self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand('stop', )))
        self.connect_action('stop', lambda: self.get_action('grab').setChecked(False))
        self.connect_action('stop', lambda: self._enable_ini_buttons(True))
        self.connect_action('stop', lambda: self._settings_widget.setEnabled(True))

        self.connect_action('grab', self._grab)
        self.connect_action('snap', lambda: self.command_sig.emit(ThreadCommand('snap', )))

        self.connect_action('save_current', lambda: self.command_sig.emit(ThreadCommand('save_current', )))
        self.connect_action('save_new', lambda: self.command_sig.emit(ThreadCommand('save_new', )))
        self.connect_action('open', lambda: self.command_sig.emit(ThreadCommand('open', )))

        self._ini_det_pb.clicked.connect(self.send_init)

        self._detectors_combo.currentTextChanged.connect(
            lambda mod: self.command_sig.emit(ThreadCommand('detector_changed', mod)))
        self._daq_types_combo.currentTextChanged.connect(self._daq_type_changed)


        self._do_bkg_cb.clicked.connect(lambda checked: self.command_sig.emit(ThreadCommand('do_bkg', checked)))
        self._take_bkg_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand('take_bkg')))

    def update_viewers(self, viewers_type: List[ViewersEnum]):
        super().update_viewers(viewers_type)
        self.command_sig.emit(ThreadCommand('viewers_changed', attribute=dict(viewer_types=self.viewer_types,
                                                                              viewers=self.viewers)))

    @property
    def data_ready(self):
        return self._data_ready_led.get_state()

    @data_ready.setter
    def data_ready(self, status):
        self._data_ready_led.set_as(status)

    def _daq_type_changed(self, daq_type: DAQTypesEnum):
        try:
            daq_type = enum_checker(DAQTypesEnum, daq_type)

            self.command_sig.emit(ThreadCommand('daq_type_changed', daq_type))
            if self.viewer_types != [daq_type.to_viewer_type()]:
                self.update_viewers([daq_type.to_viewer_type()])
        except ValueError as e:
            pass

    def show_settings(self, show=True):
        if (self.is_action_checked('show_settings') and not show) or \
                (not self.is_action_checked('show_settings') and show):
            self.get_action('show_settings').trigger()
            
    def show_controls(self, show=True):
        if (self.is_action_checked('show_controls') and not show) or \
                (not self.is_action_checked('show_controls') and show):
            self.get_action('show_controls').trigger()

    def _grab(self):
        """Slot from the *grab* action"""
        self.command_sig.emit(ThreadCommand('grab', attribute=self.is_action_checked('grab')))
        self._enable_ini_buttons(not self.is_action_checked('grab'))
        if not self.config('viewer', 'allow_settings_edition'):
            self._settings_widget.setEnabled(not self.is_action_checked('grab'))

    def do_init(self, do_init=True):
        """Programmatically press the Init button
        API entry
        Parameters
        ----------
        do_init: bool
            will fire the Init button depending on the argument value and the button check state
        """
        if do_init is not self._ini_det_pb.isChecked():
            self._ini_det_pb.click()

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
        """Programmatically press the Stop button
        API entry
        """
        self.get_action('stop').trigger()
        if self.is_action_checked('grab'):
            self.get_action('grab').trigger()

    def send_init(self, checked: bool):
        self._enable_detchoices(not checked)
        self.command_sig.emit(ThreadCommand('init', [checked,
                                                     self._daq_types_combo.currentText(),
                                                     self._detectors_combo.currentText()]))

    def _enable_detchoices(self, enable=True):
        self._detectors_combo.setEnabled(enable)
        self._daq_types_combo.setEnabled(enable)

    @property
    def detector_init(self):
        """bool: the status of the init LED."""
        return self._ini_state_led.get_state()

    @detector_init.setter
    def detector_init(self, status):
        if status:
            self._info_detector.setText(f'{self.daq_type.name} : {self.detector}')
        else:
            self._info_detector.setText('')
        self._ini_state_led.set_as(status)
        self._enable_grab_buttons(status)

    def _enable_grab_buttons(self, status):
        self.get_action('grab').setEnabled(status)
        self.get_action('snap').setEnabled(status)
        self.get_action('stop').setEnabled(status)
        self.get_action('save_current').setEnabled(status)
        self.get_action('save_new').setEnabled(status)

    def _enable_ini_buttons(self, status):
        self._ini_det_pb.setEnabled(status)
        self.get_action('quit').setEnabled(status)


def main(init_qt=True):
    from pymodaq.utils.gui_utils.dock import DockArea
    from pymodaq.utils.parameter import ParameterTree, Parameter
    from pymodaq.control_modules.viewer_utility_classes import params as daq_viewer_params

    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

    param = Parameter.create(name='settings', type='group', children=daq_viewer_params)
    tree = ParameterTree()
    tree.setParameters(param, showTop=False)

    dockarea = DockArea()
    prog = DAQ_Viewer_UI(dockarea)
    dockarea.show()

    def print_command_sig(cmd_sig):
        print(cmd_sig)
        prog.display_status(str(cmd_sig))
        if cmd_sig.command == 'init':
            prog._enable_grab_buttons(cmd_sig.attribute[0])
            prog.detector_init = cmd_sig.attribute[0]

    # prog.detectors = detectors
    prog.command_sig.connect(print_command_sig)

    prog.add_setting_tree(tree)

    prog.update_viewers([ViewersEnum['Viewer0D'], ViewersEnum['Viewer1D'], ViewersEnum['Viewer2D']])

    if init_qt:
        sys.exit(app.exec_())
    return prog, dockarea


if __name__ == '__main__':
    main()
