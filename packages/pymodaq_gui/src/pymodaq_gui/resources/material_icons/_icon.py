from __future__ import annotations

import enum
import importlib
import os

try:
    from qtpy import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtGui, QtWidgets

ColorRole = QtGui.QPalette.ColorRole
ColorGroup = QtGui.QPalette.ColorGroup
State = QtGui.QIcon.State
Mode = QtGui.QIcon.Mode


class SVGIcon(QtGui.QIcon):
    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path
        self._pixmap = QtGui.QPixmap(path)
        self._init_colors()

    def __repr__(self) -> str:
        name = os.path.basename(self._path)
        return f'{self.__class__.__name__}({name!r})'

    def _init_colors(self) -> None:
        palette = QtWidgets.QApplication.palette()
        self._color_normal = palette.color(ColorGroup.Normal, ColorRole.WindowText)
        self._color_disabled = palette.color(ColorGroup.Disabled, ColorRole.WindowText)
        self.set_color(self._color_normal, Mode.Normal, State.Off)
        self.set_color(self._color_disabled, Mode.Disabled, State.Off)

    def set_icon(
        self,
        icon: QtGui.QIcon,
        mode: Mode = Mode.Normal,
        state: State = State.Off,
    ):
        if isinstance(icon, type(self)):
            pixmap = icon._pixmap
        else:
            pixmap = icon.pixmap(self._pixmap.size())
        self.addPixmap(pixmap, mode, state)

    def pixmap(
        self,
        size: QtCore.QSize | int = 0,
        mode: Mode = Mode.Normal,
        state: State = State.Off,
        color: QtGui.QColor | None = None,
    ) -> QtGui.QPixmap:
        if size:
            pixmap = QtGui.QIcon(self._path).pixmap(size)
        else:
            pixmap = self._pixmap

        if color is None:
            if state == State.Off and mode == Mode.Disabled:
                color = self._color_disabled
            else:
                color = self._color_normal
        return fill_pixmap(pixmap, color)

    def set_color(
        self,
        color: QtGui.QColor,
        mode: Mode = Mode.Normal,
        state: State = State.Off,
    ):
        self.addPixmap(self.pixmap(color=color), mode, state)


def fill_pixmap(pixmap: QtGui.QPixmap, color: QtGui.QColor) -> QtGui.QPixmap:
    """
    Return a copy of 'pixmap' filled with 'color'.
    """
    pixmap = QtGui.QPixmap(pixmap)
    painter = QtGui.QPainter(pixmap)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return pixmap


class MaterialIcon(SVGIcon):
    class Style(enum.Enum):
        OUTLINED = 'outlined'
        ROUNDED = 'rounded'
        SHARP = 'sharp'

    OUTLINED = Style.OUTLINED
    ROUNDED = Style.ROUNDED
    SHARP = Style.SHARP

    def __init__(
        self,
        name: str,
        style: Style = Style.OUTLINED,
        fill: bool = False,
        size: int = 20,
    ) -> None:
        self.name = name
        self.import_resource(style, size)
        super().__init__(MaterialIcon.resource_path(name, style, fill, size))

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.name!r})'

    @staticmethod
    def import_resource(style: MaterialIcon.Style, size: int) -> None:
        """
        Imports the resource for Qt, separated by style to not load unneeded SVGs.
        """

        importlib.import_module(f'{__package__}.resources.icons_{style.value}_{size}')

    @staticmethod
    def resource_path(name: str, style: Style, fill: bool, size: int) -> str:
        """Return the resource path."""

        if fill:
            filename = f'{name}_fill1_{size}px.svg'
        else:
            filename = f'{name}_{size}px.svg'
        path = (
            f':/material-design-icons/symbols/web/{name}/'
            f'materialsymbols{style.value}/{filename}'
        )
        return path

    @staticmethod
    def resource_exists(name: str, style: Style, fill: bool, size: int) -> bool:
        """Return whether the resource for the requested icon exists."""

        path = MaterialIcon.resource_path(name, style, fill, size)
        return QtCore.QFile(path).exists()
