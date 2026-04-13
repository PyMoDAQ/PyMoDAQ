
import os
import sys
import warnings
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
                size, option.rect # type: ignore[attr-defined]
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

def apply_styling_rules(app : QtWidgets.QApplication):
    theme = cast(qt_themes.Theme, qt_themes.get_theme(config('gui', 'style', 'theme')[0]))
    style = config('gui', 'style', 'style')[0]
    qt_themes.set_theme(theme=theme, style=style)

    if theme.is_dark_theme():
        #Custom rules
        app.setStyle(WhiteCheckboxStyle(app.style()))


def mkQApp(name: str):
    app = mkQApppg(name)
    apply_styling_rules(app)

    return app


