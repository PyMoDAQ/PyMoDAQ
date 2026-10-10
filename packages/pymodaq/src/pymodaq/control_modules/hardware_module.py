"""GUI side of one device: a window with an instrument toolbar and one toolbar per quantity.

A :class:`HardwareModule` attaches to the registry for its device and drives the returned
:class:`~pymodaq.control_modules.controller.Controller`. It never touches the plugin or the
hardware thread directly.

Layout: the instrument toolbar sits on top (Ini., status, Settings). A channel dock on the left holds
one ``QToolBar`` per declared quantity, built from
:func:`~pymodaq.control_modules.capabilities.toolbar_widgets`. Views (plots) open on the right.

The device is only polled while a channel is grabbed: ``Grab`` polls continuously, ``Snap`` and
``Read`` read once. ``Show Graph`` only opens or closes the view; a view shows whatever readings arrive.

Only the widgets handled in :meth:`HardwareModule._fill_channel_toolbar` are built; other default
names are skipped until they are implemented.
"""
from __future__ import annotations

import time
from collections import deque

import numpy as np
import pyqtgraph as pg
from pyqtgraph.parametertree import ParameterTree
from qt_themes import get_theme
from qtpy import QtWidgets
from qtpy.QtCore import QMetaObject, QTimer, Qt, Signal, Slot
from qtpy import QtGui
from qtpy.QtGui import QColor

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.utils.widget_sync import SyncMode, ValueSync
from pymodaq_gui.utils.widgets.multistate_led import MultistateLED

from pymodaq.control_modules.capabilities import Access, Quantity, toolbar_widgets
from pymodaq.control_modules.controller import Controller
from pymodaq.control_modules.enums import ActionIconNames
from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry

__all__ = ['HardwareModule']

INSTRUMENT_TOOLBAR = 'instrument'
HISTORY_LENGTH = 200  # points kept by the trace of a scalar measurement
DISPLAY_WIDTH = 150  # fixed columns: every row's actions start at the same position
VALUE_WIDTH = 130
SLIDER_WIDTH = 120
SLIDER_STEPS = 1000  # a slider maps its range onto this many steps
ACTION_WIDTH = 44  # room for one toolbar button
SETTLE_POLL_MS = 150.0  # how often a settling control's readback is checked against its target
SETTLE_TIMEOUT_S = 10.0  # give up waiting for a control to settle after this long


class _ViewDock(QtWidgets.QDockWidget):
    """A view dock that tells its owner when the user closes it."""

    closed = Signal()

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit()


class _FallbackColors:
    """Used when no theme is applied to the application, e.g. in a bare script or a test."""

    red = QColor('#d32f2f')
    green = QColor('#388e3c')
    blue = QColor('#1976d2')
    magenta = QColor('#8e24aa')
    orange = QColor('#f57c00')


def _colors():
    """The current theme, so that the icon colours follow the application's theme."""
    theme = get_theme()
    return theme if theme is not None else _FallbackColors


def _led_states() -> list[tuple[str, str]]:
    """The channel LED's five states, named for :meth:`HardwareModule._led_state`, coloured from
    the current theme like everything else here."""
    colors = _colors()
    return [
        ('closed', '#9e9e9e'),
        ('rejected', QColor(colors.red).name()),
        ('pending', QColor(colors.orange).name()),
        ('active', QColor(colors.blue).name()),
        ('idle', QColor(colors.green).name()),
    ]


def _caption(quantity: Quantity) -> str:
    """The text shown for a channel: its label in capitals, or its name made readable."""
    text = quantity.label or quantity.name.replace('_', ' ').capitalize()
    return text.upper()


def _range_of(quantity: Quantity) -> tuple[float, float]:
    """The declared range, with 0 to 1 standing in for a missing limit."""
    lo = 0.0 if quantity.lo is None else quantity.lo
    hi = 1.0 if quantity.hi is None else quantity.hi
    return lo, hi


def _format(data) -> str:
    """A short text for a toolbar: the value of a scalar, a summary of an array."""
    values = np.asarray(data)
    if values.size == 1:
        item = values.ravel()[0]
        return f'{item:.4g}' if np.issubdtype(values.dtype, np.number) else str(item)
    if np.issubdtype(values.dtype, np.number):
        return f'{values.shape} max {np.nanmax(values):.3g}'
    return str(values.shape)


