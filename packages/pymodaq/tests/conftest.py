import pytest
from qtpy import QtWidgets


@pytest.fixture
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    yield app


@pytest.fixture
def init_qt(qapp, qtbot):
    return qtbot