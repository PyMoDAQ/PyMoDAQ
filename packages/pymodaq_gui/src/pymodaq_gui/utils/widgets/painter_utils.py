import math
from qtpy import QtCore, QtGui

SHAPES = ('circle', 'square', 'triangle', 'diamond', 'rectangle')
GRADIENTS = ('flat', 'radial', 'linear', 'glow')


# ---------------------------------------------------------------------------
# Brush factory
# ---------------------------------------------------------------------------

def make_brush(
    color: QtGui.QColor,
    rect: QtCore.QRectF,
    gradient: str = 'flat',
    lighter: int = 160,
    darker: int = 130,
    angle: float = 90.0,
) -> QtGui.QBrush:
    """Return a ``QBrush`` suitable for filling a shape inside *rect*.

    Parameters
    ----------
    color : QColor
        Base fill colour.
    rect : QRectF
        Bounding box of the shape to be filled (used to size the gradient).
    gradient : str
        Fill style — one of:

        ``'flat'``
            Solid fill with *color*.
        ``'radial'``
            Off-centre radial gradient that mimics a sphere lit from the
            top-left: bright highlight fading to a darker edge.  Classic
            LED look.  Controlled by *lighter* / *darker*.
        ``'linear'``
            Linear gradient along *angle* degrees (0 = left → right,
            90 = top → bottom).  Runs from ``color.lighter(lighter)``
            to ``color.darker(darker)``.
        ``'glow'``
            Centred radial gradient: full *color* at the centre fading to
            transparent at the edge.  Useful for an "active" pulse effect.

    lighter : int
        ``QColor.lighter()`` factor applied to the bright end of the
        gradient (default 160).  Ignored for ``'flat'`` and ``'glow'``.
    darker : int
        ``QColor.darker()`` factor applied to the dark end of the gradient
        (default 130).  Ignored for ``'flat'`` and ``'glow'``.
    angle : float
        Angle in degrees for ``'linear'`` (default 90, top → bottom).
        0 = left → right, 180 = right → left, 270 = bottom → top.

    Raises
    ------
    ValueError
        If *gradient* is not one of the supported styles.
    """
    if gradient == 'flat':
        return QtGui.QBrush(color)

    if gradient == 'radial':
        cx = rect.x() + rect.width()  * 0.35
        cy = rect.y() + rect.height() * 0.35
        radius = max(rect.width(), rect.height()) * 0.55
        grad = QtGui.QRadialGradient(cx, cy, radius)
        grad.setColorAt(0.0, color.lighter(lighter))
        grad.setColorAt(1.0, color.darker(darker))
        return QtGui.QBrush(grad)

    if gradient == 'linear':
        rad = math.radians(angle)
        dx = math.sin(rad)   # angle=0 → pure horizontal, angle=90 → pure vertical
        dy = -math.cos(rad)
        hw, hh = rect.width() / 2, rect.height() / 2
        cx, cy = rect.center().x(), rect.center().y()
        start = QtCore.QPointF(cx - dx * hw, cy - dy * hh)
        end   = QtCore.QPointF(cx + dx * hw, cy + dy * hh)
        grad = QtGui.QLinearGradient(start, end)
        grad.setColorAt(0.0, color.lighter(lighter))
        grad.setColorAt(1.0, color.darker(darker))
        return QtGui.QBrush(grad)

    if gradient == 'glow':
        center = rect.center()
        radius = max(rect.width(), rect.height()) / 2
        grad = QtGui.QRadialGradient(center, radius)
        grad.setColorAt(0.0, color)
        transparent = QtGui.QColor(color)
        transparent.setAlpha(0)
        grad.setColorAt(1.0, transparent)
        return QtGui.QBrush(grad)

    raise ValueError(f"Unknown gradient {gradient!r}. Valid styles: {GRADIENTS}")


# ---------------------------------------------------------------------------
# Shape drawing
# ---------------------------------------------------------------------------

def draw_shape(painter: QtGui.QPainter, shape: str, rect: QtCore.QRectF) -> None:
    """Draw a named shape inside *rect* using the painter's current pen and brush.

    Parameters
    ----------
    painter : QPainter
        Active painter (must already be begun on a device).
    shape : str
        One of ``'circle'``, ``'square'``, ``'triangle'``, ``'diamond'``,
        ``'rectangle'``.
    rect : QRectF
        Bounding box (margins already applied by the caller).

    Raises
    ------
    ValueError
        If *shape* is not one of the supported values.
    """
    if shape == 'circle':
        painter.drawEllipse(rect)
    elif shape in ('square', 'rectangle'):
        painter.drawRect(rect)
    elif shape == 'triangle':
        cx = rect.center().x()
        points = [
            QtCore.QPointF(cx, rect.top()),
            QtCore.QPointF(rect.right(), rect.bottom()),
            QtCore.QPointF(rect.left(), rect.bottom()),
        ]
        painter.drawPolygon(QtGui.QPolygonF(points))
    elif shape == 'diamond':
        cx, cy = rect.center().x(), rect.center().y()
        points = [
            QtCore.QPointF(cx, rect.top()),
            QtCore.QPointF(rect.right(), cy),
            QtCore.QPointF(cx, rect.bottom()),
            QtCore.QPointF(rect.left(), cy),
        ]
        painter.drawPolygon(QtGui.QPolygonF(points))
    else:
        raise ValueError(f"Unknown shape {shape!r}. Valid shapes: {SHAPES}")


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def desaturate(color: QtGui.QColor) -> QtGui.QColor:
    """Return a greyscale version of *color* with the same HSL lightness."""
    return QtGui.QColor.fromHsl(0, 0, color.lightness())
