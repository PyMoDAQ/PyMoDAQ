import pytest
from qtpy import QtCore, QtGui, QtWidgets
from pymodaq_gui.utils.widgets.painter_utils import draw_shape, make_brush, desaturate, SHAPES, GRADIENTS
from pymodaq_gui.utils.widgets.multistate_led import MultistateLED


# ---------------------------------------------------------------------------
# draw_shape
# ---------------------------------------------------------------------------

class TestDrawShape:

    @pytest.fixture(autouse=True)
    def pixmap_painter(self, qapp):
        self.pixmap = QtGui.QPixmap(40, 40)
        self.pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        self.painter = QtGui.QPainter(self.pixmap)
        self.painter.setBrush(QtGui.QBrush(QtGui.QColor('red')))
        self.painter.setPen(QtCore.Qt.PenStyle.NoPen)
        self.rect = QtCore.QRectF(2, 2, 36, 36)
        yield
        self.painter.end()

    @pytest.mark.parametrize("shape", SHAPES)
    def test_all_shapes_paint_without_error(self, shape):
        draw_shape(self.painter, shape, self.rect)

    def test_invalid_shape_raises(self):
        with pytest.raises(ValueError, match="Unknown shape"):
            draw_shape(self.painter, 'hexagon', self.rect)

    def test_circle_paints_pixels(self):
        draw_shape(self.painter, 'circle', self.rect)
        self.painter.end()
        img = self.pixmap.toImage()
        center = img.pixel(20, 20)
        assert QtGui.QColor(center).red() > 200

    def test_square_paints_pixels(self):
        draw_shape(self.painter, 'square', self.rect)
        self.painter.end()
        img = self.pixmap.toImage()
        center = img.pixel(20, 20)
        assert QtGui.QColor(center).red() > 200


# ---------------------------------------------------------------------------
# desaturate
# ---------------------------------------------------------------------------

class TestDesaturate:

    def test_red_becomes_grey(self):
        red = QtGui.QColor('red')
        grey = desaturate(red)
        assert grey.saturation() == 0

    def test_lightness_preserved(self):
        color = QtGui.QColor.fromHsl(120, 200, 100)
        grey = desaturate(color)
        assert grey.lightness() == color.lightness()

    def test_already_grey_unchanged(self):
        grey = QtGui.QColor.fromHsl(0, 0, 128)
        result = desaturate(grey)
        assert result.saturation() == 0
        assert result.lightness() == grey.lightness()


# ---------------------------------------------------------------------------
# MultistateLED — shape and disabled-state
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# make_brush
# ---------------------------------------------------------------------------

class TestMakeBrush:

    @pytest.fixture(autouse=True)
    def rect(self):
        self.rect = QtCore.QRectF(0, 0, 40, 40)
        self.color = QtGui.QColor('#00b400')

    @pytest.mark.parametrize("gradient", GRADIENTS)
    def test_all_styles_return_brush(self, gradient):
        brush = make_brush(self.color, self.rect, gradient=gradient)
        assert isinstance(brush, QtGui.QBrush)

    def test_flat_is_solid(self):
        brush = make_brush(self.color, self.rect, gradient='flat')
        assert brush.style() == QtCore.Qt.BrushStyle.SolidPattern

    def test_radial_is_radial_gradient(self):
        brush = make_brush(self.color, self.rect, gradient='radial')
        assert brush.style() == QtCore.Qt.BrushStyle.RadialGradientPattern

    def test_linear_is_linear_gradient(self):
        brush = make_brush(self.color, self.rect, gradient='linear')
        assert brush.style() == QtCore.Qt.BrushStyle.LinearGradientPattern

    def test_glow_is_radial_gradient(self):
        brush = make_brush(self.color, self.rect, gradient='glow')
        assert brush.style() == QtCore.Qt.BrushStyle.RadialGradientPattern

    def test_glow_edge_is_transparent(self):
        brush = make_brush(self.color, self.rect, gradient='glow')
        stops = brush.gradient().stops()
        edge_color = stops[-1][1]
        assert edge_color.alpha() == 0

    def test_linear_angle_0_and_90_differ(self):
        b0  = make_brush(self.color, self.rect, gradient='linear', angle=0.0)
        b90 = make_brush(self.color, self.rect, gradient='linear', angle=90.0)
        g0  = b0.gradient()
        g90 = b90.gradient()
        assert g0.start() != g90.start()

    def test_invalid_gradient_raises(self):
        with pytest.raises(ValueError, match="Unknown gradient"):
            make_brush(self.color, self.rect, gradient='sparkle')


# ---------------------------------------------------------------------------
# MultistateLED — gradient parameter
# ---------------------------------------------------------------------------

class TestMultistateLEDGradient:

    @pytest.mark.parametrize("gradient", GRADIENTS)
    def test_valid_gradients_construct(self, qapp, gradient):
        led = MultistateLED(gradient=gradient)
        assert led._gradient == gradient

    def test_invalid_gradient_raises(self, qapp):
        with pytest.raises(ValueError, match="Unknown gradient"):
            MultistateLED(gradient='sparkle')


class TestMultistateLEDShape:

    @pytest.mark.parametrize("shape", SHAPES)
    def test_valid_shapes_construct(self, qapp, shape):
        led = MultistateLED(shape=shape)
        assert led is not None

    def test_invalid_shape_raises(self, qapp):
        with pytest.raises(ValueError, match="Unknown shape"):
            MultistateLED(shape='hexagon')

    def test_shape_stored(self, qapp):
        led = MultistateLED(shape='diamond')
        assert led._shape == 'diamond'


class TestMultistateLEDDisabled:

    def test_enabled_color_is_saturated(self, qapp, qtbot):
        led = MultistateLED(states=[('on', '#00b400')], size=40)
        qtbot.addWidget(led)
        led.show()
        led.setEnabled(True)
        qtbot.waitExposed(led)
        img = led.grab().toImage()
        center = img.pixel(20, 20)
        assert QtGui.QColor(center).saturation() > 0

    def test_disabled_color_is_desaturated(self, qapp, qtbot):
        led = MultistateLED(states=[('on', '#00b400')], size=40)
        qtbot.addWidget(led)
        led.show()
        led.setEnabled(False)
        qtbot.waitExposed(led)
        img = led.grab().toImage()
        center = img.pixel(20, 20)
        assert QtGui.QColor(center).saturation() == 0
