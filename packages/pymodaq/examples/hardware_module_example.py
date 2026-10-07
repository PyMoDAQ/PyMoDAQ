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
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.shared_ui import SharedUI

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

    spectrum = measurement(units='counts', shape=(256,), label='Spectrum', docs='Replaced on each read')
    temperature = measurement(units='K', label='Sensor temperature', docs='Sensor temperature')
    status = measurement(values=['idle', 'running'], label='Device state', docs='Device state')
    exposure = control(units='ms', lo=1, hi=1000, epsilon=0.1, label='Exposure', docs='Exposure time')
    trigger = control(values=['internal', 'external'], label='Trigger source', docs='Trigger source')

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
    app = mkQApp('HardwareModule example')  # applies the PyMoDAQ theme and style, as the other modules do
    key = HardwareKey(hardware_class=FakeSpectrometer, controller_id=0)
    module = HardwareModule(key, FakeSpectrometer)
    module.resize(1100, 600)
    shared_ui = SharedUI(module)  # adds Help, Preferences and a Toolbars visibility menu, as the
    shared_ui.affect_application(module)  # other standalone modules (daq_move.py, daq_viewer.py) do
    shared_ui.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
