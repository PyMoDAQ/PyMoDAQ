"""
Colours of the pyqtgraph plots, following the qt_themes theme.

Plots are white on black with a dark theme and black on white with a light one.
The foreground colour (:func:`plot_foreground`) is also the first colour of
:class:`~pymodaq_data.plotting.utils.PlotColors`, the one of the first curve.

:func:`apply_plot_theme` sets these for plots created afterwards. It is called
at import and by :func:`pymodaq_gui.qt_utils.apply_theme`, before
``theme_changed`` is emitted. Plots already displayed follow the change if
registered with :func:`follow_plot_theme` (pymodaq's PlotWidget and the 2D
viewers' histograms are): their background, axes and labels take the new
defaults (unless given other colours), and their items drawn with the previous
foreground colour (curves, ROIs, crosshairs...) are redrawn with the new one.
"""
from typing import Tuple, Union

import pyqtgraph as pg
import qt_themes
from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))
config = GlobalConfig()

DARK_FOREGROUND = (255, 255, 255)
LIGHT_FOREGROUND = (0, 0, 0)

_foreground: Tuple[int, int, int] = DARK_FOREGROUND


def plot_foreground() -> Tuple[int, int, int]:
    """Colour of the plot items drawn in the foreground colour (first curve, ROI targets...)"""
    return _foreground


def apply_plot_theme(theme: Union[qt_themes.Theme, None]) -> Tuple[int, int, int]:
    """Set the plot colours matching *theme* for the plots created from now on.

    Sets pyqtgraph's background/foreground options and the first colour of
    ``config('data', 'plotting', 'plot_colors')``, in memory only (the configuration
    file is not written). Returns the foreground colour.
    """
    global _foreground
    dark = theme is None or theme.is_dark_theme()
    if dark:
        pg.setConfigOptions(foreground='d', background='k')
        _foreground = DARK_FOREGROUND
    else:
        pg.setConfigOptions(foreground='k', background='w')
        _foreground = LIGHT_FOREGROUND

    colors = list(config('data', 'plotting', 'plot_colors'))
    colors[0] = list(_foreground)
    config['data', 'plotting', 'plot_colors'] = colors

    # backward compatibility, for code reading pymodaq_gui.foreground_color
    import pymodaq_gui
    pymodaq_gui.foreground_color = _foreground
    return _foreground


def same_rgb(color, rgb: Tuple[int, int, int]) -> bool:
    """True if *color* (anything pyqtgraph's mkColor accepts) has the RGB components *rgb*"""
    color = pg.mkColor(color)
    return (color.red(), color.green(), color.blue()) == tuple(rgb)


def _recolor_pen(pen, old, new) -> Union[QtGui.QPen, None]:
    """Copy of *pen* with the colour *new* if it is drawn in *old*, else None"""
    if pen is None:
        return None
    pen = pg.mkPen(pen)
    if pen.style() == QtCore.Qt.PenStyle.NoPen or not same_rgb(pen.color(), old):
        return None
    color = QtGui.QColor(*new, pen.color().alpha())
    pen.setColor(color)
    return pen


def _recolor_brush(brush, old, new) -> Union[QtGui.QBrush, None]:
    if brush is None:
        return None
    brush = pg.mkBrush(brush)
    if brush.style() == QtCore.Qt.BrushStyle.NoBrush or not same_rgb(brush.color(), old):
        return None
    return pg.mkBrush(QtGui.QColor(*new, brush.color().alpha()))


def _restyle_item(item: QtWidgets.QGraphicsItem, old, new, old_axis):
    if isinstance(item, pg.AxisItem):
        # no argument: back to the foreground option, unless given another colour
        if same_rgb(item.pen().color(), old_axis):
            item.setPen()
        if same_rgb(item.textPen().color(), old_axis):
            item.setTextPen()
    elif isinstance(item, pg.LabelItem):
        if item.opts.get('color') is None:
            item.setText(item.text)  # colour resolved from the foreground option when rendered
    elif isinstance(item, pg.PlotDataItem):
        # Set on the curve and scatter items rather than with PlotDataItem.setPen...,
        # which would process the data again
        pen = _recolor_pen(item.opts.get('pen'), old, new)
        if pen is not None:
            item.opts['pen'] = pen
            item.curve.setPen(pen)
        symbol_pen = _recolor_pen(item.opts.get('symbolPen'), old, new)
        if symbol_pen is not None:
            item.opts['symbolPen'] = symbol_pen
            item.scatter.setPen(symbol_pen)
        symbol_brush = _recolor_brush(item.opts.get('symbolBrush'), old, new)
        if symbol_brush is not None:
            item.opts['symbolBrush'] = symbol_brush
            item.scatter.setBrush(symbol_brush)
    elif isinstance(item, pg.FillBetweenItem):
        brush = _recolor_brush(item.brush(), old, new)
        if brush is not None:
            item.setBrush(brush)
    elif isinstance(item, (pg.InfiniteLine, pg.ROI)):
        pen = _recolor_pen(item.pen, old, new)
        if pen is not None:
            item.setPen(pen)


def axis_foreground() -> Tuple[int, int, int]:
    """RGB of pyqtgraph's foreground option: the default colour of axes and labels"""
    color = pg.mkColor(pg.getConfigOption('foreground'))
    return color.red(), color.green(), color.blue()


def restyle_plot(view: pg.GraphicsView, old: Tuple[int, int, int], new: Tuple[int, int, int],
                 old_axis: Tuple[int, int, int]):
    """Restyle *view* after a change of the plot colours (:func:`apply_plot_theme`).

    Its background, axes and labels, if left to their defaults (the axes drawn in
    *old_axis*, the previous foreground option), take the new defaults, and its items
    drawn in the previous foreground colour *old* are redrawn in *new*.
    """
    if getattr(view, '_background', 'default') == 'default':
        view.setBackground('default')
    if old == new:
        return
    for item in view.scene().items():
        try:
            _restyle_item(item, old, new, old_axis)
        except Exception as e:  # e.g. an item being deleted: the others should still follow
            logger.debug(f'Could not restyle {item}: {e}')


class PlotThemeFollower(QtCore.QObject):
    """Restyles a plot on theme change. A child of the plot: deleted, and so
    disconnected, with it."""

    def __init__(self, view: pg.GraphicsView):
        super().__init__(view)
        self._foreground = plot_foreground()
        self._axis_foreground = axis_foreground()
        from pymodaq_gui.qt_utils import theme_signaller
        theme_signaller.theme_changed.connect(self.restyle)

    @QtCore.Slot(object)
    def restyle(self, _theme=None):
        new = plot_foreground()
        restyle_plot(self.parent(), self._foreground, new, self._axis_foreground)
        self._foreground = new
        self._axis_foreground = axis_foreground()


def follow_plot_theme(view: pg.GraphicsView) -> PlotThemeFollower:
    """Make *view* (a PlotWidget, HistogramLUTWidget...) follow theme changes"""
    return PlotThemeFollower(view)
