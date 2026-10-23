import os
from collections import OrderedDict
import numpy as np

from qtpy import QtWidgets, QtCore
import pytest
from pytest import fixture, approx
import qt_themes
from pymodaq.control_modules import daq_move as daqmv
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.move_utility_classes import HW_SETTINGS_KEY as ACTUATOR_SETTINGS_KEY
from pymodaq.control_modules.utils import ControlModule
from pymodaq.control_modules.thread_commands import ControlToHardwareMove

from pymodaq_data import Q_
from pymodaq_utils.config import GlobalConfig

from pymodaq.utils.data import DataActuator

config = GlobalConfig()
config_viewer = config['pymodaq', 'viewer']


@fixture
def init_qt(qtbot):
    return qtbot


@fixture
def ini_daq_move_without_ui(init_qt):
    qtbot = init_qt
    prog = DAQ_Move()
    return prog, qtbot


@fixture
def ini_daq_move_ui(init_qt):
    qtbot = init_qt
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])

    prog = DAQ_Move(widget)
    widget.show()
    yield prog, qtbot, widget
    prog.quit_fun()
    widget.close()


class TestMantatoryAttributes:
    def test_methods(self, ini_daq_move_without_ui):
        actuator, qtbot = ini_daq_move_without_ui
        assert 'units' in actuator.__dir__()
        assert hasattr(actuator, 'title')


class TestMethods:
    def test_overriden(self):
        assert ControlModule.stop_grab != DAQ_Move.stop_grab
        assert ControlModule.grab != DAQ_Move.grab
        assert ControlModule.quit_fun != DAQ_Move.quit_fun
        assert ControlModule.init_hardware != DAQ_Move.init_hardware


class TestDAQMove:
    def test_buttons_send_one_command(self, ini_daq_move_ui):
        """Changing the actuator rebuilds the UI: buttons must not end up connected twice"""
        daq_move, qtbot, widget = ini_daq_move_ui
        daq_move.actuator = 'Mock'
        with qtbot.waitSignal(daq_move.init_signal, timeout=10000):
            daq_move.init_hardware_ui(True)

        commands = []
        daq_move.command_hardware.connect(lambda cmd: commands.append(cmd.command))
        ui = daq_move.ui
        ui.abs_value_sb_bis.setValue(5.)
        for button, command in ((ui.find_home_pb, ControlToHardwareMove.MOVE_HOME),
                                (ui.move_abs_pb, ControlToHardwareMove.MOVE_ABS),
                                (ui.move_rel_plus_pb, ControlToHardwareMove.MOVE_REL),
                                (ui.move_rel_minus_pb, ControlToHardwareMove.MOVE_REL),
                                (ui.stop_pb, ControlToHardwareMove.STOP_MOTION)):
            commands.clear()
            button.click()
            qtbot.wait(200)
            assert commands.count(command) == 1
        daq_move.quit_fun()

    def test_plugin_sets_default_values(self, ini_daq_move_ui):
        """The plugin can change the red, green and relative values of the UI with set_default_values"""
        daq_move, qtbot, widget = ini_daq_move_ui
        daq_move.actuator = 'Mock'
        with qtbot.waitSignal(daq_move.init_signal, timeout=10000):
            daq_move.init_hardware_ui(True)

        plugin = daq_move.controller_and_thread.thread._hardwares[daq_move.title].plugin
        red_value, green_value, relative_value = -3., 7., 0.25
        plugin.set_default_values(red=red_value, green=green_value, relative=relative_value)
        qtbot.wait(200)

        assert daq_move.settings['main_settings', 'default_value_red'] == red_value
        assert daq_move.settings['main_settings', 'default_value_green'] == green_value
        assert daq_move.settings['main_settings', 'default_value_relative'] == relative_value
        # the UI shows the values in its own unit
        assert daq_move.ui.abs_value_sb_red.value() == approx(Q_(red_value, daq_move.units).m_as(daq_move.ui._unit))
        assert daq_move.ui.abs_value_sb_green.value() == approx(Q_(green_value, daq_move.units).m_as(daq_move.ui._unit))
        daq_move.quit_fun()

    def test_data_emit(self, ini_daq_move_ui):
        daq_move, qtbot, widget = ini_daq_move_ui
        daq_move.actuator = 'Mock'

        with qtbot.waitSignal(daq_move.init_signal, timeout=10000) as blocker:
            daq_move.init_hardware_ui(True)
        assert blocker.args[0] is True

        POSITION = 34.5
        TIMEOUT = int(2 * daq_move.settings[ACTUATOR_SETTINGS_KEY, 'tau'])
        with qtbot.waitSignal(daq_move.move_done_signal, timeout=TIMEOUT) as blocker:
            with qtbot.waitSignal(daq_move.current_value_signal, timeout=1000) as val_blocker:
                daq_move.move_abs(POSITION)
        assert isinstance(val_blocker.args[0], DataActuator)
        assert val_blocker.args[0].name == daq_move.title

        data = blocker.args[0]
        assert isinstance(data, DataActuator)

        assert data.value() == pytest.approx(POSITION,
                                             abs=daq_move.settings[ACTUATOR_SETTINGS_KEY, 'epsilon'])
        assert data.name == daq_move.title

        daq_move.quit_fun()
        leco = getattr(daq_move, '_leco_client', None)
        if leco is not None:
            thread = getattr(leco, 'thread', None)
            if thread is not None:
                thread.join(timeout=5.0)
        QtWidgets.QApplication.processEvents()

    def test_axis_management(self, ini_daq_move_ui):
        daq_move, qtbot, widget = ini_daq_move_ui
        daq_move.actuator = 'Mock'
        pass
