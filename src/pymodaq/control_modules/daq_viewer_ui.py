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

    def __init__(self, dockarea, title="DAQ_Viewer"):
        super().__init__(dockarea)
        self.title = title
        self.setup_ui()

        self.enable_grab_buttons(False)

    @property
    def detector(self):
        return self.detectors_combo.currentText()

    @detector.setter
    def detector(self, det_name: str):
        self.detectors_combo.setCurrentText(det_name)
    @property
    def detectors(self):
        return [self.detectors_combo.itemText(ind) for ind in range(self.detectors_combo.count())]

    @detectors.setter
    def detectors(self, detectors: List[str]):
        self.detectors_combo.clear()
        self.detectors_combo.addItems(detectors)

    @property
    def daq_type(self):
        return self.daq_types_combo.currentText()

    @daq_type.setter
    def daq_type(self, dtype: str):
        self.daq_types_combo.setCurrentText(dtype)
    @property
    def daq_types(self):
        return [self.daq_types_combo.itemText(ind) for ind in range(self.daq_types_combo.count())]

    @daq_types.setter
    def daq_types(self, dtypes: List[str]):
        self.daq_types_combo.clear()
        self.daq_types_combo.addItems(dtypes)

    def setup_docks(self):
        self.dockarea.setLayout(QVBoxLayout())
        self.dockarea.layout().setSizeConstraint(QHBoxLayout.SetFixedSize)
        self.dockarea.layout().setContentsMargins(2, 2, 2, 2)

        self.widget = QWidget()
        self.widget.setLayout(QVBoxLayout())
        self.dockarea.layout().addWidget(self.widget)

        self.detector_ui = QWidget()
        self.settings_ui = QWidget()

        self.widget.layout().addWidget(self.toolbar)

        widg_init = QtWidgets.QWidget()
        widg_init.setLayout(QtWidgets.QHBoxLayout())
        widg_init.layout().addWidget(LabelWithFont(self.title, font_name="Tahoma", font_size=14, isbold=True,
                                                   isitalic=True))
        self.ini_det_pb = PushButtonIcon('ini', 'Init. Detector', True, 'Initialize selected detector')
        self.ini_state_led = QLED(readonly=True)

        widg_init.layout().addWidget(self.ini_det_pb)
        widg_init.layout().addWidget(self.ini_state_led)

        self.widget.layout().addWidget(widg_init)
        self.widget.layout().addWidget(self.detector_ui)
        self.widget.layout().addWidget(self.settings_ui)

        self.detector_ui.setLayout(QtWidgets.QHBoxLayout())

        self.daq_types_combo = QComboBox()
        self.daq_types_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.detectors_combo = QComboBox()
        self.detectors_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.detector_ui.layout().addWidget(LabelWithFont('DAQ type:'))
        self.detector_ui.layout().addWidget(self.daq_types_combo)
        self.detector_ui.layout().addWidget(LabelWithFont('Detector:'))
        self.detector_ui.layout().addWidget(self.detectors_combo)

        self.statusbar = QtWidgets.QStatusBar()
        self.dockarea.layout().addWidget(self.statusbar)

    def setup_actions(self):
        self.add_action('grab', 'Grab', 'run2', "Grab data from the detector", checkable=True)
        self.add_action('snap', 'Snap', 'snap', "Take a snapshot from the detector")
        self.add_action('stop', 'Stop', 'stop', "Stop grabing")
        self.add_action('save_current', 'Save Current Data', 'SaveAs', "Save Current Data")
        self.add_action('save_new', 'Save New Data', 'Snap&Save', "Save New Data")
        self.add_action('open', 'Load Data', 'Open', "Load Saved Data")

        self.add_action('show_settings', 'Show Settings', 'Settings', "Show Settings", checkable=True)

        self.add_action('navigator', 'Select Data', 'Select_24', "Stop Motion")
        self.add_action('quit', 'Quit the module', 'close2')
        self.add_action('log', 'Show Log file', 'information2')

    def connect_things(self):
        self.connect_action('show_settings', lambda show: self.detector_ui.setVisible(show))
        self.connect_action('show_settings', lambda show: self.settings_ui.setVisible(show))
        self.connect_action('quit', lambda: self.command_sig.emit(ThreadCommand('quit')))

        self.connect_action('log', lambda: self.command_sig.emit(ThreadCommand('show_log')))
        self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand('stop')))

        self.ini_det_pb.clicked.connect(self.send_init)

        self.detectors_combo.currentTextChanged.connect(
            lambda mod: self.command_sig.emit(ThreadCommand('detector_changed', mod)))
        self.daq_types_combo.currentTextChanged.connect(
            lambda mod: self.command_sig.emit(ThreadCommand('daq_type_changed', mod)))

    def send_init(self):
        self.detectors_combo.setEnabled(not self.ini_det_pb.isChecked())
        self.daq_types_combo.setEnabled(not self.ini_det_pb.isChecked())

        self.command_sig.emit(ThreadCommand('init', [self.ini_det_pb.isChecked(),
                                                     self.daq_types_combo.currentText(),
                                                     self.detectors_combo.currentText()]))

    def enable_grab_buttons(self, status):
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


    widget = QtWidgets.QWidget()
    prog = DAQ_Viewer_UI(widget)
    widget.show()

    def print_command_sig(cmd_sig):
        print(cmd_sig)
        if cmd_sig.command == 'init':
            prog.enable_grab_buttons(True)

    prog.command_sig.connect(print_command_sig)
    prog.detectors = detectors
    prog.daq_types = daq_types

    if init_qt:
        sys.exit(app.exec_())
    return prog, widget


if __name__ == '__main__':
    main()
