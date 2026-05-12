from pathlib import Path
from typing import Union

import pyqtgraph as pg
import qt_themes
from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_gui.resources.material_icons import MaterialIcon
from pymodaq_utils.config import GlobalConfig as Config

config = Config()
theme = qt_themes.get_theme(config('gui', 'style', 'theme')[0])

def make_shape_icon(
    shape: str = "circle",
    filled: bool = True,
    size: int = 12,
    width: int = None,
    height: int = None,
    pen: QtGui.QPen = None,
    brush: QtGui.QBrush = None,
    **kwargs,
) -> QtGui.QIcon:
    """Return a small solid or outlined shape as a QIcon, using pyqtgraph's mkPen/mkBrush.

    Parameters
    ----------
    shape:
        Shape of the icon: 'circle', 'triangle', 'square', 'rectangle', or 'diamond'.
    filled:
        If True, the shape is filled; if False, only the outline is drawn.
    size:
        Diameter of the circle, side length of the square/diamond, or default side for triangle/rectangle in pixels (default 12).
    width:
        Width of the rectangle (if shape is 'rectangle'). If None, defaults to `size`.
    height:
        Height of the rectangle (if shape is 'rectangle'). If None, defaults to `size`.
    pen:
        QPen for the outline (e.g., pg.mkPen('blue', width=2)).
    brush:
        QBrush for filling the shape (e.g., pg.mkBrush('red')).
    **kwargs:
        Optional arguments for creating pen/brush if not provided:
        - color: str (default: 'black')
        - pen_width: int (default: 1)
        - pen_style: str (e.g., 'solid', 'dashed', 'dotted', 'dashdot', 'dashdotdot')
        - brush_color: str (default: same as color)
    """
    if width is None:
        width = size
    if height is None:
        height = size

    # Map string pen styles to Qt.PenStyle enums
    style_map = {
        "solid": QtCore.Qt.PenStyle.SolidLine,
        "dashed": QtCore.Qt.PenStyle.DashLine,
        "dotted": QtCore.Qt.PenStyle.DotLine,
        "dashdot": QtCore.Qt.PenStyle.DashDotLine,
        "dashdotdot": QtCore.Qt.PenStyle.DashDotDotLine,
        "none": QtCore.Qt.PenStyle.NoPen,
    }

    # Use the maximum of width/height to ensure the pixmap is large enough
    pixmap_size = max(width, height)
    pixmap = QtGui.QPixmap(pixmap_size, pixmap_size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    with QtGui.QPainter(pixmap) as painter:
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Create pen and brush if not provided
        if pen is None:
            color = kwargs.get("color", "black")
            pen_width = kwargs.get("pen_width", 1)
            pen_style = kwargs.get("pen_style", "solid")
            style = style_map.get(pen_style.lower(), QtCore.Qt.PenStyle.SolidLine)
            pen = pg.mkPen(color, width=pen_width)
            pen.setStyle(style)
        if brush is None and filled:
            brush_color = kwargs.get("brush_color", kwargs.get("color", "black"))
            brush = pg.mkBrush(brush_color)

        # Set brush and pen
        painter.setBrush(brush if filled else QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(pen if not filled else QtCore.Qt.PenStyle.NoPen)

        if shape == "circle":
            painter.drawEllipse(1, 1, size - 2, size - 2)
        elif shape == "triangle":
            # Draw an equilateral triangle pointing upwards
            half_size = size / 2
            triangle_height = (size * (3 ** 0.5)) / 2
            offset_y = (size - triangle_height) / 2
            points = [
                QtCore.QPointF(half_size, offset_y),
                QtCore.QPointF(size - 1, size - offset_y - 1),
                QtCore.QPointF(1, size - offset_y - 1),
            ]
            polygon = QtGui.QPolygonF(points)
            painter.drawPolygon(polygon)
        elif shape == "square":
            painter.drawRect(1, 1, size - 2, size - 2)
        elif shape == "rectangle":
            painter.drawRect(1, 1, width - 2, height - 2)
        elif shape == "diamond":
            # Draw a diamond (rotated square)
            half_width = width / 2
            half_height = height / 2
            points = [
                QtCore.QPointF(half_width, 1),
                QtCore.QPointF(width - 1, half_height),
                QtCore.QPointF(half_width, height - 1),
                QtCore.QPointF(1, half_height),
            ]
            polygon = QtGui.QPolygonF(points)
            painter.drawPolygon(polygon)
        else:
            raise ValueError(f"Unsupported shape: {shape}")

        painter.end()
    return QtGui.QIcon(pixmap)

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
                if type(px) is not QtGui.QPixmap:
                    px = QtGui.QPixmap.fromImage(px)
                px_transformed = px.transformed(transform)
                if type(px) is not QtGui.QPixmap:
                    px_transformed = QtGui.QPixmap.fromImage(px.transformed(transform))
                new_icon.addPixmap(
                    px_transformed,
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

    1) icon_name is a MaterialIcon
    2) icon_name is a regular QIcon
    3) icon_name is a registered MaterialIcon
    4) icon_name is a real path to a png
    5) icon_name is a registered png in icon_library
    6) icon_name is a registered ThemeIcon
    7) icon_name is a registered StandardPixmap

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
    if isinstance(icon_name, MaterialIcon):
        icon_name.set_color(create_color(icon_color))
        if icon_checked_color is not None:
            icon_name.set_color(create_color(icon_checked_color), state=QtGui.QIcon.State.On)
        return _flip_icon(icon_name, flip_h, flip_v)
    elif isinstance(icon_name, QtGui.QIcon):  #cannot set Color on non MaterialIcons
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
    elif Path(icon_name).is_file():  # Test if icon is in path
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(icon_name), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    elif resource_path_exists(f"icons:{icon_name}.png"):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(f"icons:{icon_name}.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    elif hasattr(QtGui.QIcon,'ThemeIcon') and hasattr(QtGui.QIcon.ThemeIcon, icon_name):  # Test if icon is in Qt's library
        icon = QtGui.QIcon.fromTheme(getattr(QtGui.QIcon.ThemeIcon, icon_name))
    elif hasattr(QtWidgets.QStyle.StandardPixmap, icon_name):
        pixmapi = getattr(QtWidgets.QStyle.StandardPixmap, icon_name)
        icon = QtWidgets.QWidget().style().standardIcon(pixmapi)
    else:
        icon = QtGui.QIcon()
    return _flip_icon(icon, flip_h, flip_v)


def resource_path_exists(path: str) -> bool:
    return QtCore.QFile(path).exists()
