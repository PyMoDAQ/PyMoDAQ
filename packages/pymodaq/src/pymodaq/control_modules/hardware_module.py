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

from collections import deque

import numpy as np
import pyqtgraph as pg
from pyqtgraph.parametertree import ParameterTree
from qt_themes import get_theme
from qtpy import QtWidgets
from qtpy.QtCore import QMetaObject, Qt, Signal, Slot
from qtpy import QtGui
from qtpy.QtGui import QColor

from pymodaq_gui.managers.action_manager import ActionManager

from pymodaq.control_modules.capabilities import Access, Quantity, toolbar_widgets
from pymodaq.control_modules.controller import Controller
from pymodaq.control_modules.enums import ActionIconNames
from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry

__all__ = ['HardwareModule']

INSTRUMENT_TOOLBAR = 'instrument'
HISTORY_LENGTH = 200  # points kept by the trace of a scalar measurement
DISPLAY_WIDTH = 150  # fixed columns: every row's actions start at the same position
VALUE_WIDTH = 130
ACTION_WIDTH = 44  # room for one toolbar button


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


def _caption(quantity: Quantity) -> str:
    """The text shown for a channel: its label in capitals, or its name made readable."""
    text = quantity.label or quantity.name.replace('_', ' ').capitalize()
    return text.upper()


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
        self._displays: dict[str, QtWidgets.QLabel] = {}
        self._views: dict[str, _ViewDock] = {}
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._history: dict[str, deque] = {}
        self._leds: dict[str, QtWidgets.QLabel] = {}
        self._pending: set[str] = set()  # writes sent, not yet acknowledged
        self._failed: set[str] = set()  # writes the plugin rejected
        self._reading: set[str] = set()  # one-shot reads in flight
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
        self.controller.new_reading.connect(self._on_reading)
        for name in self._quantities:
            self._refresh_led(name)

    # ── Layout ───────────────────────────────────────────────────────────────

    def setup_actions(self) -> None:
        """The instrument toolbar: open or close the device, show its status, show its settings."""
        theme = _colors()
        self.add_toolbar(INSTRUMENT_TOOLBAR, 'Instrument', parent=self)
        self.add_action('ini', 'Ini.', ActionIconNames.INI, 'Open the device (uncheck to close it)',
                        checkable=True, icon_color=theme.red, icon_checked_color=theme.green,
                        toolbar=INSTRUMENT_TOOLBAR)
        self.connect_action('ini', lambda *_: self._set_device_open(self.get_action('ini').isChecked()))
        self.add_action('show_settings', 'Settings', 'settings', 'Show or hide the device settings',
                        checkable=True, icon_checked_color=theme.green, toolbar=INSTRUMENT_TOOLBAR)
        self.connect_action('show_settings', lambda *_: self.settings_dock.setVisible(
            self.get_action('show_settings').isChecked()))
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
        if not self._attached or self.controller.thread is None:
            return
        for param, change, data in changes:
            path = self.controller.settings.childPath(param)
            if path is not None:
                self._settings_update.emit(path, data, change)

    def _build_channels(self, caps) -> None:
        """One toolbar per quantity, stacked in a dock on the left."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setSpacing(8)
        quantities = caps.measurements + caps.controls
        bold = QtWidgets.QLabel().font()
        bold.setBold(True)
        self._name_width = max((QtGui.QFontMetrics(bold).horizontalAdvance(_caption(q)) for q in quantities),
                               default=0) + 16
        # a whole row fits without the toolbar's overflow arrow: name, display, value, four buttons, separators
        container.setMinimumWidth(self._name_width + DISPLAY_WIDTH + VALUE_WIDTH + 4 * ACTION_WIDTH + 60)
        for quantity in quantities:
            self._quantities[quantity.name] = quantity
            bar = QtWidgets.QToolBar(quantity.name, container)
            self.reference_toolbar(quantity.name, bar)
            layout.addWidget(bar)
            self._fill_channel_toolbar(quantity)
        layout.addStretch()
        self.channels_dock = QtWidgets.QDockWidget('Channels', self)
        self.channels_dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.channels_dock)

    @staticmethod
    def _access_color(quantity: Quantity) -> str:
        """Measurements are blue and controls magenta, so the two kinds can be told apart at a glance."""
        colors = _colors()
        color = colors.blue if quantity.access is Access.MEASUREMENT else colors.magenta
        return QColor(color).name()  # a hex string, which a style sheet accepts

    def _fill_channel_toolbar(self, quantity: Quantity) -> None:
        """Name, display, value, actions, show graph: each row has the same slots, so the actions line up."""
        name = quantity.name
        is_measurement = quantity.access is Access.MEASUREMENT
        led = QtWidgets.QLabel()  # the channel status: see _led_color
        led.setFixedSize(12, 12)
        self._leds[name] = led
        self.add_widget(f'{name}_led', led, toolbar=name)
        label = QtWidgets.QLabel(_caption(quantity))  # the label shown; the name stays the identifier
        label.setStyleSheet(f'color: {self._access_color(quantity)}; font-weight: bold; letter-spacing: 1px;')
        label.setFixedWidth(self._name_width)
        kind = 'measurement: read from the device' if is_measurement else 'control: set on the device'
        label.setToolTip(f'{name} ({kind})')
        self.add_widget(f'{name}_name', label, toolbar=name)

        widgets = toolbar_widgets(quantity)
        bar = self.get_toolbar(name)
        bar.addSeparator()
        if is_measurement:
            self._add_display(quantity)
        else:
            self._add_placeholder(name, 'display', DISPLAY_WIDTH)
        bar.addSeparator()
        if 'value' in widgets:
            self._add_value_spinbox(quantity)
        elif 'selector' in widgets:
            self._add_selector(quantity)
        else:
            self._add_placeholder(name, 'value', VALUE_WIDTH)
        bar.addSeparator()
        self._actions_of(quantity, widgets)()
        if 'show_graph' in widgets:
            bar.addSeparator()
            self._add_show_graph_action(name)

    def _add_placeholder(self, name: str, slot: str, width: int) -> None:
        """An empty column, so that a row without this slot keeps the others aligned."""
        spacer = QtWidgets.QWidget()
        spacer.setFixedWidth(width)
        self.add_widget(f'{name}_{slot}_slot', spacer, toolbar=name)

    def _actions_of(self, quantity: Quantity, widgets: list[str]):
        """A function adding the read, snap and grab actions that the quantity's widgets ask for."""
        name = quantity.name

        def add():
            if 'read' in widgets or 'label' in widgets:
                self._add_read_action(name, 'Read', ActionIconNames.SNAP)
            if 'snap' in widgets:
                self._add_read_action(name, 'Snap', ActionIconNames.SNAP)
            if 'grab' in widgets:
                self._add_grab_action(name)
        return add

    def _add_display(self, quantity: Quantity) -> None:
        display = QtWidgets.QLabel('-')
        display.setFixedWidth(DISPLAY_WIDTH)
        display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._displays[quantity.name] = display
        self.add_widget(f'{quantity.name}_display', display, toolbar=quantity.name)

    def _add_read_action(self, name: str, text: str, icon: str) -> None:
        self.add_action(f'{name}_read', text, icon, f'{text} the value once', toolbar=name)
        self.connect_action(f'{name}_read', lambda *_, name=name: self._read(name))

    def _add_grab_action(self, name: str) -> None:
        theme = _colors()
        self.add_action(f'{name}_grab', 'Grab', ActionIconNames.GRAB, 'Follow the value continuously',
                        checkable=True, icon_checked=ActionIconNames.GRAB_STOP,
                        icon_checked_color=theme.green, toolbar=name)
        self.connect_action(f'{name}_grab', lambda *_, name=name: self._set_grabbing(
            name, self.get_action(f'{name}_grab').isChecked()))

    def _add_show_graph_action(self, name: str) -> None:
        self.add_action(f'{name}_show_graph', 'Show Graph', 'bid_landscape', 'Show or hide the graph',
                        checkable=True, icon_checked='bid_landscape', icon_checked_color=_colors().green,
                        toolbar=name)
        self.connect_action(f'{name}_show_graph', lambda *_, name=name: self._view(name).setVisible(
            self.get_action(f'{name}_show_graph').isChecked()))

    def _add_value_spinbox(self, quantity: Quantity) -> None:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e12 if quantity.lo is None else quantity.lo, 1e12 if quantity.hi is None else quantity.hi)
        spin.setSuffix(f' {quantity.units}' if quantity.units else '')
        spin.setFixedWidth(VALUE_WIDTH)
        spin.editingFinished.connect(lambda: self._write(quantity.name, spin.value()))
        self._value_widgets[quantity.name] = spin
        self.add_widget(f'{quantity.name}_value', spin, toolbar=quantity.name)

    def _add_selector(self, quantity: Quantity) -> None:
        combo = QtWidgets.QComboBox()
        combo.addItems([str(v) for v in quantity.values])
        combo.setFixedWidth(VALUE_WIDTH)
        combo.activated.connect(lambda index: self._write(quantity.name, quantity.values[index]))
        self._value_widgets[quantity.name] = combo
        self.add_widget(f'{quantity.name}_selector', combo, toolbar=quantity.name)

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
            self._refresh_led(name)
            setattr(self.controller, name, value)

    def _read(self, name: str) -> None:
        if self._attached:
            self._reading.add(name)
            self._refresh_led(name)
            self.controller.read(name, lambda data: self._on_reading(name, data))

    def _led_color(self, name: str) -> QColor:
        """Grey: device closed. Red: last write failed. Orange: write pending. Blue: read or grab active. Green: idle."""
        colors = _colors()
        if not self.controller.connected:
            return QColor('#9e9e9e')
        if name in self._failed:
            return QColor(colors.red)
        if name in self._pending:
            return QColor(colors.orange)
        if name in self._reading or name in self._grabbing:
            return QColor(colors.blue)
        return QColor(colors.green)

    def _refresh_led(self, name: str) -> None:
        led = self._leds.get(name)
        if led is not None:
            led.setStyleSheet(f'background-color: {self._led_color(name).name()}; border-radius: 6px; '
                              'border: 1px solid #616161;')

    def release(self) -> None:
        """Detach from the registry. The device closes when the last module lets go of it."""
        if self._attached:
            self._attached = False
            self._registry.detach(self._key)

    def closeEvent(self, event):
        self.release()
        super().closeEvent(event)

    # ── Signals from the controller ──────────────────────────────────────────

    @Slot(bool, str)
    def _on_status(self, connected: bool, info: str) -> None:
        state = 'open' if connected else 'closed'
        self.status_label.setText(f'{state}: {info}')
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
        self._pending.discard(name)
        self._failed.add(name)
        self._refresh_led(name)
        self.status_label.setText(f'error: {name}: {message}')

    def _on_written(self, name: str, value: object) -> None:
        self._pending.discard(name)
        self._failed.discard(name)
        self._refresh_led(name)
        widget = self._value_widgets.get(name)
        if widget is None:
            return
        # Block the widget's own signals so that showing a value does not write it back to the device.
        widget.blockSignals(True)
        try:
            if isinstance(widget, QtWidgets.QComboBox):
                widget.setCurrentIndex(self._quantities[name].values.index(value))
            else:
                widget.setValue(value)
        finally:
            widget.blockSignals(False)
