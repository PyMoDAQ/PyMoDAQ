import pytest
from qtpy import QtWidgets
from pymodaq.utils.gui_utils.utils import QApplicationUtils, start_qapplication

class TestQApplication:

    def start_stop_event_loop(self):
        qapp = QApplicationUtils()
        app = qapp.start_qapplication()

        widget = QtWidgets.QWidget()
        widget.show()

        qapp.stop_q_application()

    def test_with_statement(self):

        with QApplicationUtils() as app:
            assert isinstance(app, QtWidgets.QApplication)

    def test_with_statement_with_other_qapplication(self):
        app = start_qapplication()

        with QApplicationUtils() as qapp:
            assert isinstance(qapp, QtWidgets.QApplication)
            assert qapp is app

    def test_with_statement_error(self):
        with pytest.raises(IOError):
            with QApplicationUtils() as app:
                assert isinstance(app, QtWidgets.QApplication)
                raise IOError('invalid test')
