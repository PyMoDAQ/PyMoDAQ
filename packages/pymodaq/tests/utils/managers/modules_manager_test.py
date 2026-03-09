# -*- coding: utf-8 -*-
"""Tests for pymodaq.utils.managers.modules_manager"""
import numpy as np
import pytest
from unittest.mock import patch

from qtpy.QtCore import QObject, Signal

from pymodaq_data.data import DataToExport, DataRaw, DataSource

from pymodaq.utils.data import DataActuator
from pymodaq.utils.managers.modules import ModulesManager, ModuleType


# ---------------------------------------------------------------------------
# Minimal mock control modules (real QObject so signals work)
# ---------------------------------------------------------------------------

class MockDetector(QObject):
    grab_done_signal = Signal(DataToExport)
    command_hardware = Signal(object)

    def __init__(self, title: str, naverage: int = 1):
        super().__init__()
        self.title = title
        self.Naverage = naverage


class MockActuator(QObject):
    move_done_signal = Signal(DataActuator)
    current_value_signal = Signal(DataActuator)
    command_hardware = Signal(object)

    def __init__(self, title: str, current_value: float = 0.0):
        super().__init__()
        self.title = title
        self._current_value = DataActuator(title, data=current_value)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def detectors():
    return [MockDetector('Det1'), MockDetector('Det2'), MockDetector('Det3')]


@pytest.fixture
def actuators():
    return [MockActuator('X_axis', 0.0), MockActuator('Y_axis', 1.0)]


@pytest.fixture
def manager(detectors, actuators):
    mm = ModulesManager(
        detectors=detectors,
        actuators=actuators,
        selected_detectors=[detectors[0]],
        selected_actuators=[actuators[0]],
    )
    yield mm


# ---------------------------------------------------------------------------
# Helpers to build controlled DataToExport for tree-building tests
# ---------------------------------------------------------------------------

def make_raw_dte(det_title: str, channel_name: str = 'CH0') -> DataToExport:
    """DTE with a single raw 1D channel from a detector."""
    raw = DataRaw(channel_name, data=[np.zeros(10)])
    raw.origin = det_title
    dte = DataToExport('test', control_module='DAQ_Viewer')
    dte.append(raw)
    return dte


def make_dte_with_roi(det_title: str, channel_name: str = 'CH0',
                      roi_name: str = 'ROI_00') -> DataToExport:
    """DTE with one raw channel plus ROI outputs nested under it."""
    raw = DataRaw(channel_name, data=[np.zeros(10)])
    raw.origin = det_title

    roi_origin = f'{det_title} - {roi_name}'

    hor = DataRaw('hor', data=[np.zeros(10)])
    hor.origin = roi_origin
    hor.labels = [f'{roi_name}/{channel_name}']

    scalar = DataRaw('int', data=[np.array([1.0])])
    scalar.origin = roi_origin
    scalar.labels = [f'{roi_name}/{channel_name}']

    dte = DataToExport('test', control_module='DAQ_Viewer')
    dte.append(raw)
    dte.append(hor)
    dte.append(scalar)
    return dte


# ===========================================================================
# Tests
# ===========================================================================

class TestInit:

    def test_empty_init(self):
        mm = ModulesManager()
        assert mm.detectors_all == []
        assert mm.actuators_all == []
        assert mm.detectors == []
        assert mm.actuators == []

    def test_init_with_modules(self, manager, detectors, actuators):
        assert len(manager.detectors_all) == 3
        assert len(manager.actuators_all) == 2

    def test_selected_subset(self, manager, detectors, actuators):
        assert manager.detectors == [detectors[0]]
        assert manager.actuators == [actuators[0]]

    def test_selected_not_in_list_raises(self, detectors):
        outsider = MockDetector('Outsider')
        with pytest.raises(AssertionError):
            ModulesManager(detectors=detectors, selected_detectors=[outsider])

    def test_parent_name_in_repr(self, detectors):
        mm = ModulesManager(detectors=detectors, parent_name='MyParent')
        assert 'MyParent' in repr(mm)


