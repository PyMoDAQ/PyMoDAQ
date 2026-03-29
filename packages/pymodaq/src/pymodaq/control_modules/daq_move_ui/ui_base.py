from abc import abstractmethod

from qtpy.QtWidgets import QComboBox
from pint import DimensionalityError
from qtpy import QtWidgets
from typing import Union, List

from pymodaq_utils.config import GlobalConfig as Config
from pymodaq.control_modules.thread_commands import UiToMainMove
from pymodaq.control_modules.ui_utils import ControlModuleUI
from pymodaq.utils.data import DataActuator
from pymodaq_data import Q_
from pymodaq_data import DataToExport
from pymodaq_gui.plotting.data_viewers import ViewerDispatcher
from pymodaq_gui.utils import DockArea, QSpinBoxWithShortcut, PushButtonIcon, QLED, QSpinBox_ro
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_utils.utils import ThreadCommand

config = Config()


class DAQ_Move_UI_Base(ControlModuleUI):
    """DAQ_Move user interface.

    This class manages the UI and emit dedicated signals depending on actions from the user

    Attributes
    ----------
    command_sig: Signal[Threadcommand]
        This signal is emitted whenever some actions done by the user has to be
        applied on the main module. Possible commands are:
            * init
            * get_value
            * loop_get_value
            * find_home
            * stop
            * move_abs
            * move_rel
            * actuator_changed
            * rel_value
            * show_plugin_config

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

    is_compact = False

    def __init__(self, parent: Union[DockArea, QtWidgets.QWidget], title="DAQ_Move"):
        super().__init__(parent)
        self.title = title
        self._unit = ''
        self.move_toolbar = self.add_toolbar('move', 'Move')
        self.set_toolbar(self.move_toolbar)  # Set as default so ui.toolbar returns this toolbar

        self.actuators_combo: QComboBox = None
        self.abs_value_sb: QSpinBoxWithShortcut = None
        self.abs_value_sb_2: QSpinBoxWithShortcut = None
        self.abs_value_sb_bis: QSpinBoxWithShortcut = None
        self.move_done_led: QLED = None
        self.current_value_sb: QSpinBox_ro = None
        self.find_home_pb: PushButtonIcon = None
        self.move_rel_plus_pb: PushButtonIcon = None
        self.move_abs_pb: PushButtonIcon = None
        self.rel_value_sb: QSpinBoxWithShortcut = None
        self.move_rel_minus_pb: PushButtonIcon = None
        self.stop_pb: PushButtonIcon = None
        self.get_value_pb: PushButtonIcon = None
        self.statusbar: QtWidgets.QStatusBar = None

        self.control_widget: QtWidgets.QWidget = None
        self.graph_widget: QtWidgets.QWidget = None
        self.viewer: ViewerDispatcher = None

        self._settings_widget: QtWidgets.QWidget = None


        self.setup_ui()

        self.enable_move_buttons(False)

    def show_data(self, data: DataToExport):
        self.viewer.show_data(data)

    def display_value(self, value: DataActuator):
        try:
            self.current_value_sb.setValue(value.value(self._unit))
        except DimensionalityError as e:
            value.force_units(self._unit)
            self.current_value_sb.setValue(value.value())

    @property
    def actuator_init(self):
        return self._ini_state

    @actuator_init.setter
    def actuator_init(self, status):
        self._ini_state = status
        self.enable_move_buttons(status)
        self.update_init_icon(status, 'ini_actuator')

    @property
    def actuator(self):
        return self.actuators_combo.currentText()

    @actuator.setter
    def actuator(self, act_name: str):
        self.actuators_combo.setCurrentText(act_name)

    @property
    def actuators(self):
        return [self.actuators_combo.itemText(ind) for ind in range(self.actuators_combo.count())]

    @actuators.setter
    def actuators(self, actuators: List[str]):
        self.actuators_combo.clear()
        self.actuators_combo.addItems(actuators)

    @property
    def move_done(self):
        """bool: the status of the move_done LED."""
        return self.move_done_led.get_state()

    @move_done.setter
    def move_done(self, status):
        self.move_done_led.set_as(status)

    def enable_move_buttons(self, status):
        self.abs_value_sb.setEnabled(status)
        self.abs_value_sb_2.setEnabled(status)
        for action_name in ('move_abs', 'move_abs_2', 'move_rel'):
            if action_name in self.actions_names:
                self.get_action(action_name).setEnabled(status)

        self.control_widget.setEnabled(status)

    def set_abs_spinbox_properties(self, **properties):
        """ Change the Spinbox properties

        Parameters
        --------
        properties: dict or named parameters
            possible keys are :

            * decimals: to set the number of displayed decimals
            * 'minimum': to set the minimum value
            * 'maximum': to set the maximum value
            * 'step': to set the step value

        """
        if 'decimals' in properties:
            self.abs_value_sb.setDecimals(properties['decimals'])
            self.abs_value_sb_2.setDecimals(properties['decimals'])
            self.abs_value_sb_bis.setDecimals(properties['decimals'])
        if 'minimum' in properties:
            self.abs_value_sb.setMinimum(properties['minimum'])
            self.abs_value_sb_2.setMinimum(properties['minimum'])
            self.abs_value_sb_bis.setMinimum(properties['minimum'])
        if 'maximum' in properties:
            self.abs_value_sb.setMaximum(properties['maximum'])
            self.abs_value_sb_2.setMaximum(properties['maximum'])
            self.abs_value_sb_bis.setMaximum(properties['maximum'])
        if 'step' in properties:
            self.abs_value_sb.setSingleStep(properties['step'])
            self.abs_value_sb_2.setSingleStep(properties['step'])
            self.abs_value_sb_bis.setSingleStep(properties['step'])

    def set_abs_value_red(self, value: Q_):
        self.abs_value_sb_2.setValue(value.m_as(self._unit))

    def set_abs_value_green(self, value: Q_):
        self.abs_value_sb.setValue(value.m_as(self._unit))

    def set_abs_value(self, value: Q_):
        self.abs_value_sb_bis.setValue(value.m_as(self._unit))

    def set_rel_value(self, value: Q_):
        self.rel_value_sb.setValue(value.m_as(self._unit))

    def set_unit_as_suffix(self, unit: str):
        """Will append the actuator units in the value display"""
        self._unit = unit
        self.current_value_sb.setOpts(suffix=unit)
        self.abs_value_sb_bis.setOpts(suffix=unit)
        self.abs_value_sb.setOpts(suffix=unit)
        self.abs_value_sb_2.setOpts(suffix=unit)
        self.rel_value_sb.setOpts(suffix=unit)

    def set_unit_prefix(self, show=True):
        """ Change the display status of the spinbox SI prefix"""
        self.current_value_sb.setOpts(siPrefix=show)
        self.abs_value_sb_bis.setOpts(siPrefix=show)
        self.abs_value_sb.setOpts(siPrefix=show)
        self.abs_value_sb_2.setOpts(siPrefix=show)
        self.rel_value_sb.setOpts(siPrefix=show)

    def setup_docks(self):
        self.parent.setLayout(QtWidgets.QHBoxLayout())
        self.parent.layout().addWidget(self.move_toolbar)
        self.control_widget = QtWidgets.QWidget()

        self.actuators_combo = QComboBox()
        self.abs_value_sb = QSpinBoxWithShortcut(step=0.1, dec=True, siPrefix=config('pymodaq', 'actuator', 'siprefix'))
        self.abs_value_sb.setStyleSheet("background-color : lightgreen; color: black")

        self.abs_value_sb_2 = QSpinBoxWithShortcut(step=0.1, dec=True, siPrefix=config('pymodaq', 'actuator', 'siprefix'))
        self.abs_value_sb_2.setStyleSheet("background-color : lightcoral; color: black")

        self.abs_value_sb_bis = QSpinBoxWithShortcut(step=0.1, dec=True, siPrefix=config('pymodaq', 'actuator', 'siprefix'))
        self.move_done_led = QLED(readonly=True)
        self.current_value_sb = QSpinBox_ro(font_size=20, min_height=27,
                                            siPrefix=config('pymodaq', 'actuator', 'siprefix'),
                                            )
        self.find_home_pb = PushButtonIcon('home', 'Find Home', icon_color=self.get_theme().magenta)
        self.move_rel_plus_pb = PushButtonIcon('step_out', 'Set Rel. (+)', icon_color=self.get_theme().yellow)
        self.move_abs_pb = PushButtonIcon('step', 'Set Abs.',
                                          tip='Set the value of the actuator to the set absolute value',
                                          icon_color=self.get_theme().green)
        self.rel_value_sb = QSpinBoxWithShortcut(step=0.1, dec=True, siPrefix=config('pymodaq', 'actuator', 'siprefix'),
                                                 key_sequences=("Ctrl+E","Ctrl+Shift+E"),)
        self.move_rel_minus_pb = PushButtonIcon('step_into', 'Set Rel. (-)', icon_color=self.get_theme().blue)
        self.stop_pb = PushButtonIcon('stop_circle', 'Stop', icon_color=self.get_theme().red)
        self.get_value_pb = PushButtonIcon('looks_one', 'Update Value', icon_color=self.get_theme().cyan)
        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setMaximumHeight(30)

        self.graph_widget = QtWidgets.QWidget()
        self.graph_widget.setLayout(QtWidgets.QHBoxLayout())
        self.graph_widget.layout().setContentsMargins(0, 0, 0, 0)
        dockarea = DockArea()
        self.graph_widget.layout().addWidget(dockarea)
        self.viewer = ViewerDispatcher(dockarea)
        self.actuator_init = False

    def populate_control_ui(self,  widget: QtWidgets.QWidget):
        widget.setLayout(QtWidgets.QVBoxLayout())
        container_widget = QtWidgets.QWidget()
        widget.layout().addWidget(container_widget)
        widget.layout().addStretch()

        container_widget.setLayout(QtWidgets.QGridLayout())
        container_widget.layout().addWidget(LabelWithFont('Abs. Value'), 0, 0)

        container_widget.layout().addWidget(self.find_home_pb, 0, 1)

        container_widget.layout().addWidget(self.abs_value_sb_bis, 1, 0)
        container_widget.layout().addWidget(self.move_abs_pb, 1, 1)
        container_widget.layout().addWidget(LabelWithFont('Rel. Increment'), 2, 0)
        container_widget.layout().addWidget(self.move_rel_plus_pb, 2, 1)

        container_widget.layout().addWidget(self.rel_value_sb, 3, 0)

        container_widget.layout().addWidget(self.move_rel_minus_pb, 3, 1)
        container_widget.layout().addWidget(self.stop_pb, 4, 0)

        container_widget.layout().addWidget(self.get_value_pb, 4, 1)
        container_widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.setVisible(False)

    def close(self):
        self.parent.close()
        self.graph_widget.close()
        self.control_widget.close()
        self._settings_widget.close()

    def do_init(self, do_init=True):
        """Programmatically press the Init button
        API entry
        Parameters
        ----------
        do_init: bool
            will fire the Init button depending on the argument value and the button check state
        """
        if do_init is not self.is_action_checked('ini_actuator'):
            self.get_action('ini_actuator').trigger()

    def send_init(self, checked: bool):
        self.actuators_combo.setEnabled(not checked)
        self.command_sig.emit(ThreadCommand(UiToMainMove.INIT, [checked,
                                                                self.actuators_combo.currentText()]))

    def emit_move_abs(self, spinbox):
        spinbox.editingFinished.emit()
        self.command_sig.emit(ThreadCommand(UiToMainMove.MOVE_ABS, DataActuator(data=spinbox.value(),
                                                                                units=self._unit)))

    def emit_move_rel(self, sign):
        self.command_sig.emit(ThreadCommand(
            UiToMainMove.MOVE_REL,
            DataActuator(data=self.rel_value_sb.value() * (1 if sign == '+' else -1),
                         units=self._unit)))

    def set_settings_tree(self, tree):
        self._settings_widget = tree


    def setup_actions_in_toolbar(self, toolbar: QtWidgets.QToolBar):
        self._setup_name_widget(toolbar=toolbar)
        self.add_widget('actuators_combo', self.actuators_combo, toolbar=toolbar)
        self._setup_init_action(toolbar=toolbar, action_name='ini_actuator',
                                display_name='Ini. Actuator', tip='Connect to selected actuator')
        self._setup_settings_action(toolbar=toolbar)
        toolbar.addSeparator()
        self.add_widget('current', self.current_value_sb, toolbar=toolbar)
        self.add_widget('move_done', self.move_done_led, toolbar=toolbar)

        self._setup_move_actions(toolbar)

        self.add_action('stop', 'Stop', 'stop_circle', "Stop Motion",
                        toolbar=toolbar, icon_color=self.get_theme().red)
        toolbar.addSeparator()
        self.add_action('show_controls', 'Show Controls',
                        'discover_tune', "Show more controls", checkable=True,
                        toolbar=toolbar)
        self.add_action('show_graph', 'Show Graph', 'bid_landscape', 'Show/Hide the Graph Widget',
                        checkable=True, checked=True, icon_checked='bid_landscape_disabled',
                        icon_color=self.get_theme().green, icon_checked_color=self.get_theme().red,
                        toolbar=toolbar)
        self.add_action('refresh_value', 'Refresh', 'repeat',
                        "Refresh Value Continuously", checkable=True,
                        toolbar=toolbar, icon_checked='repeat_on',
                        icon_checked_color=self.get_theme().green)
        self.add_widget('status', self.statusbar, toolbar=toolbar)

    def _setup_move_actions(self, toolbar: QtWidgets.QToolBar):
        """ to be reimplemented in dedicated UI class

        either: self._setup_absolute_actions(), self._setup_relative_actions(), ...
        """
        pass

    def _setup_absolute_spinbox_actions(self, toolbar: QtWidgets.QToolBar):
        self.add_widget('abs_green', self.abs_value_sb, toolbar=toolbar)
        self.add_widget('abs_red', self.abs_value_sb_2, toolbar=toolbar)

    def _setup_absolute_actions(self, toolbar: QtWidgets.QToolBar):
        self.add_action('move_abs', 'Move Abs', 'step',
                        "Move to the set absolute value",
                        icon_color=self.get_theme().green,
                        toolbar=toolbar)
        self.add_action('move_abs_2', 'Move Abs', 'step',
                        "Move to the other set absolute value",
                        icon_color=self.get_theme().red,
                        toolbar=toolbar)

    def _setup_relative_actions(self, toolbar: QtWidgets.QToolBar):
        self.add_widget('rel_move', self.rel_value_sb, toolbar=toolbar)
        self.add_action('move_rel_plus', 'Set Rel. (+)', 'step_out',
                        toolbar=toolbar)
        self.add_action('move_rel_minus', 'Set Rel. (-)', 'step_into',
                        toolbar=toolbar)

    def connect_things(self):
        if 'show_controls' in self.actions_names:
            self.connect_action('show_controls', self.show_controls)
        if 'show_settings' in self.actions_names:
            self.connect_action('show_settings', self._show_settings)
        if 'show_graph' in self.actions_names:
            self.connect_action('show_graph', lambda checked: self.show_graph(not checked))
        if 'move_abs' in self.actions_names:
            self.connect_action('move_abs', lambda: self.emit_move_abs(self.abs_value_sb))
        if 'move_abs_2' in self.actions_names:
            self.connect_action('move_abs_2', lambda: self.emit_move_abs(self.abs_value_sb_2))
        if 'stop' in self.actions_names:
            self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.STOP, )))
        if 'show_config' in self.actions_names:
            self.connect_action('show_config', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.SHOW_CONFIG, )))
        if 'ini_actuator' in self.actions_names:
            self.connect_action('ini_actuator', self.send_init)

        self.move_abs_pb.clicked.connect(lambda: self.emit_move_abs(self.abs_value_sb_bis))
        self.abs_value_sb.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_abs(self.abs_value_sb))
        self.abs_value_sb_2.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_abs(self.abs_value_sb_2))
        self.abs_value_sb_bis.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_abs(self.abs_value_sb_bis))
        self.rel_value_sb.valueChanged.connect(lambda: self.command_sig.emit(
            ThreadCommand(UiToMainMove.REL_VALUE, self.rel_value_sb.value())))
        self.move_rel_plus_pb.clicked.connect(lambda: self.emit_move_rel('+'))
        self.move_rel_minus_pb.clicked.connect(lambda: self.emit_move_rel('-'))
        self.rel_value_sb.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_rel('+'))
        self.rel_value_sb.shortcut["Ctrl+Shift+E"].activated.connect(lambda: self.emit_move_rel('-'))

        self.find_home_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.FIND_HOME, )))
        self.stop_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.STOP, )))
        self.get_value_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.GET_VALUE, )))

        self.actuators_combo.currentTextChanged.connect(
            lambda act: self.command_sig.emit(ThreadCommand(UiToMainMove.ACTUATOR_CHANGED, act)))
        if 'refresh_value' in self.actions_names:
            self.connect_action('refresh_value',
                                lambda do_refresh: self.command_sig.emit(ThreadCommand(UiToMainMove.LOOP_GET_VALUE,
                                                                                   do_refresh)))

    def show_controls(self, show: bool = True):
        self.control_widget.setVisible(show)
        self.control_widget.closeEvent = lambda event: self.set_action_checked('show_controls', False)

    def show_graph(self, show: bool = True):
        self.graph_widget.setVisible(show)
        self.graph_widget.closeEvent = lambda event: self.set_action_checked('show_graph', False)