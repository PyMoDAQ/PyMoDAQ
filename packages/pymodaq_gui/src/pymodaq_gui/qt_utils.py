
import os
import sys
import warnings
from pathlib import Path
from typing import cast, Union

import qt_themes
from pyqtgraph import mkQApp as mkQApppg

from qtpy.QtWidgets import QProxyStyle, QStyle
from qtpy.QtGui import QPainter, QColor, QPixmap
from qtpy.QtCore import QSize
from qtpy.QtSvg import QSvgRenderer


from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import QLocale, Qt
from pymodaq_utils import logger as logger_module
from pymodaq_utils.config import GlobalConfig as Config

from pymodaq_gui.qvariant import QVariant


logger = logger_module.set_logger(logger_module.get_module_name(__file__))

config = Config()


class ThemeSignaller(QtCore.QObject):
    """Emits ``theme_changed(theme)`` each time :func:`apply_theme` applies a theme."""
    theme_changed = QtCore.Signal(object)


theme_signaller = ThemeSignaller()


TOOLBAR_BUTTON_STYLES = {
    'icon_only': QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly,
    'text_only': QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly,
    'text_beside_icon': QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
    'text_under_icon': QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
    'follow_style': QtCore.Qt.ToolButtonStyle.ToolButtonFollowStyle,
}


def get_toolbar_button_style() -> QtCore.Qt.ToolButtonStyle | None:
    """The toolbar button style set in the configuration, None if it is not set or not valid"""
    name = config.get(('gui', 'style', 'toolbar_button_style'), [None])[0]
    return TOOLBAR_BUTTON_STYLES.get(name)


class ToolbarStyleSignaller(QtCore.QObject):
    """Emits ``style_changed(style)`` each time the global toolbar button style changes."""
    style_changed = QtCore.Signal(object)


toolbar_style_signaller = ToolbarStyleSignaller()


class ToolbarStyleChecks(QtCore.QObject):
    """Keeps the checkable toolbar style actions in sync, lives as long as the menu it is parented to"""

    def __init__(self, actions: dict[str, QtGui.QAction], parent: QtCore.QObject) -> None:
        super().__init__(parent)
        self._actions = actions
        toolbar_style_signaller.style_changed.connect(self.sync)

    @QtCore.Slot(object)
    def sync(self, style: Qt.ToolButtonStyle) -> None:
        for name, action in self._actions.items():
            action.setChecked(TOOLBAR_BUTTON_STYLES[name] == style)


class ThemeChecks(QtCore.QObject):
    """Keeps the checkable theme actions in sync, lives as long as the menu it is parented to"""

    def __init__(self, actions: dict[str, QtGui.QAction], themes: dict[str, qt_themes.Theme],
                 parent: QtCore.QObject):
        super().__init__(parent)
        self._actions = actions
        self._themes = themes
        theme_signaller.theme_changed.connect(self.sync)

    @QtCore.Slot(object)
    def sync(self, theme: qt_themes.Theme):
        for name, action in self._actions.items():
            action.setChecked(self._themes[name] == theme)


class MenuIconRefresher(QtCore.QObject):
    """Rebuilds a menu icon on theme change, lives as long as the menu it is parented to"""

    def __init__(self, icon_name: Union[str, Path], parent: QtWidgets.QMenu):
        super().__init__(parent)
        self._icon_name = icon_name
        theme_signaller.theme_changed.connect(self.refresh)

    @QtCore.Slot(object)
    def refresh(self, _theme=None):
        from pymodaq_gui.utils.styling import create_icon
        self.parent().setIcon(create_icon(self._icon_name))


class WhiteCheckboxStyle(QProxyStyle):
    _pixmap_cache: dict = {}
    def _get_checkbox_pixmap(self, checked : bool, size: QSize) -> QPixmap:
        icon_name = "check_box" if checked else "check_box_outline_blank"
        key = (checked, size.width(), size.height())
        if key not in self._pixmap_cache:
            from pymodaq_gui.utils.styling import create_icon
            icon = create_icon(icon_name, icon_color="white")
            self._pixmap_cache[key] = icon.pixmap(size)
        return self._pixmap_cache[key]


    def drawPrimitive(self, element:QtWidgets.QStyle.PrimitiveElement, option: QtWidgets.QStyleOption,
                      painter: QtGui.QPainter, widget: Union[QtWidgets.QWidget, None] = None):
        if element == QStyle.PrimitiveElement.PE_IndicatorCheckBox:
            size = QSize(18, 18)
            state = bool(option.state & QStyle.StateFlag.State_On)  # type: ignore[attr-defined]
            checkbox = self._get_checkbox_pixmap(state, size)

            icon_rect = self.baseStyle().alignedRect(
                Qt.LayoutDirection.LeftToRight, Qt.AlignmentFlag.AlignCenter,
                size, option.rect,  # type: ignore[attr-defined]
            )
            painter.drawPixmap(icon_rect.topLeft(), checkbox)
        else:
            super().drawPrimitive(element, option, painter, widget)


