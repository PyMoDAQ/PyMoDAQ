"""Try HardwareModule with a fake spectrometer. Run from any directory:

    python hardware_module_example.py

Step 2 of 3: builds on hardware_module_minimal_example.py (a bare control and measurement) by adding
get= shortcuts, a post_set hook and a plugin setting. hardware_module_stage_example.py is step 3,
adding a readback, settling, Stop, Enable and Home.

What to try:
- Ini. (instrument toolbar) opens the fake device; the status line shows "open".
- exposure: type a value and press Enter. The device gets it, and Read/Snap/its own readback row all
  show it back too.
- trigger: pick a value. The device gets it, and Read shows it back too.
- spectrum: Snap reads the spectrum once; Show Graph opens a live view that polls it.
- temperature: Read, or Show Graph for a live trace of the last 200 values.
- status: read-only, shows the device state, which changes while the device is open.
- Settings (instrument toolbar): a plugin parameter, "averaging", not declared as a channel. Changing
  it reaches the plugin's commit_settings and reduces the spectrum's noise.
- Set exposure above 500 ms: the plugin turns averaging off by itself, and the settings dock follows,
  without the GUI having written anything.

temperature and status answer their read with ``get='_read_method_name'`` - a plugin method, called
with no arguments, for a value that's genuinely computed each time. trigger and exposure both answer
theirs with ``get=True`` instead - reading back whatever the last write stored, which happens
automatically now for every control, no plugin code needed (see FakeSpectrometer's docstring).
exposure also keeps a side effect (clamping averaging above 500 ms), as ``post_set='_clamp_averaging'``
- the plugin method ``post_set`` calls instead of a hand-written ``write()`` - the "more automatic way
to access a Controller attribute [...] or method call" Seb5g's review of PR #1289 asked for.
exposure's ``readback=True`` is answered by that same ``get=True``, for free: a control with no
settling lag has nothing separate for a readback to report. spectrum alone keeps a real read(): it's
the channel that would share a batched read with others like it on a real instrument, so there's no
single attribute or method call to point a shortcut at.
"""
import sys
import time

import numpy as np
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.shared_ui import SharedUI

from pymodaq.control_modules.hardware.capabilities import control, measurement
from pymodaq.control_modules.hardware_module import HardwareModule
from pymodaq.control_modules.hardware.hardware_registry import HardwareKey, HardwareRegistry


class _Reading:
    """Stands in for DataToExport: one array per requested channel."""

    def __init__(self, arrays):
        self._arrays = arrays

    def get_data_from_name(self, name):
        return self._arrays[name]


class FakeSpectrometer:
    """A plugin with the new-style API: declarations, open/close and read.

    ``averaging`` is a plain plugin setting, not a declared channel: it only affects how the
    spectrum is computed, through ``commit_settings``. It also shows the other direction: the
    plugin turns it off by itself for a long exposure, and the settings dock follows without a
    write from the GUI.

    ``temperature`` and ``status`` answer their own read with ``get='_read_temperature'``/
    ``get='_read_status'`` - sugar for ``lambda plugin: plugin._read_temperature()`` etc.: a Grab of
    ``temperature`` never calls ``read()`` at all, it calls ``_read_temperature()`` directly.

    ``trigger`` and ``exposure`` both answer their read with ``get=True`` instead - reading back
    whatever the quantity's own attribute already holds. What's new is that the attribute no longer
    needs the plugin to maintain it by hand: every control's write is stored as ``plugin.<name>``
    automatically, by the device thread, once it succeeds (see ``HardwareThread.request_write``).
    ``trigger`` has nothing else to say, so that's its entire write path - no setter, no ``write()``
    branch. ``exposure`` still has a side effect (turning ``averaging`` off above 500 ms), so it adds
    ``post_set='_clamp_averaging'`` for just that - sugar for ``lambda plugin, value:
    plugin._clamp_averaging(value)``, called after the value is already stored, so the method could
    read ``self.exposure`` back if it needed to. Neither needs a ``write()`` branch any more, and the
    plugin defines no ``write()`` at all - nothing is left that would call it. ``exposure`` also
    declares ``readback=True``: since its own ``get=True`` already answers "what is the device doing
    right now" exactly (no settling lag to report separately), the auto-created readback measurement
    defaults to that same answer - no extra code for it either.

    ``spectrum`` alone keeps a real ``read()``: it's the channel that would share a batched read
    with others like it on a real multi-channel instrument, so there's no single attribute or method
    call to answer it from.
    """

    params: list = [
        {'name': 'averaging', 'type': 'int', 'value': 8, 'limits': (1, 1000),
         'tip': 'Number of reads averaged into the spectrum; turned off above 500 ms exposure'},
    ]

    spectrum = measurement(units='counts', shape=(256,), label='Spectrum', docs='Replaced on each read')
    temperature = measurement(units='K', label='Sensor temperature', docs='Sensor temperature',
                              get='_read_temperature')
    status = measurement(values=['idle', 'running'], label='Device state', docs='Device state',
                         get='_read_status')
    exposure = control(units='ms', lo=1, hi=1000, epsilon=0.1, label='Exposure', docs='Exposure time',
                      get=True, readback=True, post_set='_clamp_averaging')
    trigger = control(values=['internal', 'external'], label='Trigger source', docs='Trigger source',
                      get=True)

    def __init__(self):
        self.exposure = 10.0  # a plain default; __init__ may still set one, it just isn't required to
        self.trigger = 'internal'
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
                shape = np.sin(x + self._elapsed()) + 1.5  # ranges 0.5 .. 2.5, exposure-independent
                signal = shape * self.exposure / 10
                # Real averaging: the shape stays put, only the noise shrinks, by 1 / sqrt(N).
                noise_std = (1.5 / 10) / np.sqrt(max(self._averaging, 1))
                arrays[name] = signal + np.random.normal(0, noise_std, size=256)
        return _Reading(arrays)

    def _read_temperature(self):
        return np.array([293.1 + 0.5 * np.sin(self._elapsed())])

    def _read_status(self):
        return np.array(['running' if np.sin(self._elapsed()) > 0 else 'idle'])

    def _clamp_averaging(self, value):
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
