"""Try HardwareModule with a fake spectrometer. Run from any directory:

    python hardware_module_example.py

What to try:
- Ini. (instrument toolbar) opens the fake device; the status line shows "open".
- exposure: type a value and press Enter. The device gets it and the spinbox follows the device.
- trigger: pick a value. The device gets it.
- spectrum: Snap reads the spectrum once; Show Graph opens a live view that polls it.
- temperature: Read, or Show Graph for a live trace of the last 200 values.
- status: read-only, shows the device state, which changes while the device is open.
- Settings (instrument toolbar): a plugin parameter, "averaging", not declared as a channel. Changing
  it reaches the plugin's commit_settings and reduces the spectrum's noise.
- Set exposure above 500 ms: the plugin turns averaging off by itself, and the settings dock follows,
  without the GUI having written anything.

temperature, status and trigger declare get/set directly and never go through read()/write(): see
FakeSpectrometer's docstring. spectrum and exposure still do, since spectrum is the channel that
would share a batched read with others like it on a real instrument.
"""
import sys
import time

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
    """A plugin with the new-style API: declarations, open/close, read and write.

    ``averaging`` is a plain plugin setting, not a declared channel: it only affects how the
    spectrum is computed, through ``commit_settings``. It also shows the other direction: the
    plugin turns it off by itself for a long exposure, and the settings dock follows without a
    write from the GUI.

    ``temperature``, ``status`` and ``trigger`` each answer their own read or write with a
    ``get``/``set`` callback: a Grab of ``temperature`` never calls ``read()`` at all. ``spectrum``
    and ``exposure`` stay in ``read()``/``write()``, since ``spectrum`` is the channel that would
    share a batched ``read()`` call with others like it on a real multi-channel instrument.
    """

    params: list = [
        {'name': 'averaging', 'type': 'int', 'value': 8, 'limits': (1, 1000),
         'tip': 'Number of reads averaged into the spectrum; turned off above 500 ms exposure'},
    ]

    spectrum = measurement(units='counts', shape=(256,), label='Spectrum', docs='Replaced on each read')
    temperature = measurement(units='K', label='Sensor temperature', docs='Sensor temperature',
                              get=lambda plugin: plugin._read_temperature())
    status = measurement(values=['idle', 'running'], label='Device state', docs='Device state',
                         get=lambda plugin: plugin._read_status())
    exposure = control(units='ms', lo=1, hi=1000, epsilon=0.1, label='Exposure', docs='Exposure time')
    trigger = control(values=['internal', 'external'], label='Trigger source', docs='Trigger source',
                      set=lambda plugin, value: plugin._set_trigger(value))

    def __init__(self):
        self._exposure = 10.0
        self._trigger = 'internal'
        self._averaging = 8
        self._start = time.monotonic()
        self._settings = None

    def _elapsed(self) -> float:
        """Wall-clock phase: each channel's own read advances it by however long it has been open,

        instead of by how many times it has been read, so temperature and status drift at the
        same rate whether or not spectrum is also being grabbed.
        """
        return time.monotonic() - self._start

    def open(self, settings):
        self._settings = settings

    def close(self):
        pass

    def read(self, names=None, fresh=True):
        arrays = {}
        for name in names:
            if name == 'spectrum':
                x = np.linspace(0, 4 * np.pi, 256)
                signal = (np.sin(x + self._elapsed()) + 1.5) * self._exposure
                noise = np.random.rand(256) / max(self._averaging, 1)
                arrays[name] = signal * noise / 10
        return _Reading(arrays)

    def _read_temperature(self):
        return np.array([293.1 + 0.5 * np.sin(self._elapsed())])

    def _read_status(self):
        return np.array(['running' if np.sin(self._elapsed()) > 0 else 'idle'])

    def _set_trigger(self, value):
        self._trigger = value

    def write(self, name, value):
        if name == 'exposure':
            self._exposure = value
            if value > 500 and self._averaging != 1:
                # the plugin's own decision, not a GUI write: update both, since setValue alone
                # does not call commit_settings, and the settings dock must still follow it
                self._averaging = 1
                self._settings.child('averaging').setValue(1)

    def commit_settings(self, param):
        if param.name() == 'averaging':
            self._averaging = param.value()


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
