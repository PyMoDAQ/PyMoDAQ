"""
Animation Demo — PyMoDAQ.

Three-tab showcase of AnimatedIconEngine:
  • Tab 1 – Icon Animations   : every BaseAnimation subclass on shape icons
  • Tab 2 – Action Animations : animated QActions on a QToolBar
  • Tab 3 – Material Icons    : MaterialIcon + animation

Run with:
    python -m pymodaq_gui.examples.animated_actions
"""
import sys
from qtpy import QtWidgets, QtCore

from pymodaq_gui.utils.styling import (
    animate_icon, create_icon, make_shape_icon,
)
from pymodaq_gui.utils.animation import (
    Spin, Pulse, Breathe, Fade, HeartBeat,ColorCycle,
    Shake, Swing, Elastic, Travel, CompositeAnimation,
)

_ICON_SIZE = QtCore.QSize(32, 32)
_BTN_STYLE = QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon
_COLS = 3


class AnimationDemo(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyMoDAQ — Animation Demo")
        self.resize(900, 620)

        tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(tabs)
        tabs.addTab(self._build_combined_tab(), "Animations")
        tabs.addTab(self._build_material_tab(), "Material Icons")

    # ------------------------------------------------------------------
    def _build_combined_tab(self) -> QtWidgets.QWidget:
        """Toolbar QActions at the top, icon-button grid below."""

        # --- toolbar actions -------------------------------------------
        action_entries = [
            ("Run",       make_shape_icon("circle",   size=24, color="limegreen"),
             Spin(self, step=2),
             "Spin — active processing"),
            ("Pause",     make_shape_icon("square",   size=22, color="orange"),
             Fade(self, min_opacity=0.1, period=800),
             "Fade — waiting for resume"),
            ("Scan",      make_shape_icon("triangle", size=24, color="dodgerblue"),
             Pulse(self),
             "Pulse — scan in progress"),
            ("Connected", make_shape_icon("circle",   size=24, color="teal"),
             HeartBeat(self, period=1200),
             "HeartBeat — device alive"),
            ("Error",     make_shape_icon("diamond",  size=24, color="red"),
             Shake(self, amplitude_x=3, amplitude_y=0, period=150),
             "Shake — needs attention"),
        ]

        toolbar = QtWidgets.QToolBar()
        toolbar.setIconSize(QtCore.QSize(28, 28))
        toolbar.setToolButtonStyle(_BTN_STYLE)

        action_timers = []
        for label, icon, anim, _ in action_entries:
            action = QtWidgets.QAction(icon, label, self)
            toolbar.addAction(action)
            animate_icon(action, anim)
            action_timers.append((label, action._animation_timer))

        controls_box = QtWidgets.QGroupBox("Toggle toolbar animations")
        controls_layout = QtWidgets.QHBoxLayout(controls_box)
        for label, timer in action_timers:
            btn = QtWidgets.QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.toggled.connect(
                lambda checked, t=timer: t.start() if checked else t.stop()
            )
            controls_layout.addWidget(btn)

        # --- icon-button grid ------------------------------------------
        composite = CompositeAnimation(self, [
            Spin(self, step=2, autostart=False),
            Breathe(self, autostart=False),
        ])

        # (label, animation, color, shape, tooltip)
        icon_entries = [
            ("Spin",        Spin(self, step=3),
             "limegreen",    "circle",   "Continuous rotation"),
            ("Pulse",       Pulse(self),
             "dodgerblue",   "square",   "Stepped 45° rotation"),
            ("Breathe",     Breathe(self, min_scale=0.7, max_scale=1.3),
             "mediumorchid", "circle",   "Smooth scale pulse"),
            ("Fade",        Fade(self, min_opacity=0.1, period=800),
             "orange",       "square",   "Opacity blink"),
            ("HeartBeat",   HeartBeat(self, period=1000),
             "tomato",       "circle",   "Double-pulse then pause"),
            ("Shake",       Shake(self, amplitude_x=4, amplitude_y=0, period=150),
             "crimson",      "diamond",  "Horizontal vibration"),
            ("Swing",       Swing(self, angle=20),
             "teal",         "triangle", "Pendulum rotation"),
            ("Elastic",     Elastic(self),
             "gold",         "circle",   "Spring overshoot"),
            ("Travel X",    Travel(self, direction='x', period=1500),
             "mediumseagreen", "square", "Horizontal wrap-around travel"),
            ("Travel Y",    Travel(self, direction='y', period=1500),
             "cornflowerblue", "circle", "Vertical wrap-around travel"),
            ("Travel XY",   Travel(self, direction='xy', period=1800),
             "darkorange",   "diamond",  "Diagonal wrap-around travel"),
            ("Composite\nSpin+Breathe", composite,
             "steelblue",    "triangle", "Combined animations"),
        ]

        grid_widget = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(grid_widget)
        grid.setSpacing(16)

        for idx, (label, anim, color, shape, tip) in enumerate(icon_entries):
            icon = make_shape_icon(shape, size=28, color=color)
            btn = QtWidgets.QToolButton()
            btn.setIconSize(_ICON_SIZE)
            btn.setToolButtonStyle(_BTN_STYLE)
            btn.setText(label)
            btn.setToolTip(tip)
            animate_icon(btn, anim, icon)
            grid.addWidget(btn, idx // _COLS, idx % _COLS)

        # --- assemble --------------------------------------------------
        wrapper = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(wrapper)
        vbox.addWidget(toolbar)
        vbox.addWidget(controls_box)
        vbox.addWidget(QtWidgets.QLabel("<h3>Icon animations</h3>"))
        vbox.addWidget(grid_widget)
        vbox.addStretch()
        return wrapper

    # ------------------------------------------------------------------
    def _build_material_tab(self) -> QtWidgets.QWidget:
        """Animated MaterialIcons on QToolButtons."""

        # (material icon name, color hint, animation, label, tooltip)
        entries = [
            ("replay", "limegreen",    Spin(self, step=2),
             "Run",        "Spin — processing"),
            ("pause_circle",      "orange",       Fade(self, min_opacity=0.1, period=700),
             "Pause",      "Fade — blinking pause"),
            ("sync_lock",       "dodgerblue",   Pulse(self),
             "Sync",       "Pulse — syncing"),
            ("camera",   "tomato",       HeartBeat(self, period=900),
             "Heartbeat",  "HeartBeat — alive"),
            ("arrows_input", "blue",     Breathe(self, min_scale=0.7, max_scale=1.3),
             "Focus",       "Focusing"),
            ("settings",   "teal",         Spin(self, step=1, interval=30),
             "Settings",   "Slow spin — configuring"),
            ("help",   "yellow",                Swing(self, angle=20),
             "Help",   "Swing — Looking for help"),
            ("security",    "red",          Shake(self, amplitude_x=3, amplitude_y=0, period=120),
             "Warning",    "Shake — attention needed"),
            ("lightbulb",   "tomato",       ColorCycle(self, interval=100),
             "Color",  "ColorCycle — processing"),
            ("moving",   "purple",       Travel(self, direction=(1.0,-1.0), period=1500),
             "Moving",  "Travel  — moving"),
        ]

        grid_widget = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(grid_widget)
        grid.setSpacing(20)

        cols = 3
        for idx, (name, color, anim, label, tip) in enumerate(entries):
            icon = create_icon(name, icon_color=color)
            btn = QtWidgets.QToolButton()
            btn.setIconSize(QtCore.QSize(40, 40))
            btn.setToolButtonStyle(_BTN_STYLE)
            btn.setText(label)
            btn.setToolTip(tip)
            animate_icon(btn, anim, icon)
            grid.addWidget(btn, idx // cols, idx % cols)

        desc_lines = "".join(
            f"<li><b>{lbl}</b>: {tip}</li>"
            for _, _, _, lbl, tip in entries
        )
        wrapper = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(wrapper)
        vbox.addWidget(QtWidgets.QLabel(
            "<h3>MaterialIcon + animation</h3>"
            "<p>Same engine, same animation classes — just a different icon source.</p>"
            f"<ul>{desc_lines}</ul>"
        ))
        vbox.addWidget(grid_widget)
        vbox.addStretch()
        return wrapper


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = AnimationDemo()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
