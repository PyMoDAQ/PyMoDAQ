# -*- coding: utf-8 -*-
"""
Created the 05/09/2022

@author: Sebastien Weber
"""


from typing import List
import sys

from qtpy import QtWidgets
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QToolBar, QComboBox

from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_utils.gui_utils.custom_app import CustomApp
from pymodaq.daq_utils.gui_utils.widgets import PushButtonIcon, LabelWithFont, SpinBox, QSpinBox_ro, QLED
from pymodaq.daq_utils.gui_utils import DockArea, Dock


class DAQ_Viewer_UI(CustomApp):
    """DAQ_Viewer user interface.

    This class manages the UI and emit dedicated signals depending on actions from the user

    Attributes
    ----------
    command_sig: Signal[Threadcommand]
        This signal is emitted whenever some actions done by the user has to be
        applied on the main module. Possible commands are:
            * init
            * quit
            * get_value
            * loop_get_value
            * find_home
            * stop
            * move_abs
            * move_rel
            * show_log
            * actuator_changed
            * rel_value

    Methods
    -------
    display_value(value: float)
        Update the display of the actuator's value on the UI
    do_init()
        Programmatic init

    See Also
    --------
    pymodaq.daq_utils.daq_utils.ThreadCommand
    """

    command_sig = Signal(ThreadCommand)

    def __init__(self, parent, title="DAQ_Viewer"):
        super().__init__(parent)
        self.title = title

        self._detector_widget = None
        self._settings_widget = None
        self._info_detector = None
        self._daq_types_combo = None
        self._detectors_combo = None
        self._ini_det_pb = None
        self._ini_state_led = None
        self._statusbar = None

        self.setup_ui()

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
        self._detectors_combo.clear()
        self._detectors_combo.addItems(detectors)

    @property
    def daq_type(self):
        return self._daq_types_combo.currentText()

    @daq_type.setter
    def daq_type(self, dtype: str):
        self._daq_types_combo.setCurrentText(dtype)
    @property
    def daq_types(self):
        return [self._daq_types_combo.itemText(ind) for ind in range(self._daq_types_combo.count())]

    @daq_types.setter
    def daq_types(self, dtypes: List[str]):
        self._daq_types_combo.clear()
        self._daq_types_combo.addItems(dtypes)

    def setup_docks(self):
        settings_dock = Dock(self.title + "_Settings", size=(10, 10))
        self.viewer_dock = Dock(self.title + "_Viewer", size=(10, 10))

        self.dockarea.addDock(settings_dock)
        self.dockarea.addDock(self.viewer_dock, 'right', settings_dock)

        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setSizeConstraint(QHBoxLayout.SetFixedSize)
        widget.layout().setContentsMargins(2, 2, 2, 2)
        settings_dock.addWidget(widget)

        info_ui = QWidget()
        self._detector_widget = QWidget()
        self._settings_widget = QWidget()
        self._settings_widget.setLayout(QtWidgets.QVBoxLayout())

        widget.layout().addWidget(info_ui)
        widget.layout().addWidget(self.toolbar)
        widget.layout().addWidget(self._detector_widget)
        widget.layout().addWidget(self._settings_widget)

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

        self._detector_widget.layout().addWidget(LabelWithFont('DAQ type:'), 0, 0)
        self._detector_widget.layout().addWidget(self._daq_types_combo, 0, 1)
        self._detector_widget.layout().addWidget(LabelWithFont('Detector:'), 1, 0)
        self._detector_widget.layout().addWidget(self._detectors_combo, 1, 1)
        self._detector_widget.layout().addWidget(self._ini_det_pb, 0, 2)
        self._detector_widget.layout().addWidget(self._ini_state_led, 1, 2)

        self._statusbar = QtWidgets.QStatusBar()
        settings_dock.addWidget(self._statusbar)

    def add_setting_tree(self, tree):
        self._settings_widget.layout().addWidget(tree)

    def add_viewer(self):
        pass

    def setup_actions(self):
        self.add_action('grab', 'Grab', 'run2', "Grab data from the detector", checkable=True)
        self.add_action('snap', 'Snap', 'snap', "Take a snapshot from the detector")
        self.add_action('stop', 'Stop', 'stop', "Stop grabing")
        self.add_action('save_current', 'Save Current Data', 'SaveAs', "Save Current Data")
        self.add_action('save_new', 'Save New Data', 'Snap&Save', "Save New Data")
        self.add_action('open', 'Load Data', 'Open', "Load Saved Data")

        self.add_action('show_settings', 'Show Settings', 'Settings', "Show Settings", checkable=True)

        self.add_action('navigator', 'Select Data', 'Select_24', "Display ROI in a 2D viewer")
        self.add_action('quit', 'Quit the module', 'close2')
        self.add_action('log', 'Show Log file', 'information2')

    def connect_things(self):
        self.connect_action('show_settings', lambda show: self._detector_widget.setVisible(show))
        self.connect_action('quit', lambda: self.command_sig.emit(ThreadCommand('quit')))

        self.connect_action('log', lambda: self.command_sig.emit(ThreadCommand('show_log')))
        self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand('stop')))

        self.connect_action('grab', self._grab)
        self.connect_action('snap', lambda: self.command_sig.emit(ThreadCommand('snap')))

        self.connect_action('save_current', lambda: self.command_sig.emit(ThreadCommand('save_current')))
        self.connect_action('save_new', lambda: self.command_sig.emit(ThreadCommand('save_new')))
        self.connect_action('open', lambda: self.command_sig.emit(ThreadCommand('open')))

        self._ini_det_pb.clicked.connect(self._send_init)

        self._detectors_combo.currentTextChanged.connect(
            lambda mod: self.command_sig.emit(ThreadCommand('detector_changed', [mod])))
        self._daq_types_combo.currentTextChanged.connect(
            lambda mod: self.command_sig.emit(ThreadCommand('daq_type_changed', [mod])))

    def _grab(self):
        """Slot from the *grab* action"""
        self.command_sig.emit(ThreadCommand('grab', attributes=[self.is_action_checked('grab')]))

    def do_init(self, do_init=True):
        """Programmatically press the Init button
        API entry
        Parameters
        ----------
        do_init: bool
            will fire the Init button depending on the argument value and the button check state
        """
        if (do_init and not self._ini_det_pb.isChecked()) or ((not do_init) and self._ini_det_pb.isChecked()):
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

    def _send_init(self):
        self._enable_detchoices(not self._ini_det_pb.isChecked())
        self._ini_det_pb.isChecked()
        self.command_sig.emit(ThreadCommand('init', [self._ini_det_pb.isChecked(),
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
            self._info_detector.setText(f'{self.daq_type} : {self.detector}')
        else:
            self._info_detector.setText('')
        self._ini_state_led.set_as(status)

    def _enable_grab_buttons(self, status):
        self.get_action('grab').setEnabled(status)
        self.get_action('snap').setEnabled(status)
        self.get_action('stop').setEnabled(status)
        self.get_action('save_current').setEnabled(status)
        self.get_action('save_new').setEnabled(status)


def main(init_qt=True):
    from pymodaq.daq_utils.gui_utils.dock import DockArea
    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

    daq_types = ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND']
    detectors = [f'Detector Detector {ind}' for ind in range(5)]

    dockarea = DockArea()
    prog = DAQ_Viewer_UI(dockarea)
    dockarea.show()

    def print_command_sig(cmd_sig):
        print(cmd_sig)
        if cmd_sig.command == 'init':
            prog._enable_grab_buttons(cmd_sig.attributes[0])
            prog.detector_init = cmd_sig.attributes[0]

    prog.command_sig.connect(print_command_sig)
    prog.detectors = detectors
    prog.daq_types = daq_types

    if init_qt:
        sys.exit(app.exec_())
    return prog, dockarea


if __name__ == '__main__':
    main()