def decode_data(encoded_data):
    """
    Decode QbyteArrayData generated when drop items in table/tree/list view
    Parameters
    ----------
    encoded_data: QByteArray
                    Encoded data of the mime data to be dropped
    Returns
    -------
    data: list
            list of dict whose key is the QtRole in the Model, and the value a QVariant

    """
    data = []

    ds = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
    while not ds.atEnd():
        row = ds.readInt32()
        col = ds.readInt32()

        map_items = ds.readInt32()
        item = {}
        for ind in range(map_items):
            key = ds.readInt32()
            #TODO check this is fine
            value = QVariant()
            #value = None
            ds >> value
            item[QtCore.Qt.ItemDataRole(key)] = value.value()
        data.append(item)
    return data


def setLocale():
    """
    defines the Locale to use to convert numbers to strings representation using language/country conventions
    Default is English and US
    """
    language = getattr(QLocale, config('gui', 'style', 'language'))
    country = getattr(QLocale, config('gui', 'style', 'country'))
    QLocale.setDefault(QLocale(language, country))


def center_widget_on_screen_and_show(widget: QtWidgets.QWidget):
    widget.show()
    qtRect = widget.frameGeometry()
    cPt = QtGui.QScreen.availableGeometry(QtWidgets.QApplication.primaryScreen()).center()
    qtRect.moveCenter(cPt)
    widget.move(qtRect.topLeft())


def start_qapplication(name='default_app') -> QtWidgets.QApplication:
    return mkQApp(name=name)

def apply_theme(theme: Union[str, qt_themes.Theme], style: str = None,
                app: QtWidgets.QApplication = None) -> Union[qt_themes.Theme, None]:
    """Apply a qt_themes theme to the running application, at startup or at any time later.

    Sets the application palette and style, re-applies PyMoDAQ's custom rules (the
    style proxy making checkboxes visible on dark themes, which a new style would
    otherwise drop) and emits ``theme_signaller.theme_changed``.

    Widgets built from the palette repaint by themselves, and so do the icons of
    :class:`~pymodaq_gui.managers.action_manager.ActionManager` actions and menus
    given by name and the pymodaq plots (they listen to ``theme_changed``, see
    :mod:`pymodaq_gui.plotting.plot_theme`). Anything else whose colours were
    computed once from the theme should listen to ``theme_signaller.theme_changed``.

    Parameters
    ----------
    theme: str or qt_themes.Theme
        A theme or the name of one (see ``qt_themes.get_themes()``)
    style: str, optional
        Qt style name. Defaults to the configured one (``config('gui', 'style', 'style')[0]``)
    app: QApplication, optional
        Defaults to the running instance

    Returns
    -------
    qt_themes.Theme or None
        The applied theme, None if *theme* is an unknown name
    """
    if isinstance(theme, str):
        name = theme
        theme = qt_themes.get_theme(name)
        if theme is None:
            logger.warning(f'Unknown theme {name!r}, theme not changed')
            return None
    if app is None:
        app = QtWidgets.QApplication.instance()
    if style is None:
        style = config('gui', 'style', 'style')[0]

    # Palette first, then style: setting the style re-polishes every widget, which is
    # what makes widgets under a style sheet (e.g. in a pyqtgraph Dock) take the new
    # palette. qt_themes.set_theme(theme, style) does it the other way round.
    qt_themes.set_theme(theme=theme, style=None)
    QtWidgets.QApplication.setStyle(style)
    if app is not None and theme.is_dark_theme():
        # Custom rules
        app.setStyle(WhiteCheckboxStyle(app.style()))

    # Before emitting: plots restyle on theme_changed from the new plot colours
    from pymodaq_gui.plotting.plot_theme import apply_plot_theme
    apply_plot_theme(theme)

    theme_signaller.theme_changed.emit(theme)
    return theme


def apply_styling_rules(app : QtWidgets.QApplication):
    theme = cast(qt_themes.Theme, qt_themes.get_theme(config('gui', 'style', 'theme')[0]))
    style = config('gui', 'style', 'style')[0]
    apply_theme(theme, style=style, app=app)


def mkQApp(name: str):
    app = mkQApppg(name)
    apply_styling_rules(app)

    return app