class TestNameResolution:

    def test_get_names(self, detectors):
        assert ModulesManager.get_names(detectors) == ['Det1', 'Det2', 'Det3']

    def test_get_names_single_module(self, detectors):
        assert ModulesManager.get_names(detectors[0]) == ['Det1']

    def test_get_mod_from_name_found(self, manager, detectors):
        assert manager.get_mod_from_name('Det1') is detectors[0]

    def test_get_mod_from_name_not_found_returns_none(self, manager):
        assert manager.get_mod_from_name('Ghost') is None

    def test_get_mod_from_name_actuator(self, manager, actuators):
        assert manager.get_mod_from_name('X_axis', ModuleType.Actuator) is actuators[0]

    def test_get_mod_from_name_backcompat_det_string(self, manager, detectors):
        assert manager.get_mod_from_name('Det1', 'det') is detectors[0]

    def test_get_mods_from_names(self, manager, detectors):
        result = manager.get_mods_from_names(['Det1', 'Det3'])
        assert result == [detectors[0], detectors[2]]

    def test_get_mods_from_names_skips_missing(self, manager, detectors):
        result = manager.get_mods_from_names(['Det1', 'Ghost'])
        assert result == [detectors[0]]


class TestSelection:

    def test_detectors_name_lists_all(self, manager):
        assert set(manager.detectors_name) == {'Det1', 'Det2', 'Det3'}

    def test_selected_detectors_name(self, manager):
        assert manager.selected_detectors_name == ['Det1']

    def test_set_selected_detectors_name(self, manager):
        manager.selected_detectors_name = ['Det2', 'Det3']
        assert set(manager.selected_detectors_name) == {'Det2', 'Det3'}

    def test_set_selected_detectors_name_ignores_unknown(self, manager):
        manager.selected_detectors_name = ['Ghost']
        assert manager.selected_detectors_name == ['Det1']  # unchanged

    def test_actuators_name_lists_all(self, manager):
        assert set(manager.actuators_name) == {'X_axis', 'Y_axis'}

    def test_set_selected_actuators_name(self, manager):
        manager.selected_actuators_name = ['Y_axis']
        assert manager.selected_actuators_name == ['Y_axis']

    def test_set_selected_actuators_name_ignores_unknown(self, manager):
        manager.selected_actuators_name = ['Ghost']
        assert manager.selected_actuators_name == ['X_axis']  # unchanged

    def test_ndetectors(self, manager):
        assert manager.Ndetectors == 1

    def test_nactuators(self, manager):
        assert manager.Nactuators == 1

    def test_modules_selected(self, manager, detectors, actuators):
        assert manager.modules == [detectors[0], actuators[0]]

    def test_modules_all(self, manager, detectors, actuators):
        assert manager.modules_all == detectors + actuators

    def test_detectors_all_setter_clears_selection(self, manager):
        new_det = MockDetector('New')
        manager.detectors_all = [new_det]
        assert manager.detectors_all == [new_det]
        assert manager.selected_detectors_name == []

    def test_actuators_all_setter_clears_selection(self, manager):
        new_act = MockActuator('New')
        manager.actuators_all = [new_act]
        assert manager.actuators_all == [new_act]
        assert manager.selected_actuators_name == []


class TestSignals:

    def test_detectors_changed_emitted(self, qtbot, manager):
        with qtbot.waitSignal(manager.detectors_changed, timeout=500) as blocker:
            manager.selected_detectors_name = ['Det2']
        assert blocker.args == [['Det2']]

    def test_actuators_changed_emitted(self, qtbot, manager):
        with qtbot.waitSignal(manager.actuators_changed, timeout=500) as blocker:
            manager.selected_actuators_name = ['Y_axis']
        assert blocker.args == [['Y_axis']]


