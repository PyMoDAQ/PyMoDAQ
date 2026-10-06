"""GUI side of one device: a window with an instrument toolbar and one toolbar per quantity.

A :class:`HardwareModule` attaches to the registry for its device and drives the returned
:class:`~pymodaq.control_modules.controller.Controller`. It never touches the plugin or the
hardware thread directly.

Layout: the instrument toolbar sits on top, and a channel dock on the left holds one
``QToolBar`` per declared quantity. The widgets of each toolbar come from
:func:`~pymodaq.control_modules.capabilities.toolbar_widgets`. A channel's ``show_graph`` action
opens a view dock on the right. The view polls its channel while it is open and stops when it closes.

Only the widgets handled in :meth:`HardwareModule._fill_channel_toolbar` are built; other default
names are skipped until they are implemented.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets
from qtpy.QtCore import QMetaObject, Qt, Signal

from pymodaq_gui.managers.action_manager import ActionManager

from pymodaq.control_modules.capabilities import Access, Quantity, toolbar_widgets
from pymodaq.control_modules.controller import Controller
from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry

__all__ = ['HardwareModule']

INSTRUMENT_TOOLBAR = 'instrument'
HISTORY_LENGTH = 200  # points kept by the trace of a scalar measurement


class _ViewDock(QtWidgets.QDockWidget):
    """A view dock that tells its owner when the user closes it."""

    closed = Signal()

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit()


def _format(data) -> str:
    values = np.asarray(data)
    if values.size == 1:
        return f'{values.ravel()[0]:.4g}'
    return np.array2string(values, precision=3, threshold=10)


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
    view_period_ms :
        Polling period of an open view.
    """

    def __init__(self, key: HardwareKey, plugin_class: type, params_state: dict | None = None,
                 registry: HardwareRegistry | None = None, parent: QtWidgets.QWidget | None = None,
                 view_period_ms: float = 200.0):
        QtWidgets.QMainWindow.__init__(self, parent)
        ActionManager.__init__(self)
        self._registry = registry if registry is not None else HardwareRegistry.get()
        self._key = key
        self._attached = True
        self._view_period_ms = view_period_ms
        self._quantities: dict[str, Quantity] = {}
        self._value_widgets: dict[str, QtWidgets.QWidget] = {}
        self._displays: dict[str, QtWidgets.QLabel] = {}
        self._views: dict[str, _ViewDock] = {}
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._history: dict[str, deque] = {}
        self.controller: Controller = self._registry.attach(key, plugin_class, params_state)
        self.setWindowTitle(plugin_class.__name__)
        self.setCentralWidget(QtWidgets.QWidget())  # the area the views will fill

        self.status_label = QtWidgets.QLabel('not open')
        self.setup_actions()
        self._build_channels(self.controller.capabilities)

        self.controller.device_status.connect(self._on_status)
        self.controller.device_error.connect(self._on_error)
        self.controller.written.connect(self._on_written)
        self.controller.new_reading.connect(self._on_reading)

    # ── Layout ───────────────────────────────────────────────────────────────

    def setup_actions(self) -> None:
        """The instrument toolbar: initialise the device and show its status."""
        self.add_toolbar(INSTRUMENT_TOOLBAR, 'Instrument', parent=self)
        self.add_action('ini', 'Ini.', 'Open', 'Open the device', toolbar=INSTRUMENT_TOOLBAR)
        self.connect_action('ini', lambda *_: self.initialize())
        self.add_widget('status', self.status_label, toolbar=INSTRUMENT_TOOLBAR)

    def _build_channels(self, caps) -> None:
        """One toolbar per quantity, stacked in a dock on the left."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        for quantity in caps.measurements + caps.controls:
            self._quantities[quantity.name] = quantity
            bar = QtWidgets.QToolBar(quantity.name, container)
            self.reference_toolbar(quantity.name, bar)
            layout.addWidget(bar)
            self._fill_channel_toolbar(quantity)
        layout.addStretch()
        self.channels_dock = QtWidgets.QDockWidget('Channels', self)
        self.channels_dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.channels_dock)

    def _fill_channel_toolbar(self, quantity: Quantity) -> None:
        name = quantity.name
        self.add_widget(f'{name}_name', QtWidgets.QLabel(name), toolbar=name)
        if quantity.access is Access.MEASUREMENT:
            display = QtWidgets.QLabel('-')
            self._displays[name] = display
            self.add_widget(f'{name}_display', display, toolbar=name)
        for widget_name in toolbar_widgets(quantity):
            if widget_name == 'value':
                self._add_value_spinbox(quantity)
            elif widget_name == 'selector':
                self._add_selector(quantity)
            elif widget_name == 'read':
                self.add_action(f'{name}_read', 'Read', 'repeat', 'Read the value once', toolbar=name)
                self.connect_action(f'{name}_read', lambda *_, name=name: self._read(name))
            elif widget_name == 'show_graph':
                self.add_action(f'{name}_show_graph', 'Show Graph', 'bid_landscape',
                                'Show or hide the graph of this channel', checkable=True, toolbar=name)
                self.connect_action(f'{name}_show_graph',
                                    lambda *_, name=name: self._set_view_shown(name, self._graph_checked(name)))

    def _graph_checked(self, name: str) -> bool:
        return self.get_action(f'{name}_show_graph').isChecked()

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

    def _set_view_shown(self, name: str, shown: bool) -> None:
        self._view(name).setVisible(shown)
        if shown:
            self._start_poll(name)
        else:
            self.controller.stop_poll(name)

    def _on_view_closed(self, name: str) -> None:
        """The user closed the view dock: uncheck its action and stop polling, without firing the action."""
        action = self.get_action(f'{name}_show_graph')
        action.blockSignals(True)
        action.setChecked(False)
        action.blockSignals(False)
        self.controller.stop_poll(name)

    def _start_poll(self, name: str) -> None:
        if self.controller.connected:  # polling needs an open device; reconnected devices restart it
            self.controller.poll(name, self._view_period_ms)

    def _add_value_spinbox(self, quantity: Quantity) -> None:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e12 if quantity.lo is None else quantity.lo, 1e12 if quantity.hi is None else quantity.hi)
        spin.setSuffix(f' {quantity.units}' if quantity.units else '')
        spin.editingFinished.connect(lambda: self._write(quantity.name, spin.value()))
        self._value_widgets[quantity.name] = spin
        self.add_widget(f'{quantity.name}_value', spin, toolbar=quantity.name)

    def _add_selector(self, quantity: Quantity) -> None:
        combo = QtWidgets.QComboBox()
        combo.addItems([str(v) for v in quantity.values])
        combo.activated.connect(lambda index: self._write(quantity.name, quantity.values[index]))
        self._value_widgets[quantity.name] = combo
        self.add_widget(f'{quantity.name}_selector', combo, toolbar=quantity.name)

    # ── Device ───────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Open the device on its hardware thread. The status line reports the result."""
        QMetaObject.invokeMethod(self.controller.thread, 'ini_hardware', Qt.ConnectionType.QueuedConnection)

    def _write(self, name: str, value: object) -> None:
        if self._attached:  # a widget can still emit after the device is released
            setattr(self.controller, name, value)

    def _read(self, name: str) -> None:
        if self._attached:
            self.controller.read(name, lambda data: self._displays[name].setText(_format(data)))

    def release(self) -> None:
        """Detach from the registry. The device closes when the last module lets go of it."""
        if self._attached:
            self._attached = False
            self._registry.detach(self._key)

    def closeEvent(self, event):
        self.release()
        super().closeEvent(event)

    # ── Signals from the controller ──────────────────────────────────────────

    def _on_status(self, connected: bool, info: str) -> None:
        state = 'open' if connected else 'closed'
        self.status_label.setText(f'{state}: {info}')
        if connected:
            for name, dock in self._views.items():
                if not dock.isHidden():
                    self._start_poll(name)

    def _on_reading(self, name: str, data: object) -> None:
        if name in self._displays:
            self._displays[name].setText(_format(data))
        if name not in self._curves:
            return
        values = np.asarray(data)
        if values.size == 1:  # a scalar: plot its history
            self._history[name].append(float(values.ravel()[0]))
            self._curves[name].setData(list(self._history[name]))
        else:
            self._curves[name].setData(values.ravel())

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f'error: {message}')

    def _on_written(self, name: str, value: object) -> None:
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