class HardwareModule(QtWidgets.QMainWindow, ActionManager):
    """One device: instrument toolbar on top, channel toolbars in a dock on the left.

    Parameters
    ----------
    key :
        Identity of the device in the registry.
    plugin_class :
        The new-style plugin class of the device.
    params_state :
        Saved plugin settings, used only by the first module that attaches to *key*.
    registry :
        Registry to attach to. Defaults to the process-wide one.
    grab_period_ms :
        Polling period of a grabbed channel.
    """

    # Settings edited in the settings dock, sent to the hardware thread: (path, value, change).
    _settings_update = Signal(list, object, str)

    def __init__(self, key: HardwareKey, plugin_class: type, params_state: dict | None = None,
                 registry: HardwareRegistry | None = None, parent: QtWidgets.QWidget | None = None,
                 grab_period_ms: float = 200.0):
        QtWidgets.QMainWindow.__init__(self, parent)
        ActionManager.__init__(self)
        self._registry = registry if registry is not None else HardwareRegistry.get()
        self._key = key
        self._attached = True
        self._grab_period_ms = grab_period_ms
        self._grabbing: set[str] = set()
        self._quantities: dict[str, Quantity] = {}
        self._value_widgets: dict[str, QtWidgets.QWidget] = {}
        self._sliders: dict[str, QtWidgets.QSlider] = {}
        self._displays: dict[str, QtWidgets.QLabel] = {}
        self._views: dict[str, _ViewDock] = {}
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._history: dict[str, deque] = {}
        self._leds: dict[str, MultistateLED] = {}
        self._row_of: dict[str, str] = {}  # a channel's row: a control's row holds its readback too
        self._row_channels: dict[str, list[str]] = {}  # the channels of each row
        self._merged_into: dict[str, list[Quantity]] = {}  # a row's name: the controls merged into it
        # a quantity's name: a ValueSync every widget showing it is bound to (FROM_SYNC: the device's
        # confirmed value drives the widgets, not the other way - each widget's own edit still writes
        # through _write as before). Setting .value fans out to all of them, blockSignals handled by
        # the sync itself. See pymodaq_gui.utils.widget_sync.
        self._syncs: dict[str, ValueSync] = {}
        self._pending: set[str] = set()  # writes sent, not yet acknowledged, or not yet settled
        self._failed: set[str] = set()  # writes the plugin rejected, or that never settled
        self._reading: set[str] = set()  # one-shot reads in flight
        self._targets: dict[str, float] = {}  # a settling control's last requested value
        self._settle_timers: dict[str, QTimer] = {}  # settling controls: readback polled until within epsilon
        self._settle_deadlines: dict[str, float] = {}
        self.controller: Controller = self._registry.attach(key, plugin_class, params_state)
        self.setWindowTitle(plugin_class.__name__)
        self.setCentralWidget(QtWidgets.QWidget())  # the area the views will fill

        self.status_label = QtWidgets.QLabel('not open')
        self.setup_actions()
        self._build_channels(self.controller.capabilities)
        self._build_settings()
        self._settings_update.connect(self.controller.thread.update_settings)

        self.controller.device_status.connect(self._on_status)
        self.controller.device_error.connect(self._on_error)
        self.controller.written.connect(self._on_written)
        self.controller.write_failed.connect(self._on_write_failed)
        self.controller.action_done.connect(self._on_action_done)
        self.controller.action_failed.connect(self._on_action_failed)
        self.controller.new_reading.connect(self._on_reading)
        for name in self._quantities:
            self._refresh_led(name)

    @property
    def title(self) -> str:
        """For SharedUI: lets it merge this module's toolbars and menus when run standalone."""
        return self.windowTitle()

    # ── Layout ───────────────────────────────────────────────────────────────

    def setup_actions(self) -> None:
        """The instrument toolbar: the device's name, then Ini. and Settings, then its status far right."""
        theme = _colors()
        bar = self.add_toolbar(INSTRUMENT_TOOLBAR, 'Instrument', parent=self)

        title = QtWidgets.QLabel(self.title)
        title.setStyleSheet('font-weight: bold; font-size: 11pt;')
        self.add_widget('title', title, toolbar=INSTRUMENT_TOOLBAR)
        bar.addSeparator()

        self.add_action('ini', 'Ini.', ActionIconNames.INI, 'Open the device (uncheck to close it)',
                        checkable=True, icon_color=theme.red, icon_checked_color=theme.green,
                        toolbar=INSTRUMENT_TOOLBAR)
        self.connect_action('ini', lambda *_: self._set_device_open(self.get_action('ini').isChecked()))
        self.add_action('show_settings', 'Settings', 'settings', 'Show or hide the device settings',
                        checkable=True, icon_checked_color=theme.green, toolbar=INSTRUMENT_TOOLBAR)
        self.connect_action('show_settings', lambda *_: self.settings_dock.setVisible(
            self.get_action('show_settings').isChecked()))
        bar.addSeparator()

        spacer = QtWidgets.QWidget()  # pushes the status to the right end of the toolbar
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.add_widget('spacer', spacer, toolbar=INSTRUMENT_TOOLBAR)
        self.add_widget('status', self.status_label, toolbar=INSTRUMENT_TOOLBAR)

    def _build_settings(self) -> None:
        """The plugin's settings in a dock. Edits go to the hardware thread."""
        tree = ParameterTree(showHeader=False)
        tree.setParameters(self.controller.settings, showTop=False)
        self.controller.settings.sigTreeStateChanged.connect(self._relay_settings_change)
        self.settings_dock = QtWidgets.QDockWidget('Settings', self)
        self.settings_dock.setWidget(tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.settings_dock)
        self.settings_dock.hide()
        self.settings_dock.visibilityChanged.connect(
            lambda visible: self.get_action('show_settings').setChecked(visible))

    def _relay_settings_change(self, _, changes) -> None:
        if not self._attached or self.controller.thread is None or self.controller._syncing_from_device:
            return  # a change coming from the device, not the user: do not write it back
        for param, change, data in changes:
            path = self.controller.settings.childPath(param)
            if path is not None:
                self._settings_update.emit(path, data, change)

    def _build_channels(self, caps) -> None:
        """One toolbar per row, stacked in a dock on the left. A readback is shown in its control's row."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setSpacing(8)
        quantities = caps.measurements + caps.controls
        for quantity in quantities:
            self._quantities[quantity.name] = quantity
        for control in caps.controls:
            if control.merge_into:
                self._merged_into.setdefault(control.merge_into, []).append(control)
        merged_names = {c.name for controls in self._merged_into.values() for c in controls}
        linked = {q.readback for q in caps.controls if q.readback} | merged_names
        rows = [q for q in quantities if q.name not in linked]
        bold = QtWidgets.QLabel().font()
        bold.setBold(True)
        self._name_width = max((QtGui.QFontMetrics(bold).horizontalAdvance(_caption(q)) for q in rows),
                               default=0) + 16
        # a whole row fits without the toolbar's overflow arrow: name, display, value, its buttons, separators
        max_actions = max((self._row_action_count(q) for q in rows), default=4)
        container.setMinimumWidth(
            self._name_width + DISPLAY_WIDTH + VALUE_WIDTH + SLIDER_WIDTH + max_actions * ACTION_WIDTH + 60)
        for quantity in rows:
            bar = QtWidgets.QToolBar(quantity.name, container)
            self.reference_toolbar(quantity.name, bar)
            layout.addWidget(bar)
            self._fill_channel_toolbar(quantity)
        layout.addStretch()
        self.channels_dock = QtWidgets.QDockWidget('Channels', self)
        self.channels_dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.channels_dock)

    def _row_action_count(self, quantity: Quantity) -> int:
        """How many action buttons *quantity*'s row ends up with, to size the dock: its own, its
        readback's, and one per control merged into it."""
        channel = quantity.readback or quantity.name
        widgets = toolbar_widgets(quantity)
        if channel != quantity.name:
            widgets += [w for w in toolbar_widgets(self._quantities[channel]) if w not in widgets]
        return self._action_count(widgets) + len(self._merged_into.get(quantity.name, []))

    @staticmethod
    def _action_count(widgets: list[str]) -> int:
        """How many buttons :meth:`_actions_of` adds for *widgets*: read and label share one slot."""
        count = 1 if ('read' in widgets or 'label' in widgets) else 0
        count += sum(1 for w in ('snap', 'grab', 'show_graph') if w in widgets)
        not_a_button = {'value', 'selector', 'slider', 'toggle', 'show_controls', 'label',
                        'read', 'snap', 'grab', 'show_graph', 'save', 'history'}
        count += sum(1 for w in widgets if w not in not_a_button)  # stop, or any other declared action
        return count

    @staticmethod
    def _access_color(quantity: Quantity) -> str:
        """Measurements are blue and controls magenta, so the two kinds can be told apart at a glance."""
        colors = _colors()
        color = colors.blue if quantity.access is Access.MEASUREMENT else colors.magenta
        return QColor(color).name()  # a hex string, which a style sheet accepts

    def _fill_channel_toolbar(self, quantity: Quantity) -> None:
        """Name, display, value, actions, show graph: each row has the same slots, so the actions line up.

        The row is named after the quantity. A control's readback, when it has one, is the channel the
        display and the actions read.
        """
        row = quantity.name
        is_measurement = quantity.access is Access.MEASUREMENT
        channel = quantity.readback or row
        has_display = is_measurement or bool(quantity.readback)
        self._row_of[row] = row
        self._row_channels[row] = [row, channel] if channel != row else [row]
        self._row_of[channel] = row

        led = MultistateLED(states=_led_states(), size=12, readonly=True)  # the channel status: see _led_state
        self._leds[row] = led
        self.add_widget(f'{row}_led', led, toolbar=row)
        label = QtWidgets.QLabel(_caption(quantity))  # the label shown; the name stays the identifier
        label.setStyleSheet(f'color: {self._access_color(quantity)}; font-weight: bold; letter-spacing: 1px;')
        label.setFixedWidth(self._name_width)
        kind = 'measurement: read from the device' if is_measurement else 'control: set on the device'
        label.setToolTip(f'{row} ({kind})')
        self.add_widget(f'{row}_name', label, toolbar=row)

        widgets = toolbar_widgets(quantity)
        if channel != row:  # a control with a readback also has the actions of its readback
            widgets += [w for w in toolbar_widgets(self._quantities[channel]) if w not in widgets]
        bar = self.get_toolbar(row)
        bar.addSeparator()
        if has_display:
            self._add_display(channel, row)
        else:
            self._add_placeholder(row, 'display', DISPLAY_WIDTH)
        bar.addSeparator()
        if 'value' in widgets:
            self._add_value_spinbox(quantity)
        elif 'toggle' in widgets:
            self._add_toggle(quantity)
        elif 'selector' in widgets:
            self._add_selector(quantity)
        else:
            self._add_placeholder(row, 'value', VALUE_WIDTH)
        if 'slider' in widgets:
            self._add_slider(quantity)
        else:
            self._add_placeholder(row, 'slider', SLIDER_WIDTH)
        bar.addSeparator()
        self._actions_of(channel, row, widgets)()
        for merged in self._merged_into.get(row, []):
            self._add_merged_action(row, merged)
        if 'show_graph' in widgets:
            bar.addSeparator()
            self._add_show_graph_action(channel, row)
    def _add_placeholder(self, name: str, slot: str, width: int) -> None:
        """An empty column, so that a row without this slot keeps the others aligned."""
        spacer = QtWidgets.QWidget()
        spacer.setFixedWidth(width)
        self.add_widget(f'{name}_{slot}_slot', spacer, toolbar=name)

    def _actions_of(self, channel: str, row: str, widgets: list[str]):
        """A function adding the read, snap, grab and declared-action buttons the widgets ask for."""

        def add():
            if 'read' in widgets or 'label' in widgets:
                self._add_read_action(channel, row, 'Read', ActionIconNames.SNAP)
            if 'snap' in widgets:
                self._add_read_action(channel, row, 'Snap', ActionIconNames.SNAP)
            if 'grab' in widgets:
                self._add_grab_action(channel, row)
            # always the control's own channel: an action is declared on it, never on its readback
            for action_name in self._quantities[row].actions:
                if action_name in widgets:
                    self._add_action_button(row, action_name)
        return add
    def _add_display(self, channel: str, row: str) -> None:
        display = QtWidgets.QLabel('-')
        display.setFixedWidth(DISPLAY_WIDTH)
        display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._displays[channel] = display
        self.add_widget(f'{row}_display', display, toolbar=row)
    def _add_read_action(self, channel: str, row: str, text: str, icon: str) -> None:
        self.add_action(f'{channel}_read', text, icon, f'{text} the value once', toolbar=row)
        self.connect_action(f'{channel}_read', lambda *_, channel=channel: self._read(channel))
    def _add_grab_action(self, channel: str, row: str) -> None:
        theme = _colors()
        self.add_action(f'{channel}_grab', 'Grab', ActionIconNames.GRAB, 'Follow the value continuously',
                        checkable=True, icon_checked=ActionIconNames.GRAB_STOP,
                        icon_checked_color=theme.green, toolbar=row)
        self.connect_action(f'{channel}_grab', lambda *_, channel=channel: self._set_grabbing(
            channel, self.get_action(f'{channel}_grab').isChecked()))
    def _add_action_button(self, name: str, action_name: str) -> None:
        """A channel's one declared action as a button in its own row, its look taken from the
        declared :class:`~pymodaq.control_modules.capabilities.Action` (icon and label).

        A ``checkable`` one (e.g. a hardware dark-reference toggle) stays pressed between clicks
        instead of firing once; its new checked state is read off the button itself and passed along,
        since ``_run_action`` otherwise has no way to know which way it just flipped."""
        action = self._quantities[name].actions[action_name]
        label = action.label or action_name.replace('_', ' ').title()
        self.add_action(f'{name}_{action_name}', label, action.icon, f'{label} this control', toolbar=name,
                        checkable=action.checkable, **action.opts)
        button_name = f'{name}_{action_name}'
        if action.checkable:
            self.connect_action(button_name, lambda *_, name=name, action_name=action_name, button_name=button_name:
                                self._run_action(name, action_name, self.get_action(button_name).isChecked()))
        else:
            self.connect_action(button_name, lambda *_, name=name, action_name=action_name:
                                self._run_action(name, action_name))

    def _add_merged_action(self, row: str, quantity: Quantity) -> None:
        """A binary control (``merge_into``) as a checkable action in another control's own row, e.g.
        an axis's enable button, right next to its move controls instead of in a row of its own."""
        theme = _colors()
        label = _caption(quantity)
        self.add_action(f'{quantity.name}_merged', label, '', f'Toggle {label.lower()}', checkable=True,
                        icon_checked_color=theme.green, toolbar=row)
        self.connect_action(f'{quantity.name}_merged', lambda *_, quantity=quantity: self._write(
            quantity.name, quantity.values[1] if self.get_action(f'{quantity.name}_merged').isChecked()
            else quantity.values[0]))
        self._row_of[quantity.name] = row
        self._row_channels[row].append(quantity.name)
        action = self.get_action(f'{quantity.name}_merged')
        self._sync_for(quantity.name).bind(
            action, setter=lambda v: action.setChecked(quantity.values.index(v) == 1),
            mode=SyncMode.FROM_SYNC, init_from=None)

    def _add_show_graph_action(self, channel: str, row: str) -> None:
        self.add_action(f'{channel}_show_graph', 'Show Graph', 'bid_landscape', 'Show or hide the graph',
                        checkable=True, icon_checked='bid_landscape', icon_checked_color=_colors().green,
                        toolbar=row)
        self.connect_action(f'{channel}_show_graph', lambda *_, channel=channel: self._view(channel).setVisible(
            self.get_action(f'{channel}_show_graph').isChecked()))
    def _add_value_spinbox(self, quantity: Quantity) -> None:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e12 if quantity.lo is None else quantity.lo, 1e12 if quantity.hi is None else quantity.hi)
        spin.setSuffix(f' {quantity.units}' if quantity.units else '')
        spin.setFixedWidth(VALUE_WIDTH)
        spin.editingFinished.connect(lambda: self._write(quantity.name, spin.value()))
        self._value_widgets[quantity.name] = spin
        self.add_widget(f'{quantity.name}_value', spin, toolbar=quantity.name)
        self._sync_for(quantity.name).bind(spin, setter=spin.setValue, mode=SyncMode.FROM_SYNC, init_from=None)

    def _add_slider(self, quantity: Quantity) -> None:
        """A slider over the declared range. It writes when released, or at once for keyboard and wheel steps."""
        slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, SLIDER_STEPS)
        slider.setFixedWidth(SLIDER_WIDTH)
        slider.sliderReleased.connect(lambda: self._write(quantity.name, self._slider_value(quantity.name)))
        slider.valueChanged.connect(lambda _: None if slider.isSliderDown() else
                                    self._write(quantity.name, self._slider_value(quantity.name)))
        self._sliders[quantity.name] = slider
        self.add_widget(f'{quantity.name}_slider', slider, toolbar=quantity.name)

        def set_slider(value, slider=slider, quantity=quantity):
            lo, hi = _range_of(quantity)
            slider.setValue(round((value - lo) / (hi - lo) * SLIDER_STEPS))
        self._sync_for(quantity.name).bind(slider, setter=set_slider, mode=SyncMode.FROM_SYNC, init_from=None)

    def _slider_value(self, name: str) -> float:
        quantity = self._quantities[name]
        lo, hi = _range_of(quantity)
        return lo + (hi - lo) * self._sliders[name].value() / SLIDER_STEPS

    def _add_selector(self, quantity: Quantity) -> None:
        combo = QtWidgets.QComboBox()
        combo.addItems([str(v) for v in quantity.values])
        combo.setFixedWidth(VALUE_WIDTH)
        combo.activated.connect(lambda index: self._write(quantity.name, quantity.values[index]))
        self._value_widgets[quantity.name] = combo
        self.add_widget(f'{quantity.name}_selector', combo, toolbar=quantity.name)

        def set_combo(value, combo=combo, quantity=quantity):
            combo.setCurrentIndex(quantity.values.index(value))
        self._sync_for(quantity.name).bind(combo, setter=set_combo, mode=SyncMode.FROM_SYNC, init_from=None)

    def _add_toggle(self, quantity: Quantity) -> None:
        """A two-valued control as a checkable push button: pressed is the second value, like led_push."""
        button = QtWidgets.QPushButton(str(quantity.values[0]))
        button.setCheckable(True)
        button.setFixedWidth(VALUE_WIDTH)
        button.toggled.connect(lambda checked, quantity=quantity: self._toggle_clicked(quantity, checked))
        self._value_widgets[quantity.name] = button
        self.add_widget(f'{quantity.name}_toggle', button, toolbar=quantity.name)

        def set_toggle(value, button=button, quantity=quantity):
            button.setChecked(quantity.values.index(value) == 1)
            button.setText(str(value))
        self._sync_for(quantity.name).bind(button, setter=set_toggle, mode=SyncMode.FROM_SYNC, init_from=None)

    def _toggle_clicked(self, quantity: Quantity, checked: bool) -> None:
        value = quantity.values[1] if checked else quantity.values[0]
        self._value_widgets[quantity.name].setText(str(value))
        self._write(quantity.name, value)

    def _view(self, name: str) -> _ViewDock:
        """The view dock of *name*, created on first use and hidden until shown."""
        if name not in self._views:
            plot = pg.PlotWidget()
            self._curves[name] = plot.plot()
            self._history[name] = deque(maxlen=HISTORY_LENGTH)
            dock = _ViewDock(name, self)
            dock.setWidget(plot)
            dock.closed.connect(lambda name=name: self._on_view_closed(name))
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            dock.hide()
            self._views[name] = dock
        return self._views[name]

    def _on_view_closed(self, name: str) -> None:
        """The user closed the view: uncheck its action without firing it."""
        action = self.get_action(f'{name}_show_graph')
        action.blockSignals(True)
        action.setChecked(False)
        action.blockSignals(False)

    # ── Device ───────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Open the device on its hardware thread. The status line reports the result."""
        QMetaObject.invokeMethod(self.controller.thread, 'ini_hardware', Qt.ConnectionType.QueuedConnection)

    def _set_device_open(self, opened: bool) -> None:
        if opened:
            self.initialize()
        else:
            for name in list(self._grabbing):  # unchecking the grab stops its poll
                self.get_action(f'{name}_grab').setChecked(False)
            QMetaObject.invokeMethod(self.controller.thread, 'close_hardware', Qt.ConnectionType.QueuedConnection)

    def _set_grabbing(self, name: str, grabbing: bool) -> None:
        if grabbing:
            self._grabbing.add(name)
            self._start_grab(name)
        else:
            self._grabbing.discard(name)
            self.controller.stop_poll(name)
        self._refresh_led(name)

    def _start_grab(self, name: str) -> None:
        if self.controller.connected:  # a grab restarts when the device opens again
            self.controller.poll(name, self._grab_period_ms)

    def _write(self, name: str, value: object) -> None:
        if self._attached:  # a widget can still emit after the device is released
            self._pending.add(name)
            self._failed.discard(name)
            if self._settles(self._quantities[name]):
                self._targets[name] = value
            self._refresh_led(name)
            setattr(self.controller, name, value)

    def _read(self, name: str) -> None:
        if self._attached:
            self._reading.add(name)
            self._refresh_led(name)
            self.controller.read(name, lambda data: self._on_reading(name, data))

    def _run_action(self, name: str, action_name: str, checked: bool | None = None) -> None:
        """Call one of a channel's declared actions. Only queues the request - ``run_action`` is a
        queued cross-thread call, so nothing about the action having run, let alone succeeded, is known
        yet; see :meth:`_on_action_done` for the side effects that depend on that.

        *checked* is the button's new state for a ``checkable`` action, read off the button by the
        caller (see :meth:`_add_action_button`); ``None`` for a plain action."""
        if not self._attached:
            return
        self.controller.run_action(name, action_name, checked)

    def _on_action_done(self, name: str, action_name: str, result: object) -> None:
        """An action's callback ran without raising. ``stop`` also clears the settle watch and any
        pending/rejected state, since it interrupts a pending move; that side effect is specific to it,
        not to a custom action in general. Done here, once confirmed, rather than optimistically in
        _run_action on click: a failing stop goes through :meth:`_on_action_failed` instead and leaves
        the row's state untouched, rather than this showing a false "stopped" state that never actually
        happened.

        If the callback also reported a value (``result`` is not ``None`` - e.g. Stop freezing a
        target at the axis's current position), every widget showing this control updates to it, the
        same fan-out a confirmed write uses. Deliberately not routed through _on_written: an action is
        not a write (no settling of its own; the pending/failed bookkeeping above is specific to
        ``stop``, not a general consequence of reporting a value)."""
        if action_name == 'stop':
            self._stop_settle_watch(name)
            self._pending.discard(name)
            self._failed.discard(name)
            self._refresh_led(name)
        if result is not None:
            self._sync_for(name).value = result

    def _on_action_failed(self, name: str, action_name: str, message: str) -> None:
        """An action's callback raised - e.g. a real stop the hardware refused. Turns the row red, the
        same way a rejected write does, rather than the invisible, channel-less ``error`` this used to
        go through. Does not touch an in-progress settle watch or pending state: nothing about a move
        already underway changed because this action failed, so there is nothing to cancel."""
        self._failed.add(name)
        self._refresh_led(name)
        self.status_label.setText(f'error: {name}: {message}')

    def _led_state(self, row: str) -> str:
        """closed: device shut. rejected: last write or action failed. pending: write pending or
        settling. active: read or grab in progress. idle: none of the above."""
        names = self._row_channels.get(row, [row])
        if not self.controller.connected:
            return 'closed'
        if any(n in self._failed for n in names):
            return 'rejected'
        if any(n in self._pending for n in names):
            return 'pending'
        if any(n in self._reading or n in self._grabbing for n in names):
            return 'active'
        return 'idle'

    def _led_color(self, row: str) -> QColor:
        """The QColor for :meth:`_led_state`'s current state, for callers that want the colour
        directly rather than the state name (e.g. comparing against a theme colour in a test)."""
        return QColor(dict(_led_states())[self._led_state(row)])

    def _refresh_led(self, name: str) -> None:
        row = self._row_of.get(name, name)
        led = self._leds.get(row)
        if led is not None:
            led.set_state(self._led_state(row))

    # ── Settling: a control with a readback and an epsilon waits for the readback to reach the target ──

    @staticmethod
    def _settles(quantity: Quantity) -> bool:
        """Whether writing *quantity* should stay pending until its readback is within epsilon of the target.

        Without both a readback and a non-zero epsilon there is nothing to compare against, and the
        existing behaviour (clear as soon as the plugin's write call returns) is the best available.
        """
        return bool(quantity.readback) and quantity.epsilon > 0

    def _start_settle_watch(self, name: str) -> None:
        self._stop_settle_watch(name)  # a new write restarts the watch, so only the latest target matters
        self._settle_deadlines[name] = time.monotonic() + SETTLE_TIMEOUT_S
        timer = QTimer(self)
        timer.setInterval(int(SETTLE_POLL_MS))
        timer.timeout.connect(lambda name=name: self._check_settled(name))
        self._settle_timers[name] = timer
        timer.start()

    def _check_settled(self, name: str) -> None:
        if name not in self._settle_timers:
            return
        if time.monotonic() > self._settle_deadlines.get(name, 0.0):
            self._stop_settle_watch(name)
            self._pending.discard(name)
            self._failed.add(name)
            self._refresh_led(name)
            self.status_label.setText(f'error: {name}: did not settle within {SETTLE_TIMEOUT_S:.0f} s')
            return
        channel = self._quantities[name].readback
        self.controller.read(channel, lambda data, name=name: self._on_settle_reading(name, data))

    def _on_settle_reading(self, name: str, data: object) -> None:
        if name not in self._settle_timers:
            return  # a newer write, a stop, or a disconnect ended this watch; a late reply changes nothing
        target = self._targets.get(name)
        values = np.asarray(data).ravel()
        if target is None or values.size != 1:
            return
        if abs(float(values[0]) - target) <= self._quantities[name].epsilon:
            self._stop_settle_watch(name)
            self._pending.discard(name)
            self._failed.discard(name)
            self._refresh_led(name)

    def _stop_settle_watch(self, name: str) -> None:
        timer = self._settle_timers.pop(name, None)
        self._settle_deadlines.pop(name, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def release(self) -> None:
        """Detach from the registry. The device closes when the last module lets go of it."""
        if self._attached:
            self._attached = False
            for name in list(self._settle_timers):
                self._stop_settle_watch(name)
            self._registry.detach(self._key)

    def closeEvent(self, event):
        self.release()
        super().closeEvent(event)

    # ── Signals from the controller ──────────────────────────────────────────

    @Slot(bool, str)
    def _on_status(self, connected: bool, info: str) -> None:
        state = 'open' if connected else 'closed'
        self.status_label.setText(f'{state}: {info}')
        if not connected:  # a settle watch reads the device, which closed from under it
            for name in list(self._settle_timers):
                self._stop_settle_watch(name)
        for name in self._leds:
            self._refresh_led(name)
        ini = self.get_action('ini')
        ini.blockSignals(True)
        ini.setChecked(connected)
        ini.blockSignals(False)
        ini.set_icon(ActionIconNames.INI, _colors().green if connected else _colors().red)
        if connected:
            for name in self._grabbing:
                self._start_grab(name)

    def _on_reading(self, name: str, data: object) -> None:
        self._reading.discard(name)
        self._refresh_led(name)
        if name in self._displays:
            self._displays[name].setText(self._display_text(name, data))
        if name not in self._curves:
            return
        values = np.asarray(data)
        if not np.issubdtype(values.dtype, np.number):
            return  # a label such as a discrete state has no trace
        if values.size == 1:  # a scalar: plot its history
            self._history[name].append(float(values.ravel()[0]))
            self._curves[name].setData(list(self._history[name]))
        else:
            self._curves[name].setData(values.ravel())

    def _display_text(self, name: str, data: object) -> str:
        text = _format(data)
        units = self._quantities[name].units
        return f'{text} {units}' if units and np.asarray(data).size == 1 else text

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f'error: {message}')

    def _on_write_failed(self, name: str, message: str) -> None:
        self._stop_settle_watch(name)  # a rejected write has nothing left to settle towards
        self._pending.discard(name)
        self._failed.add(name)
        self._refresh_led(name)
        self.status_label.setText(f'error: {name}: {message}')

    def _on_written(self, name: str, value: object) -> None:
        if self._settles(self._quantities[name]):
            self._start_settle_watch(name)  # stays pending (orange) until the readback reaches the target
        else:
            self._pending.discard(name)
            self._failed.discard(name)
            self._refresh_led(name)
        # Every widget bound to this quantity's sync - value widget, slider, a merged control's
        # action, any number of them - updates to the confirmed value, without writing it back.
        self._sync_for(name).value = value

    def _sync_for(self, name: str) -> ValueSync:
        """The :class:`ValueSync` every widget showing *name* is bound to (FROM_SYNC), created on
        first use. Setting its ``.value`` fans out to all of them; see pymodaq_gui.utils.widget_sync."""
        if name not in self._syncs:
            self._syncs[name] = ValueSync()
        return self._syncs[name]
