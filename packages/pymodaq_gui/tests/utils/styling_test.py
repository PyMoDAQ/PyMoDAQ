from pathlib import Path

import pytest
from pyqtgraph import mkColor
from qtpy import QtWidgets
from pymodaq_gui.utils.styling import create_icon
import random

from pymodaq_gui.examples.material_icon_ex import Icons, icons

def test_material_icons(qtbot):
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    icon_widget = Icons(widget)
    widget.show()


@pytest.mark.parametrize("fliph, flipv, rotate",
                         [(True, True, 45),
                          (True, False, 180),
                          (False, True, -45),
                          ])
def test_icon_transform(qtbot, fliph, flipv, rotate):

    icon_name = random.choice(icons)
    create_icon(icon_name=icon_name,
                flip_h=fliph,
                flip_v=flipv,
                rotate=rotate)


def test_icon_color_transform(qtbot):
    icon_name = random.choice(icons)

    icon = create_icon(icon_name=icon_name,
                       icon_color=mkColor(123, 45, 45),
                       flip_h=True,
                       flip_v=True,
                       rotate=45)

    button = QtWidgets.QPushButton(icon_name)
    button.setIcon(icon)
    qtbot.addWidget(button)
    button.show()
    pass


