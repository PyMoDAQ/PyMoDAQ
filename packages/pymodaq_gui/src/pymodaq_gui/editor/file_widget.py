from pathlib import Path

from qt_themes import get_theme
from qtpy import QtWidgets, QtCore
from pymodaq_gui.utils.styling import create_icon
from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()



class FileWidget(QtWidgets.QFrame):

    close_signal = QtCore.Signal(Path)

    def __init__(self, filepath: Path, parent=None):
        super().__init__(parent)

        self.path = filepath
        self.close_button: QtWidgets.QPushButton = None
        self.file_name_button: QtWidgets.QPushButton = None

        self.setup_ui()

    def setup_ui(self):
        self.setLayout(QtWidgets.QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.file_name_button = QtWidgets.QPushButton(self.path.name)
        self.file_name_button.setToolTip(str(self.path))

        self.file_name_button.setCheckable(True)
        self.file_name_button.setFlat(True)

        self.layout().addWidget(self.file_name_button)
        self.close_button = QtWidgets.QPushButton()
        self.close_button.setIcon(
            create_icon('close', get_theme(config('gui', 'style', 'theme')[0]).red))
        self.close_button.setVisible(False)
        self.close_button.setFlat(True)
        self.close_button.setMaximumWidth(20)
        self.close_button.clicked.connect(lambda: self.close_signal.emit(self.path))
        self.file_name_button.toggled.connect(self.show_close)
        self.layout().addWidget(self.close_button)

    def show_close(self, show=True):
        self.close_button.setVisible(show)


class FileWidgetAction(QtWidgets.QWidgetAction):

    def __init__(self, file_path: Path, parent=None):
        super().__init__(parent)

        self.setDefaultWidget(FileWidget(file_path))

    def defaultWidget(self, /) -> FileWidget:
        return super().defaultWidget()


def main():
    from pymodaq_gui.utils.utils import mkQApp

    qapp = mkQApp('Monaco')

    widget = FileWidget(Path(__file__))
    widget.show()

    qapp.exec_()


if __name__ == "__main__":
    main()