class TestDetDone:

    def _init_grab(self, manager, selected_names):
        manager.selected_detectors_name = selected_names
        manager.det_done_datas = DataToExport('test', control_module='DAQ_Viewer')
        manager._received_data = 0
        manager.det_done_flag = False

    def test_flag_set_when_all_received(self, manager):
        self._init_grab(manager, ['Det1', 'Det2'])

        manager.det_done(DataToExport('a', control_module='DAQ_Viewer'))
        assert not manager.det_done_flag

        manager.det_done(DataToExport('b', control_module='DAQ_Viewer'))
        assert manager.det_done_flag

    def test_data_appended(self, manager):
        self._init_grab(manager, ['Det1'])
        dte = DataToExport('a', control_module='DAQ_Viewer')
        dte.append(DataRaw('CH0', data=[np.array([1.0])]))

        manager.det_done(dte)
        assert len(manager.det_done_datas) == 1

    def test_empty_dte_not_appended(self, manager):
        self._init_grab(manager, ['Det1'])
        manager.det_done(DataToExport('empty', control_module='DAQ_Viewer'))
        assert len(manager.det_done_datas) == 0

    def test_ignored_when_not_initialized(self, manager):
        manager.det_done_datas = None
        manager._received_data = 0
        manager.det_done(DataToExport('x', control_module='DAQ_Viewer'))  # must not raise
        assert manager._received_data == 0


class TestMoveDone:

    def _init_move(self, manager, selected_names):
        manager.selected_actuators_name = selected_names
        manager.move_done_positions = DataToExport('test', control_module='DAQ_Move')
        manager.move_done_flag = False

    def test_flag_set_when_all_received(self, manager):
        self._init_move(manager, ['X_axis', 'Y_axis'])

        manager.move_done(DataActuator('X_axis', data=1.0))
        assert not manager.move_done_flag

        manager.move_done(DataActuator('Y_axis', data=2.0))
        assert manager.move_done_flag

    def test_positions_accumulated(self, manager):
        self._init_move(manager, ['X_axis', 'Y_axis'])

        manager.move_done(DataActuator('X_axis', data=1.0))
        manager.move_done(DataActuator('Y_axis', data=2.0))
        assert len(manager.move_done_positions) == 2

    def test_duplicate_ignored(self, manager):
        self._init_move(manager, ['X_axis', 'Y_axis'])

        manager.move_done(DataActuator('X_axis', data=1.0))
        manager.move_done(DataActuator('X_axis', data=9.0))  # duplicate
        assert len(manager.move_done_positions) == 1
        assert not manager.move_done_flag


class TestGetDetDataList:

    def test_no_detectors_returns_empty_dte(self, manager):
        manager.selected_detectors_name = []
        result = manager.get_det_data_list()
        assert isinstance(result, DataToExport)
        assert len(result) == 0

    def test_raw_channel_in_tree(self, manager):
        manager.selected_detectors_name = ['Det1']
        dte = make_raw_dte('Det1', 'CH0')
        with patch.object(manager, 'grab_data', return_value=dte):
            manager.get_det_data_list()

        det_param = manager.settings.child('probe_data').children()[0]
        assert det_param.name() == 'Det1'
        ch_param = det_param.children()[0]
        assert ch_param.name() == 'CH0'
        assert ch_param.opts['full_name'] == 'Det1/CH0'

    def test_tree_cleared_on_repopulate(self, manager):
        manager.selected_detectors_name = ['Det1']
        dte = make_raw_dte('Det1', 'CH0')
        with patch.object(manager, 'grab_data', return_value=dte):
            manager.get_det_data_list()
            manager.get_det_data_list()  # second call must not duplicate

        assert len(manager.settings.child('probe_data').children()) == 1

    def test_roi_nested_under_raw_channel(self, manager):
        manager.selected_detectors_name = ['Det1']
        dte = make_dte_with_roi('Det1', 'CH0', 'ROI_00')
        with patch.object(manager, 'grab_data', return_value=dte):
            manager.get_det_data_list()

        ch_param = manager.settings.child('probe_data').children()[0].children()[0]
        roi_groups = [p for p in ch_param.children() if p.type() == 'group']
        assert len(roi_groups) == 1
        assert roi_groups[0].name() == 'ROI_00'
        roi_child_names = {p.name() for p in roi_groups[0].children()}
        assert {'hor', 'int'}.issubset(roi_child_names)

    def test_multiple_rois_nested_under_same_channel(self, manager):
        manager.selected_detectors_name = ['Det1']
        dte = make_dte_with_roi('Det1', 'CH0', 'ROI_00')
        for dwa in make_dte_with_roi('Det1', 'CH0', 'ROI_01').data:
            if dwa.origin != 'Det1':
                dte.append(dwa)

        with patch.object(manager, 'grab_data', return_value=dte):
            manager.get_det_data_list()

        ch_param = manager.settings.child('probe_data').children()[0].children()[0]
        roi_groups = [p for p in ch_param.children() if p.type() == 'group']
        assert {g.name() for g in roi_groups} == {'ROI_00', 'ROI_01'}

    def test_connect_detectors_released_on_exception(self, manager):
        """connect_detectors(False) must be called via finally even if grab_data raises."""
        manager.selected_detectors_name = ['Det1']
        with patch.object(manager, 'grab_data', side_effect=RuntimeError('oops')):
            with patch.object(manager, 'connect_detectors') as mock_connect:
                with pytest.raises(RuntimeError):
                    manager.get_det_data_list()
        mock_connect.assert_any_call(False)


