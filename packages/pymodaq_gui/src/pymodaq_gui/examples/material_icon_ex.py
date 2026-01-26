from pathlib import Path

from qtpy import QtGui, QtWidgets

from pymodaq_gui.resources.material_icons import MaterialIcon
from pymodaq_gui.utils.styling import resource_path_exists
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_utils.config import Config
from pymodaq_gui.utils.styling import create_icon

import toml

config = Config()
here = Path(__file__).parent
icons = toml.load(here.parent.joinpath('resources/icons.toml'))['icons']['names']
icons.sort()

class Icons():
    def __init__(self, widget: QtWidgets.QWidget):
        super().__init__()
        self.widget = widget

        Ncol = 6

        self.widget.setLayout(QtWidgets.QVBoxLayout())

        layout_material = QtWidgets.QGridLayout()
        for n, name in enumerate(icons):
            btn = QtWidgets.QPushButton(name)
            btn.setIcon(create_icon(name))

            layout_material.addWidget(btn, int(n/Ncol), int(n%Ncol))

        self.widget.layout().addLayout(layout_material)

def main():
    from pymodaq_gui.qt_utils import mkQApp
    import sys
    app = mkQApp("Icon list")

    w = Icons(QtWidgets.QWidget())
    w.widget.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()