from pathlib import Path
from random import choice, choices

import numpy as np
from pyqtgraph import mkColor
from qtpy import QtGui, QtWidgets

from pymodaq_gui.resources.material_icons import MaterialIcon
from pymodaq_gui.utils.styling import resource_path_exists
from pymodaq_gui.utils.custom_app import CustomApp

from pymodaq_gui.utils.styling import create_icon

import toml

here = Path(__file__).parent
icons = toml.load(here.parent.joinpath('resources/icons.toml'))['icons']['names']
icons.sort()

class Icons():
    def __init__(self, widget: QtWidgets.QWidget, with_transform=False):
        super().__init__()
        self.widget = widget

        Ncol = 6

        self.widget.setLayout(QtWidgets.QVBoxLayout())

        layout_material = QtWidgets.QGridLayout()
        for n, name in enumerate(icons):
            btn = QtWidgets.QPushButton(name)
            icon = create_icon(name,
                               icon_color=mkColor(*choices(np.arange(256), k=3)),
                               flip_h=choice((True, False)) if with_transform else False,
                               flip_v=choice((True, False)) if with_transform else False,
                               fill=choice((True, False)) if with_transform else False,
                               rotate=choice(np.arange(360)) if with_transform else False,
                               )
            btn.setIcon(icon)

            layout_material.addWidget(btn, int(n/Ncol), int(n%Ncol))

        self.widget.layout().addLayout(layout_material)

def main():
    from pymodaq_gui.qt_utils import mkQApp
    import sys
    app = mkQApp("Icon list")

    w = Icons(QtWidgets.QWidget(), False)
    w.widget.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()