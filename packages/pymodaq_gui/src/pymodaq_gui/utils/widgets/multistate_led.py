from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal
from pymodaq_gui.utils.widgets.painter_utils import draw_shape, make_brush, desaturate, SHAPES, GRADIENTS

# Default two-state set — visually matches QLED
DEFAULT_STATES = [
    ('false', '#c80000'),
    ('true',  '#00b400'),
]


class MultistateLED(QtWidgets.QWidget):
    """A painted LED indicator that can represent any number of named states.

    Each state is a (name, color) pair supplied at construction time.  The
    widget emits ``state_changed`` with the state name whenever the active
    state changes.

    Parameters
    ----------
    parent : QWidget, optional
    states : list of (str, str | QColor), optional
        Ordered ``[(name, color), ...]`` pairs.  *color* can be a hex string
        (``'#rrggbb'``), an SVG color name, or a ``QColor`` instance (e.g.
        from :class:`~pymodaq_gui.utils.status_palette.StatusPalette`).
        Defaults to a two-state red/green set.
    readonly : bool
        When ``True`` (default) clicking has no effect.  Sets ``self.clickable``
        to ``not readonly`` — assign ``w.clickable`` directly to change at
        runtime (same pattern as :class:`~pymodaq_gui.utils.widgets.qled.QLED`).
    clickable_cycle : bool
        When ``True`` (default) each click advances to the next state in
        order, wrapping around.  When ``False``, clicking only toggles between
        the first and last state.
    size : int
        Diameter / side length of the shape in pixels (default 20).
    shape : str
        Visual shape: one of ``'circle'``, ``'square'``, ``'triangle'``,
        ``'diamond'``, ``'rectangle'``.  Defaults to ``'circle'``.
    gradient : str
        Fill style passed to :func:`~pymodaq_gui.utils.widgets.painter_utils.make_brush`.
        One of ``'flat'`` (default), ``'radial'``, ``'linear'``, ``'glow'``.
    """

    state_changed = Signal(str)  # emits state name

    def __init__(
        self,
        parent=None,
        states=None,
        readonly: bool = True,
        clickable_cycle: bool = True,
        size: int = 20,
        shape: str = 'circle',
        gradient: str = 'radial',
    ):
        super().__init__(parent)
        if shape not in SHAPES:
            raise ValueError(f"Unknown shape {shape!r}. Valid shapes: {SHAPES}")
        if gradient not in GRADIENTS:
            raise ValueError(f"Unknown gradient {gradient!r}. Valid styles: {GRADIENTS}")

        self._states: list[tuple[str, QtGui.QColor]] = []
        self._diameter = size
        self.clickable = not readonly   # public — set directly to change at runtime
        self._cycle = clickable_cycle
        self._gradient = gradient
        self._shape = shape

        states = states if states is not None else DEFAULT_STATES
        for name, color in states:
            self._states.append(
                (name, color if isinstance(color, QtGui.QColor) else QtGui.QColor(color))
            )

        if not self._states:
            raise ValueError("states must contain at least one entry")

        self._index = 0  # index into self._states

        self.setFixedSize(self._diameter, self._diameter)
        self._update_cursor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self) -> str:
        """Return the current state name."""
        return self._states[self._index][0]

    def set_state(self, name: str):
        """Set the active state by name.  Emits ``state_changed`` if changed."""
        for i, (n, _) in enumerate(self._states):
            if n == name:
                if i != self._index:
                    self._index = i
                    self.update()
                    self.state_changed.emit(name)
                return
        raise ValueError(f"Unknown state {name!r}. Valid states: {[n for n, _ in self._states]}")

    def state_names(self) -> list[str]:
        """Return the ordered list of state names."""
        return [n for n, _ in self._states]

    def set_states(self, states: list):
        """Replace the full state list.  Current state is reset to index 0."""
        if not states:
            raise ValueError("states must contain at least one entry")
        self._states = [
            (name, color if isinstance(color, QtGui.QColor) else QtGui.QColor(color))
            for name, color in states
        ]
        self._index = 0
        self.update()

    def set_gradient(self, gradient: str):
        if gradient not in GRADIENTS:
            raise ValueError(f"Unknown gradient {gradient!r}. Valid styles: {GRADIENTS}")
        self._gradient = gradient
        self.update()

    def set_shape(self, shape: str):
        if shape not in SHAPES:
            raise ValueError(f"Unknown shape {shape!r}. Valid shapes: {SHAPES}")
        self._shape = shape
        self.update()

    def set_size(self, size: int):
        self._diameter = size
        self.setFixedSize(size, size)
        self.update()

    def cycle(self):
        """Advance to the next state programmatically (ignores ``clickable``)."""
        n = len(self._states)
        new_index = (self._index + 1) % n if self._cycle else (n - 1 if self._index != n - 1 else 0)
        self._index = new_index
        self.update()
        self.state_changed.emit(self._states[self._index][0])

    def _update_cursor(self):
        if self.clickable:
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        _, color = self._states[self._index]
        if not self.isEnabled():
            color = desaturate(color)

        border_width = max(1, self._diameter // 12)
        margin = border_width
        d = min(self.width(), self.height()) - 2 * margin
        x = (self.width()  - d) / 2
        y = (self.height() - d) / 2
        rect = QtCore.QRectF(x, y, d, d)

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setBrush(make_brush(color, rect, gradient=self._gradient))
        painter.setPen(QtGui.QPen(color.darker(160), 1))                                                                                                                                                                                                 
        draw_shape(painter, self._shape, rect)
        painter.end()

    def sizeHint(self):
        return QtCore.QSize(self._diameter, self._diameter)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.Type.EnabledChange:
            self.update()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Click handling
    # ------------------------------------------------------------------

    def mouseReleaseEvent(self, event):
        if self.clickable and self.rect().contains(event.pos()):
            n = len(self._states)
            if self._cycle:
                new_index = (self._index + 1) % n
            else:
                new_index = n - 1 if self._index != n - 1 else 0
            self._index = new_index
            self.update()
            self.state_changed.emit(self._states[self._index][0])
        event.accept()


def main():
    app = QtWidgets.QApplication([])
    from pymodaq_gui.utils.status_palette import StatusPalette

    w = MultistateLED(states=StatusPalette.as_states(), readonly=False)
    timer = QtCore.QTimer(w, interval=1000)
    timer.timeout.connect(w.cycle)
    timer.start()
    w.resize(640, 480)
    w.show()
    return app.exec_()


if __name__ == '__main__':
    main()
