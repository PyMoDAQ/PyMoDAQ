"""Try HardwareModule with the simplest possible device. Run from packages/pymodaq:

    python examples/hardware_module_minimal_example.py

Start here. One control, one measurement, nothing else - no settings, no get/set shortcuts, no
readback, no slider, no actions. The next two examples build on this one, feature by feature:
1. hardware_module_minimal_example.py (this one): a control and a measurement, read()/write() only.
2. hardware_module_example.py (spectrometer): adds get/set shortcuts and a plugin setting.
3. hardware_module_stage_example.py (stage): adds a readback, settling, Stop, Enable, Home.

What to try:
- Ini. opens the device; the status line shows "open".
- Type a target and press Enter. The device gets it at once.
- Read reads the temperature once; Grab polls it continuously; Show Graph plots it live.
- The temperature drifts towards the target over a few seconds - watch it with Grab or Show Graph.

target and temperature both go through write()/read(), the plugin's two simplest methods: no get/set
shortcut, no readback link (temperature is a plain measurement here, not tied to target by a
declaration - it just happens to drift towards it, in the plugin's own _advance()), no settings.
"""
import sys
import time

import numpy as np

from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.shared_ui import SharedUI

from pymodaq.control_modules.hardware.capabilities import control, measurement
from pymodaq.control_modules.hardware_module import HardwareModule
from pymodaq.control_modules.hardware.hardware_registry import HardwareKey


class _Reading:
    """Stands in for DataToExport: one array per requested channel."""

    def __init__(self, arrays):
        self._arrays = arrays

    def get_data_from_name(self, name):
        return self._arrays[name]


class FakeHeater:
    """A single control and a single measurement: the smallest useful plugin.

    ``target`` is a control: the GUI writes to it, the plugin applies it in ``write()``.
    ``temperature`` is a measurement: the GUI reads it, the plugin answers in ``read()``. The two
    are not linked by a declaration (no ``readback=``, see the stage example for that) - the
    temperature just happens to drift towards the target, in this plugin's own ``_advance()``, the
    same idea the stage example uses for three axes at once.
    """

    target = control(units='C', lo=0, hi=100, label='Target')
    temperature = measurement(units='C', label='Temperature')

    def __init__(self):
        self._target = 20.0
        self._temperature = 20.0
        self._last_update = time.monotonic()

    def open(self, settings):
        self._last_update = time.monotonic()

    def close(self):
        pass

    def _advance(self) -> None:
        """Drift the temperature a third of the way to the target for every second elapsed."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now
        self._temperature += (self._target - self._temperature) * min(1.0, elapsed / 3)

    def read(self, names=None, fresh=True):
        self._advance()
        return _Reading({'temperature': np.array([self._temperature])})

    def write(self, name, value):
        self._target = float(value)


def main() -> int:
    app = mkQApp('HardwareModule minimal example')  # applies the PyMoDAQ theme and style
    key = HardwareKey(hardware_class=FakeHeater, controller_id=0)
    module = HardwareModule(key, FakeHeater)
    module.resize(900, 400)
    shared_ui = SharedUI(module)  # adds Help, Preferences and a Toolbars visibility menu, as the
    shared_ui.affect_application(module)  # other standalone modules (daq_move.py, daq_viewer.py) do
    shared_ui.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
