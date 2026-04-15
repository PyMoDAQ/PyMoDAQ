from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal
from pymodaq_gui.utils.utils import clickable

# Default two-state set — visually matches QLED
DEFAULT_STATES = [
    ('false', '#c80000'),
    ('true',  '#00b400'),
]


class MultistateLED(QtWidgets.QWidget):
    """A painted circular LED indicator that can represent any number of named states.

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
        When ``True`` (default) mouse clicks have no effect.
    clickable_cycle : bool
        When ``True`` (default) and *readonly* is ``False``, each click
        advances to the next state in order, wrapping around.  When
        ``False``, clicking only toggles between the first and last state.
    size : int
        Diameter of the LED circle in pixels (default 20).
    """

    state_changed = Signal(str)  # emits state name

    def __init__(
        self,
        parent=None,
        states=None,
        readonly: bool = True,
        clickable_cycle: bool = True,
        size: int = 20,
    ):
        super().__init__(parent)
        self._states: list[tuple[str, QtGui.QColor]] = []
        self._diameter = size
        self._readonly = readonly
        self._cycle = clickable_cycle

        states = states if states is not None else DEFAULT_STATES
        for name, color in states:
            # Accept both QColor objects (e.g. from StatusPalette) and strings
            self._states.append((name, color if isinstance(color, QtGui.QColor) else QtGui.QColor(color)))

        if not self._states:
            raise ValueError("states must contain at least one entry")

        self._index = 0  # index into self._states

        self.setFixedSize(self._diameter, self._diameter)
        clickable(self).connect(self._on_click)

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

    def setReadOnly(self, readonly: bool):
        self._readonly = readonly

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        _, color = self._states[self._index]
        d = min(self.width(), self.height()) - 2
        x = (self.width()  - d) // 2
        y = (self.height() - d) // 2

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        gradient = QtGui.QRadialGradient(x + d * 0.35, y + d * 0.35, d * 0.55)
        gradient.setColorAt(0.0, color.lighter(160))
        gradient.setColorAt(1.0, color.darker(130))

        painter.setBrush(QtGui.QBrush(gradient))
        painter.setPen(QtGui.QPen(color.darker(160), 1))
        painter.drawEllipse(x, y, d, d)
        painter.end()

    def sizeHint(self):
        return QtCore.QSize(self._diameter, self._diameter)

    # ------------------------------------------------------------------
    # Click handling
    # ------------------------------------------------------------------

    def _on_click(self):
        if self._readonly:
            return
        n = len(self._states)
        if self._cycle:
            new_index = (self._index + 1) % n
        else:
            # toggle: first ↔ last
            new_index = n - 1 if self._index != n - 1 else 0
        self._index = new_index
        self.update()
        self.state_changed.emit(self._states[self._index][0])


def main():
    app = QtWidgets.QApplication([])
    from pymodaq_gui.utils.status_palette import StatusPalette

    w = MultistateLED(states=StatusPalette.as_states(), readonly=False)
    timer = QtCore.QTimer(w, interval=1000, timeout=lambda: w._on_click)
    timer.start()
    w.resize(640, 480)
    w.show()
    return app.exec_()


if __name__ == '__main__':
    main()