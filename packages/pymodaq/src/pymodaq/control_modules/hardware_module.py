"""GUI side of one device: a window with an instrument toolbar and one toolbar per quantity.

A :class:`HardwareModule` attaches to the registry for its device and drives the returned
:class:`~pymodaq.control_modules.controller.Controller`. It never touches the plugin or the
hardware thread directly.

Layout: the instrument toolbar sits on top, and a channel dock on the left holds one
``QToolBar`` per declared quantity. The widgets of each toolbar come from
:func:`~pymodaq.control_modules.capabilities.toolbar_widgets`. Views (plots) will be docks of
this window.

Only the widgets handled in :meth:`HardwareModule._fill_channel_toolbar` are built; other default
names are skipped until they are implemented.
"""
from __future__ import annotations

import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import QMetaObject, Qt

from pymodaq_gui.managers.action_manager import ActionManager

from pymodaq.control_modules.capabilities import Access, Quantity, toolbar_widgets
from pymodaq.control_modules.controller import Controller
from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry

__all__ = ['HardwareModule']

INSTRUMENT_TOOLBAR = 'instrument'


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
    """

    def __init__(self, key: HardwareKey, plugin_class: type, params_state: dict | None = None,
                 registry: HardwareRegistry | None = None, parent: QtWidgets.QWidget | None = None):
        QtWidgets.QMainWindow.__init__(self, parent)
        ActionManager.__init__(self)
        self._registry = registry if registry is not None else HardwareRegistry.get()
        self._key = key
        self._attached = True
        self._quantities: dict[str, Quantity] = {}
        self._value_widgets: dict[str, QtWidgets.QWidget] = {}
        self._displays: dict[str, QtWidgets.QLabel] = {}
        self.controller: Controller = self._registry.attach(key, plugin_class, params_state)
        self.setWindowTitle(plugin_class.__name__)
        self.setCentralWidget(QtWidgets.QWidget())  # the area the views will fill

        self.status_label = QtWidgets.QLabel('not open')
        self.setup_actions()
        self._build_channels(self.controller.capabilities)

        self.controller.device_status.connect(self._on_status)
        self.controller.device_error.connect(self._on_error)
        self.controller.written.connect(self._on_written)

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
