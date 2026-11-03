"""The text of a time value can come from a file: it must never be able to run code."""
import pytest
from qtpy import QtCore

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import pymodaq_ptypes  # registers the parameter types
from pymodaq_utils.utils import UnsafeExpressionError


@pytest.fixture
def time_param(qtbot):
    return Parameter.create(name='p', type='time', value=QtCore.QTime(1, 2, 3))


def test_unsafe_time_text_is_refused(time_param):
    with pytest.raises(UnsafeExpressionError):
        time_param.setValue("QTime(__import__('sys').version_info[:3])")

    assert time_param.value() == QtCore.QTime(1, 2, 3)


@pytest.mark.parametrize('text', ['PySide6.QtCore.QTime(10, 5, 3, 0)', 'PyQt6.QtCore.QTime(10, 5, 3)',
                                  'PyQt5.QtCore.QTime(10, 5)'])
def test_time_text_of_older_versions_is_still_read(time_param, text):
    time_param.setValue(text)

    assert time_param.value().hour() == 10
    assert time_param.value().minute() == 5


def test_time_value_round_trip(time_param):
    time_param.setValue(QtCore.QTime(7, 8, 9))

    assert time_param.value() == QtCore.QTime(7, 8, 9)
