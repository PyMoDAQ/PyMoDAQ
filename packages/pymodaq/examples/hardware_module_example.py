"""Try HardwareModule with a fake spectrometer. Run from any directory:

    python hardware_module_example.py

What to try:
- Ini. (instrument toolbar) opens the fake device; the status line shows "open".
- exposure: type a value and press Enter. The device gets it and the spinbox follows the device.
- trigger: pick a value. The device gets it.
- spectrum: Snap reads the spectrum once; Show Graph opens a live view that polls it.
- temperature: Read, or Show Graph for a live trace of the last 200 values.
- status: read-only, shows the device state, which changes while the device is open.
"""
import sys

import numpy as np
from qtpy import QtWidgets

from pymodaq.control_modules.capabilities import control, measurement
from pymodaq.control_modules.hardware_module import HardwareModule
from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry


class _Reading:
    """Stands in for DataToExport: one array per requested channel."""

    def __init__(self, arrays):
        self._arrays = arrays

    def get_data_from_name(self, name):
        return self._arrays[name]


class FakeSpectrometer:
    """A plugin with the new-style API: declarations, open/close, read and write."""

    params: list = []

    spectrum = measurement(units='counts', shape=(256,), docs='Spectrum, replaced on each read')
    temperature = measurement(units='K', docs='Sensor temperature')
    status = measurement(values=['idle', 'running'], docs='Device state')
    exposure = control(units='ms', lo=1, hi=1000, epsilon=0.1, docs='Exposure time')
    trigger = control(values=['internal', 'external'], docs='Trigger source')

    def __init__(self):
        self._exposure = 10.0
        self._trigger = 'internal'
        self._phase = 0.0

    def open(self, settings):
        pass

    def close(self):
        pass

    def read(self, names=None, fresh=True):
        self._phase += 0.1
        arrays = {}
        for name in names:
            if name == 'spectrum':
                x = np.linspace(0, 4 * np.pi, 256)
                arrays[name] = (np.sin(x + self._phase) + 1.5) * self._exposure * np.random.rand(256) / 10
            elif name == 'temperature':
                arrays[name] = np.array([293.1 + 0.5 * np.sin(self._phase)])
            elif name == 'status':
                arrays[name] = np.array(['running' if np.sin(self._phase) > 0 else 'idle'])
        return _Reading(arrays)

    def write(self, name, value):
        if name == 'exposure':
            self._exposure = value
        elif name == 'trigger':
            self._trigger = value


def main() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    key = HardwareKey(hardware_class=FakeSpectrometer, controller_id=0)
    module = HardwareModule(key, FakeSpectrometer)
    module.resize(900, 520)
    module.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
