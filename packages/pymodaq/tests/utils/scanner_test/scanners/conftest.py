import pytest

from pymodaq_gui.parameter import Parameter
from pymodaq.utils.scanner.scanner import Scanner
from pymodaq.utils.scanner.scan_factory import ScannerFactory

UNITS = ['nm', 'kW', 'ms']


class MoveMock:
    def __init__(self, ind: int = 0):
        self.title = f'act_{ind}'
        self.units = UNITS[ind]


@pytest.fixture
def make_scanner(qtbot):
    """Return a function building a scanner from the factory with n_act mocked actuators"""
    def _make(scan_type: str, scan_subtype: str, n_act: int = 1):
        settings = Parameter.create(name='settings', type='group', children=Scanner.params)
        actuators = [MoveMock(ind) for ind in range(n_act)]
        return ScannerFactory().get(scan_type, scan_subtype, actuators=actuators, settings=settings)
    return _make


def assert_steps_consistent(scanner):
    """The quick evaluation of the number of steps must be equal to the really calculated one"""
    evaluated = scanner.evaluate_steps()
    scanner.set_scan()
    assert evaluated == scanner.n_steps, (
        f'{type(scanner).__name__}: evaluate_steps gave {evaluated}, real number of steps is {scanner.n_steps}')
    assert scanner.n_steps == len(scanner.positions)


def known_bug(*values, reason: str):
    """Parametrization of a case where evaluate_steps is known to differ from the real calculation"""
    return pytest.param(*values, marks=pytest.mark.xfail(strict=True, reason=reason))
