"""GUI side of one device: a widget built from the device's capabilities.

A :class:`HardwareModule` attaches to the registry for its device and drives the returned
:class:`~pymodaq.control_modules.controller.Controller`. It never touches the plugin or the
hardware thread directly. Each declared quantity becomes one row, and the widgets of a row come
from :func:`~pymodaq.control_modules.capabilities.toolbar_widgets`.

Every measurement shows its last value. Only the widgets in :data:`WIDGET_BUILDERS` are built;
other names from the defaults are skipped until their builder exists.
"""
from __future__ import annotations

import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import QMetaObject, Qt

from pymodaq.control_modules.capabilities import Access, Quantity, toolbar_widgets
from pymodaq.control_modules.controller import Controller
from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry

__all__ = ['HardwareModule', 'WIDGET_BUILDERS']


def _format(data) -> str:
    values = np.asarray(data)
    if values.size == 1:
        return f'{values.ravel()[0]:.4g}'
    return np.array2string(values, precision=3, threshold=10)


def _value_spinbox(module: HardwareModule, quantity: Quantity) -> QtWidgets.QWidget:
    spin = QtWidgets.QDoubleSpinBox()
    spin.setRange(-1e12 if quantity.lo is None else quantity.lo, 1e12 if quantity.hi is None else quantity.hi)
    spin.setSuffix(f' {quantity.units}' if quantity.units else '')
    spin.editingFinished.connect(lambda: setattr(module.controller, quantity.name, spin.value()))
    module._value_widgets[quantity.name] = spin
    return spin


def _selector(module: HardwareModule, quantity: Quantity) -> QtWidgets.QWidget:
    combo = QtWidgets.QComboBox()
    combo.addItems([str(v) for v in quantity.values])
    combo.activated.connect(lambda index: setattr(module.controller, quantity.name, quantity.values[index]))
    module._value_widgets[quantity.name] = combo
    return combo


def _read(module: HardwareModule, quantity: Quantity) -> QtWidgets.QWidget:
    button = QtWidgets.QPushButton('Read')

    def on_click():
        module.controller.read(quantity.name, lambda data: module._displays[quantity.name].setText(_format(data)))

    button.clicked.connect(on_click)
    return button


WIDGET_BUILDERS = {
    'value': _value_spinbox,
    'selector': _selector,
    'read': _read,
}


class HardwareModule(QtWidgets.QWidget):
    """One device: a status line, then one row per quantity.

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
        super().__init__(parent)
        self._registry = registry if registry is not None else HardwareRegistry.get()
        self._key = key
        self._attached = True
        self._value_widgets: dict[str, QtWidgets.QWidget] = {}
        self._displays: dict[str, QtWidgets.QLabel] = {}
        self._quantities: dict[str, Quantity] = {}
        self.controller: Controller = self._registry.attach(key, plugin_class, params_state)

        self.status_label = QtWidgets.QLabel('not open')
        self.init_button = QtWidgets.QPushButton('Ini.')
        self.init_button.clicked.connect(self.initialize)
        rows = QtWidgets.QVBoxLayout(self)
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(self.init_button)
        toolbar.addWidget(self.status_label)
        rows.addLayout(toolbar)

        caps = self.controller.capabilities
        for quantity in caps.measurements + caps.controls:
            rows.addLayout(self._row(quantity))

        self.controller.device_status.connect(self._on_status)
        self.controller.device_error.connect(self._on_error)
        self.controller.written.connect(self._on_written)

    def _row(self, quantity: Quantity) -> QtWidgets.QHBoxLayout:
        self._quantities[quantity.name] = quantity
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(quantity.name))
        if quantity.access is Access.MEASUREMENT:
            # Every measurement shows its last value; 'read' and polls update it.
            display = QtWidgets.QLabel('-')
            self._displays[quantity.name] = display
            row.addWidget(display)
        for widget_name in toolbar_widgets(quantity):
            builder = WIDGET_BUILDERS.get(widget_name)
            if builder is not None:
                row.addWidget(builder(self, quantity))
        return row

    def initialize(self) -> None:
        """Open the device on its hardware thread. The status line reports the result."""
        QMetaObject.invokeMethod(self.controller.thread, 'ini_hardware', Qt.ConnectionType.QueuedConnection)

    def release(self) -> None:
        """Detach from the registry. The device closes when the last module lets go of it."""
        if self._attached:
            self._attached = False
            self._registry.detach(self._key)

    def closeEvent(self, event):
        self.release()
        super().closeEvent(event)

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