class TestGetProbedDataChannels:

    def _populate(self, manager):
        manager.selected_detectors_name = ['Det1']
        dte = make_dte_with_roi('Det1', 'CH0', 'ROI_00')
        with patch.object(manager, 'grab_data', return_value=dte):
            manager.get_det_data_list()

    def test_returns_raw_channel(self, manager):
        self._populate(manager)
        assert 'Det1/CH0' in manager.get_probed_data_channels()

    def test_returns_roi_outputs(self, manager):
        self._populate(manager)
        names = manager.get_probed_data_channels()
        assert 'Det1 - ROI_00/hor' in names
        assert 'Det1 - ROI_00/int' in names

    def test_dim_filter(self, manager):
        self._populate(manager)
        # 'DataND' should match nothing in our simple 0D/1D test data
        assert manager.get_probed_data_channels(dim='DataND') == []

    def test_empty_before_probe(self, manager):
        assert manager.get_probed_data_channels() == []


class TestShowOnlyControlModules:

    def test_hides_probe_params(self, manager):
        probe = manager.settings.child('probe_data')
        test_act = manager.settings.child('test_actuator')
        with patch.object(probe, 'show') as p, patch.object(test_act, 'show') as t:
            manager.show_only_control_modules(True)
            p.assert_called_once_with(False)
            t.assert_called_once_with(False)

    def test_shows_probe_params(self, manager):
        probe = manager.settings.child('probe_data')
        test_act = manager.settings.child('test_actuator')
        with patch.object(probe, 'show') as p, patch.object(test_act, 'show') as t:
            manager.show_only_control_modules(False)
            p.assert_called_once_with(True)
            t.assert_called_once_with(True)


class TestTestActuatorTree:

    def test_children_populated_after_move(self, manager):
        """After move_done collects all positions, test_actuator children reflect them."""
        manager.selected_actuators_name = ['X_axis', 'Y_axis']
        manager.move_done_positions = DataToExport('test', control_module='DAQ_Move')
        manager.move_done_positions.append(DataActuator('X_axis', data=3.14))
        manager.move_done_positions.append(DataActuator('Y_axis', data=2.71))

        test_act = manager.settings.child('test_actuator')
        test_act.clearChildren()
        for dact in manager.move_done_positions:
            test_act.addChild(
                {'title': dact.name, 'name': dact.name.replace(' ', '_'),
                 'type': 'float', 'value': dact.value(), 'readonly': True}
            )

        children = {p.name(): p.value() for p in test_act.children()}
        assert 'X_axis' in children
        assert 'Y_axis' in children
        assert abs(children['X_axis'] - 3.14) < 1e-9
        assert abs(children['Y_axis'] - 2.71) < 1e-9

    def test_children_cleared_on_new_move(self, manager):
        """A second move replaces the previous children."""
        test_act = manager.settings.child('test_actuator')
        test_act.addChild(
            {'title': 'X_axis', 'name': 'X_axis', 'type': 'float', 'value': 0.0, 'readonly': True}
        )
        assert len(test_act.children()) == 1

        test_act.clearChildren()
        test_act.addChild(
            {'title': 'X_axis', 'name': 'X_axis', 'type': 'float', 'value': 5.0, 'readonly': True}
        )
        assert len(test_act.children()) == 1
        assert test_act.children()[0].value() == 5.0
