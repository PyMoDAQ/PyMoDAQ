import pytest
from pytestqt import qtbot
from qtpy import QtWidgets

from pymodaq_gui.utils.custom_app import CustomApp


class MyApp(CustomApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setup_ui()

    def setup_docks(self):
        self.n_iter_widget = QtWidgets.QSpinBox()
        self.statusbar.addPermanentWidget(self.n_iter_widget)

    def setup_actions(self):
        pass

    def connect_things(self):
        pass


@pytest.fixture()
def app(qtbot):
    main_window = QtWidgets.QMainWindow()
    my_app = MyApp(parent=main_window, title="My App")
    main_window.show()
    qtbot.addWidget(main_window)
    main_window.show()
    yield my_app

    main_window.close()
    main_window.deleteLater()


def test_status_bar(app):
    my_app = app

    my_app.update_status('a message for 2s', wait_time=2000)
    my_app.n_iter_widget.setValue(24)