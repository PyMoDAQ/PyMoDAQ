from pathlib import Path
from typing import Union

import qt_themes
from qtpy import QtGui, QtWidgets, QtCore

from pymodaq_gui.resources.material_icons import MaterialIcon
from pymodaq_utils.config import GlobalConfig as Config


config = Config()
theme = qt_themes.get_theme(config('gui', 'style', 'theme')[0])


def create_font(font_name=None, font_size=None, isbold=False, isitalic=False) -> QtGui.QFont:
    font = QtGui.QFont()
    if font_name is not None:
        font.setFamily(font_name)
    if font_size is not None:
        font.setPointSize(font_size)

    font.setBold(isbold)
    font.setItalic(isitalic)
    return font


def create_color(icon_color: Union[QtGui.QColor, str]) -> Union[QtGui.QColor, None]:
    if icon_color is not None:
        if isinstance(icon_color, str):
            try:
                icon_color = theme.__getattribute__(icon_color)
            except AttributeError:
                icon_color = QtGui.QColor(icon_color)
                if not icon_color.isValid():
                    icon_color = None
    return icon_color


def create_icon(icon_name: Union[QtGui.QIcon, str, Path],
                icon_color: Union[QtGui.QColor, bytes, str] = None,
                icon_checked_color: Union[QtGui.QColor, bytes, str] = None):
    """ Create an icon from various sources by order of preference:

    1) icon_name is an icon
    2) icon_name is a registered MaterialIcon
    3) icon_name is a real path to a png
    4) icon_name is a registered png in icon_library
    5) icon_name is a registered ThemeIcon
    6) icon_name is a registered StandardPixmap
    """

    if isinstance(icon_name, QtGui.QIcon):
        return icon_name
    elif resource_path_exists(
            MaterialIcon.resource_path(
                icon_name,
                style=MaterialIcon.Style(config('gui', 'style', 'icons', 'style')[0]),
                fill=config('gui', 'style', 'icons', 'fill')[0],
                size=config('gui', 'style', 'icons', 'size')[0])):
        icon = MaterialIcon(
            icon_name,
            style=MaterialIcon.Style(config('gui', 'style', 'icons', 'style')[0]),
            fill=config('gui', 'style', 'icons', 'fill')[0],
            size=config('gui', 'style', 'icons', 'size')[0])
        icon.set_color(create_color(icon_color))
        if icon_checked_color is not None:
            icon.set_color(create_color(icon_checked_color), state=QtGui.QIcon.State.On)
    elif Path(icon_name).is_file(): # Test if icon is in path
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(icon_name), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    elif resource_path_exists(f"icons:{icon_name}.png"):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(f"icons:{icon_name}.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    elif hasattr(QtGui.QIcon,'ThemeIcon') and hasattr(QtGui.QIcon.ThemeIcon, icon_name): # Test if icon is in Qt's library
        icon = QtGui.QIcon.fromTheme(getattr(QtGui.QIcon.ThemeIcon, icon_name))
    elif hasattr(QtWidgets.QStyle.StandardPixmap, icon_name):
        pixmapi = getattr(QtWidgets.QStyle.StandardPixmap, icon_name)
        icon = QtWidgets.QWidget().style().standardIcon(pixmapi)
    else:
        icon = QtGui.QIcon()
    return icon




def resource_path_exists(path: str) -> bool:
    return QtCore.QFile(path).exists()
