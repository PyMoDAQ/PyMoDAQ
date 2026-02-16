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

def transform_icon(icon: QtGui.QIcon, transform: QtGui.QTransform) -> QtGui.QIcon:
    """Return a new QIcon with all pixmaps transformed by transform.
    
    Parameters
    ----------
    icon: QtGui.QIcon
        The icon to transform.
        
    transform: QtGui.QTransform
        The transform to apply to the icon.
    """
    new_icon = QtGui.QIcon()
    sizes = icon.availableSizes() or [QtCore.QSize(s, s) for s in (20, 40)]
    for size in sizes:
        for state in (QtGui.QIcon.State.Off, QtGui.QIcon.State.On):
            px = icon.pixmap(size, QtGui.QIcon.Mode.Normal, state)
            if not px.isNull():
                new_icon.addPixmap(
                    QtGui.QPixmap.fromImage(px.transformed(transform)),
                    QtGui.QIcon.Mode.Normal,
                    state,
                )
    return new_icon

def _translate_icon(icon: QtGui.QIcon, x: int = 0, y: int = 0) -> QtGui.QIcon:
    """Return a new QIcon with all pixmaps translated by x and y pixels.
    
    Parameters
    ----------
    icon: QtGui.QIcon
        The icon to translate.
        
    x: int
        The number of pixels to translate the icon in the x direction.
        
    y: int
        The number of pixels to translate the icon in the y direction.
    """
    transform = QtGui.QTransform().translate(x, y)
    return transform_icon(icon, transform)

def _scale_icon(icon: QtGui.QIcon, scale_x: float = 1.0, scale_y: float = None) -> QtGui.QIcon:
    """Return a new QIcon with all pixmaps scaled by scale.
    
    Parameters
    ----------
    icon: QtGui.QIcon
        The icon to scale.
        
    scale: float
        The scale factor to apply to the icon.
    """
    if scale_y is None:
        scale_y = scale_x
    transform = QtGui.QTransform().scale(scale_x, scale_y)
    return transform_icon(icon, transform)

def _rotate_icon(icon: QtGui.QIcon, angle: int = 0) -> QtGui.QIcon:
    """Return a new QIcon with all pixmaps rotated by angle degrees.
    
    Parameters
    ----------
    icon: QtGui.QIcon
        The icon to rotate.
        
    angle: int
        The angle in degrees to rotate the icon.
    """
    transform = QtGui.QTransform().rotate(angle)
    return transform_icon(icon, transform)    


def _flip_icon(icon: QtGui.QIcon, flip_h: bool, flip_v: bool) -> QtGui.QIcon:
    """Return a new QIcon with all Normal-mode pixmaps mirrored.

    Only the Normal mode is transformed; Qt derives Disabled/Active/Selected
    variants automatically.  Both Off and On states are handled so that
    checkable actions with two visual states work correctly.

    For SVG/vector icons (e.g. MaterialIcon) ``availableSizes()`` returns an
    empty list; the function falls back to the two standard Material sizes
    (20 × 20 and 40 × 40) so the icon is still rendered at a usable resolution.
    """
    if not flip_h and not flip_v:
        return icon
    sx = -1.0 if flip_h else 1.0
    sy = -1.0 if flip_v else 1.0
    return _scale_icon(icon, scale_x=sx, scale_y=sy)


def create_icon(icon_name: Union[QtGui.QIcon, str, Path],
                icon_color: Union[QtGui.QColor, bytes, str] = None,
                icon_checked_color: Union[QtGui.QColor, bytes, str] = None,
                flip_h: bool = False,
                flip_v: bool = False):
    """ Create an icon from various sources by order of preference:

    1) icon_name is an icon
    2) icon_name is a registered MaterialIcon
    3) icon_name is a real path to a png
    4) icon_name is a registered png in icon_library
    5) icon_name is a registered ThemeIcon
    6) icon_name is a registered StandardPixmap

    Parameters
    ----------
    icon_name:
        Icon source — see priority list above.
    icon_color:
        Colour applied to the unchecked/off-state icon (MaterialIcon only).
    icon_checked_color:
        Colour applied to the checked/on-state icon (MaterialIcon only).
    flip_h:
        Mirror the icon horizontally (left ↔ right).
    flip_v:
        Mirror the icon vertically (top ↔ bottom).
    """

    if isinstance(icon_name, QtGui.QIcon):
        return _flip_icon(icon_name, flip_h, flip_v)
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
    return _flip_icon(icon, flip_h, flip_v)


def resource_path_exists(path: str) -> bool:
    return QtCore.QFile(path).exists()
