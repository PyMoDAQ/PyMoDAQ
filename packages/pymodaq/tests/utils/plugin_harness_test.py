"""Tests of the plugin testing harness (pymodaq.utils.plugin_testing), run against small fake plugins, the mock plugin
of PyMoDAQ and the deprecated import path of the pytest mixin"""
import importlib

import numpy as np
import pytest

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, DataActuatorType
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq.utils.data import DataActuator, DataFromPlugins
from pymodaq_data.data import DataToExport

from pymodaq.utils.plugin_testing import (make_actuator, make_detector, move_abs_and_wait, move_rel_and_wait,
                                          move_home_and_wait, grab_and_wait, assert_units, wait_for_signal,
                                          SignalTimeout)


class FakeController:
    """Stands for the python wrapper of a real instrument: instantaneous, in memory, records what it was asked"""
    def __init__(self):
        self.position = 0.
        self.is_open = True
        self.calls = []

    def move_at(self, value: float):
        self.calls.append(('move_at', value))
        self.position = value

    def acquire(self, npts: int = 10) -> np.ndarray:
        return np.linspace(0., 1., npts)

    def close(self):
        self.is_open = False


class DAQ_Move_Fake(DAQ_Move_base):
    _controller_units = 'mm'
    is_multiaxes = False
    _axis_names = ['axis']
    _epsilons = [0.01]
    data_actuator_type = DataActuatorType.DataActuator
    params = comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilons)

    def ini_attributes(self):
        self.controller: FakeController = None

    def ini_stage(self, controller=None):
        self.controller = FakeController() if self.is_master else controller
        return 'fake stage ready', True

    def get_actuator_value(self) -> DataActuator:
        pos = DataActuator(data=self.controller.position, units=self.axis_unit)
        return self.get_position_with_scaling(pos)

    def move_abs(self, value: DataActuator):
        value = self.check_bound(value)
        self.target_value = value
        self.controller.move_at(self.set_position_with_scaling(value).value())

    def move_rel(self, value: DataActuator):
        self.move_abs(self.current_value + value)

    def move_home(self):
        self.move_abs(DataActuator(data=0., units=self.axis_unit))

    def stop_motion(self):
        self.controller.calls.append(('stop',))

    def commit_settings(self, param):
        pass

    def close(self):
        if self.is_master:
            self.controller.close()


class DAQ_MultiAxes_Fake(DAQ_Move_Fake):
    is_multiaxes = True
    _axis_names = ['x', 'y']
    _epsilons = [0.01, 0.01]
    params = comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilons)


class DAQ_1DViewer_Fake(DAQ_Viewer_base):
    params = comon_parameters + [{'title': 'Npts:', 'name': 'npts', 'type': 'int', 'value': 10, 'min': 1}]

    def ini_attributes(self):
        self.controller: FakeController = None

    def ini_detector(self, controller=None):
        self.controller = FakeController() if self.is_master else controller
        return 'fake detector ready', True

    def commit_settings(self, param):
        pass

    def grab_data(self, Naverage=1, **kwargs):
        y = self.controller.acquire(self.settings['npts'])
        self.dte_signal.emit(DataToExport(
            name='fake', data=[DataFromPlugins(name='trace', data=[y], dim='Data1D', labels=['signal'], units='V')]))

    def close(self):
        if self.is_master:
            self.controller.close()


@pytest.fixture
def actuator(qtbot):
    plugin = make_actuator(DAQ_Move_Fake)
    yield plugin
    plugin.close()


@pytest.fixture
def detector(qtbot):
    plugin = make_detector(DAQ_1DViewer_Fake, npts=20)
    yield plugin
    plugin.close()


class TestActuator:
    def test_ini(self, actuator):
        assert actuator.initialized is True
        assert isinstance(actuator.init_info, str)

    def test_value_has_units(self, actuator):
        assert actuator.get_actuator_value().units == 'mm'

    def test_move_abs(self, actuator):
        pos = move_abs_and_wait(actuator, 2.5)
        assert pos.value('mm') == pytest.approx(2.5, abs=0.01)
        assert actuator.controller.calls[-1] == ('move_at', 2.5)

    def test_move_rel(self, actuator):
        move_abs_and_wait(actuator, 1.)
        pos = move_rel_and_wait(actuator, 0.5)
        assert pos.value('mm') == pytest.approx(1.5, abs=0.01)

    def test_move_home(self, actuator):
        move_abs_and_wait(actuator, 3.)
        assert move_home_and_wait(actuator).value('mm') == pytest.approx(0., abs=0.01)

    def test_target_is_converted_to_the_axis_unit(self, actuator):
        target = DataActuator(data=1., units='cm')
        pos = move_abs_and_wait(actuator, target)
        assert pos.value('mm') == pytest.approx(10., abs=0.01)
        assert target.units == 'cm'  # the caller's object is left untouched

    def test_close_releases_the_controller(self, actuator):
        controller = actuator.controller
        actuator.close()
        assert controller.is_open is False

    def test_slave_axis_uses_the_given_controller(self, qtbot):
        master = make_actuator(DAQ_MultiAxes_Fake)
        slave = make_actuator(DAQ_MultiAxes_Fake, controller=master.controller)
        assert slave.controller is master.controller
        move_abs_and_wait(slave, 1.)
        assert master.controller.calls[-1] == ('move_at', 1.)
        slave.close()
        assert master.controller.is_open  # only the master releases the shared controller
        master.close()
        assert not master.controller.is_open


class TestDetector:
    def test_grab(self, detector):
        dte = grab_and_wait(detector)
        assert len(dte) == 1
        assert dte[0].shape == (20,)
        assert_units(dte, 'V')

    def test_assert_units_detects_missing_units(self):
        dte = DataToExport('x', data=[DataFromPlugins(name='t', data=[np.zeros(3)], dim='Data1D')])
        with pytest.raises(AssertionError):
            assert_units(dte)

    def test_close_releases_the_controller(self, detector):
        controller = detector.controller
        detector.close()
        assert controller.is_open is False


def test_timeout(actuator):
    with pytest.raises(SignalTimeout):
        wait_for_signal(actuator.move_done_signal, lambda: None, timeout_ms=100)


def test_harness_with_the_mock_plugins(qtbot):
    """The same helpers drive the plugins of pymodaq_plugins_mock, whose controller is a time dependent simulation"""
    from pymodaq_plugins_mock.daq_move_plugins.daq_move_Mock import DAQ_Move_Mock
    from pymodaq_plugins_mock.daq_viewer_plugins.plugins_1D.daq_1Dviewer_Mock import DAQ_1DViewer_Mock

    mock_move = make_actuator(DAQ_Move_Mock)
    assert mock_move.initialized
    pos = move_abs_and_wait(mock_move, 2.)
    assert pos.value(mock_move.axis_unit) == pytest.approx(2., abs=mock_move.epsilon + 1e-3)
    mock_move.close()

    mock_viewer = make_detector(DAQ_1DViewer_Mock)
    assert mock_viewer.initialized
    assert len(grab_and_wait(mock_viewer)) >= 1
    mock_viewer.close()


def test_deprecated_import_path_still_works():
    module = importlib.import_module('pymodaq_utils.plugin_testing')
    with pytest.warns(DeprecationWarning, match='pymodaq.utils.plugin_testing'):
        mixin = module.PluginPackageChecks
    from pymodaq.utils.plugin_testing import PluginPackageChecks
    assert mixin is PluginPackageChecks
    with pytest.raises(AttributeError):
        module.does_not_exist
