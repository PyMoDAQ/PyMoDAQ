"""The use cases of the ModulesManager page of the developer documentation (docs/src/developer_folder/managers.rst, section Modules Manager)

Each test runs the code shown in the page, on mock control modules answering immediately, so that the page stays true.
"""
import numpy as np
import pytest
from qtpy.QtCore import QObject, Signal

from pymodaq.control_modules.enums import MoveType
from pymodaq.control_modules.thread_commands import ControlToHardwareMove, ControlToHardwareViewer
from pymodaq.utils.data import DataActuator
from pymodaq.utils.managers.modules import ModulesManager
from pymodaq_data.data import DataRaw, DataToExport
from pymodaq_utils.utils import ThreadCommand


class MockDetector(QObject):
    grab_done_signal = Signal(DataToExport)
    command_hardware = Signal(ThreadCommand)

    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self.Naverage = 1
        self.command_hardware.connect(self._on_command)

    def _on_command(self, cmd: ThreadCommand):
        if cmd.command == ControlToHardwareViewer.SINGLE:
            self.grab_done_signal.emit(
                DataToExport(self.title, data=[DataRaw('signal', data=[np.zeros((10,))], origin=self.title)]))


class MockActuator(QObject):
    move_done_signal = Signal(DataActuator)
    current_value_signal = Signal(DataActuator)
    command_hardware = Signal(ThreadCommand)

    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self.command_hardware.connect(self._on_command)

    def _on_command(self, cmd: ThreadCommand):
        if cmd.command == ControlToHardwareMove.MOVE_ABS:
            dact = cmd.attribute[0]
            dact.origin = self.title
            self.move_done_signal.emit(dact)


@pytest.fixture
def modules_manager(qtbot):
    return ModulesManager(detectors=[MockDetector('Det1'), MockDetector('Det2')],
                          actuators=[MockActuator('X'), MockActuator('Y')])


class MoveThenGrab:
    """Use case 1: move, then grab, without blocking the GUI"""

    def __init__(self, modules_manager: ModulesManager):
        self.modules_manager = modules_manager
        self.data = None

    def start(self, positions: dict[str, float], detectors: list[str]):
        dte_move = DataToExport('targets', data=[DataActuator(name, data=value)
                                                 for name, value in positions.items()])
        self.modules_manager.selected_detectors_name = detectors
        self.modules_manager.move_actuators_with_callback(dte_move, mode=MoveType.ABS,
                                                          callback=self._on_move_done)

    def _on_move_done(self, dte_positions: DataToExport):
        self.modules_manager.grab_data_with_callback(callback=self._on_grab_done)

    def _on_grab_done(self, dte: DataToExport):
        self.data = dte


def test_move_then_grab_with_callbacks(qtbot, modules_manager):
    use_case = MoveThenGrab(modules_manager)
    with qtbot.waitSignal(modules_manager.det_done_signal, timeout=5000):
        use_case.start({'X': 1.0, 'Y': 2.0}, ['Det2'])

    assert use_case.data.get_origins() == ['Det2']
    assert [dact.value() for dact in modules_manager.move_done_positions] == [1.0, 2.0]
    assert not modules_manager.actuators_connected and not modules_manager.detectors_connected


def test_blocking_move_and_grab(modules_manager):
    """Use case 2: the blocking calls, for code running in a loop (modules must be connected first)"""
    modules_manager.selected_actuators_name = ['X']
    modules_manager.selected_detectors_name = ['Det1']
    modules_manager.connect_actuators()
    modules_manager.connect_detectors()
    try:
        positions = modules_manager.move_actuators(DataToExport('targets', data=[DataActuator('X', data=3.0)]),
                                                   mode=MoveType.ABS)
        dte = modules_manager.grab_data()
    finally:
        modules_manager.connect_actuators(False)
        modules_manager.connect_detectors(False)

    assert positions[0].value() == 3.0
    assert dte.get_origins() == ['Det1']


def test_the_selection_is_empty_after_the_lists_are_set(modules_manager):
    """Use case 3: choose the modules, and start again from an empty selection when the experiment changes"""
    modules_manager.selected_actuators_name = ['Y', 'unknown']  # ignored as a whole: one name is unknown
    assert modules_manager.selected_actuators_name == []

    modules_manager.selected_actuators_name = ['Y']
    assert [act.title for act in modules_manager.actuators] == ['Y']
    assert modules_manager.Nactuators == 1

    selections = []
    modules_manager.actuators_changed.connect(selections.append)
    modules_manager.actuators_all = list(modules_manager.actuators_all)  # what a new experiment does
    assert modules_manager.selected_actuators_name == []
    assert selections == [[]]


def test_grab_without_connection_times_out(qtbot, modules_manager, monkeypatch):
    """The detectors have to be connected before the blocking grab"""
    monkeypatch.setattr(ModulesManager, 'detector_timeout', 300)
    modules_manager.selected_detectors_name = ['Det1']
    with qtbot.waitSignal(modules_manager.timeout_signal, timeout=5000) as blocker:
        dte = modules_manager.grab_data()
    assert blocker.args[0] == ['Det1']
    assert len(dte) == 0


def test_move_with_a_wrong_number_of_positions_times_out(qtbot, modules_manager, monkeypatch):
    monkeypatch.setattr(ModulesManager, 'actuator_timeout', 0.3)
    modules_manager.selected_actuators_name = ['X', 'Y']
    modules_manager.connect_actuators()
    try:
        with qtbot.waitSignal(modules_manager.timeout_signal, timeout=5000) as blocker:
            modules_manager.move_actuators(DataToExport('targets', data=[DataActuator('X', data=1.0)]))
    finally:
        modules_manager.connect_actuators(False)
    assert blocker.args[0] == ['X', 'Y']
