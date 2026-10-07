"""Try HardwareModule with a fake three-axis stage. Run from packages/pymodaq:

    python examples/hardware_module_stage_example.py

Each axis is one row: a target (a control, with a spinbox and a slider) and its position (a
measurement, linked as the control's readback), like DAQ_Move. The position moves towards the target
at a fixed speed, and only while the device is read. So:
- Ini. opens the stage.
- Move a target with the slider or the spinbox. The device gets the new target at once, and the row's
  LED stays orange (settling) until the readback is within epsilon of it, not just until the device
  accepted the move.
- Stop an axis mid-move: the target freezes where the axis currently is, like a real motor's stop.
- Grab the position of an axis (Grab, blue LED). Its display follows the target with a delay.
- Motion shows "moving" while any axis is still on its way.
- Settings (instrument toolbar): "speed", a plugin parameter, not a channel - it's shared by every
  axis, so it belongs with the plugin's settings rather than any one row. Changing it reaches
  commit_settings and takes effect on the next move.

Each target (x, y, z) has its own set and stop callback, so writing or stopping one never goes through
write() at all: the plugin does not define it. The positions and motion stay in read(), since they all
depend on one shared _advance() step and would lose that if each had its own get.
"""
import sys
import time

import numpy as np

from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.shared_ui import SharedUI

from pymodaq.control_modules.capabilities import Capabilities, control, measurement
from pymodaq.control_modules.hardware_module import HardwareModule
from pymodaq.control_modules.hardware_registry import HardwareKey


class _Reading:
    def __init__(self, arrays):
        self._arrays = arrays

    def get_data_from_name(self, name):
        return self._arrays[name]


class FakeStage:
    """Three axes. Each target is a control whose readback, ``<axis>_readback``, is its position.

    Each target's ``set`` writes straight to ``_target``, and ``stop`` freezes it where the axis
    currently is, so the plugin needs no ``write()`` at all.

    ``speed`` is a plain plugin setting, not a channel: it is shared by every axis, so it belongs in
    the settings dock rather than in any one row, the same way ``averaging`` does in the spectrometer
    example. A setting that genuinely belonged to one axis alone (e.g. a per-axis acceleration) would
    still live here, just nested under a ``{'type': 'group', ...}`` named after the axis - the
    settings dock already renders that, no per-row widget needed.
    """

    params: list = [
        {'name': 'speed', 'type': 'float', 'value': 10.0, 'limits': (0.1, 100), 'suffix': 'mm/s',
         'tip': 'Speed shared by every axis'},
    ]

    x = control(units='mm', lo=0, hi=50, epsilon=0.01, label='X', ui_add=('slider',), readback=True,
               set=lambda plugin, value: plugin._set_target('x', value),
               stop=lambda plugin: plugin._stop_axis('x'))
    y = control(units='mm', lo=0, hi=50, epsilon=0.01, label='Y', ui_add=('slider',), readback=True,
               set=lambda plugin, value: plugin._set_target('y', value),
               stop=lambda plugin: plugin._stop_axis('y'))
    z = control(units='mm', lo=0, hi=10, epsilon=0.01, label='Z', ui_add=('slider',), readback="my_z_readback",
               set=lambda plugin, value: plugin._set_target('z', value),
               stop=lambda plugin: plugin._stop_axis('z'))
    motion = measurement(values=['idle', 'moving'], label='Motion')

    AXES = ('x', 'y', 'z')

    def __init__(self):
        self._target = {axis: 0.0 for axis in self.AXES}
        self._position = {axis: 0.0 for axis in self.AXES}
        self._last_update = time.monotonic()
        self._speed = 10.0  # mm/s, overwritten by open() from the declared default, then by commit_settings
        # the readback names come from the declarations, so any name works
        self._axis_of_readback = {c.readback: c.name for c in Capabilities.from_device(type(self)).controls
                                  if c.readback}

    def open(self, settings):
        self._last_update = time.monotonic()
        self._speed = settings.child('speed').value()

    def close(self):
        pass

    def commit_settings(self, param):
        if param.name() == 'speed':
            self._speed = param.value()

    def _advance(self) -> None:
        """Move every axis towards its target for the time elapsed since the last update."""
        now = time.monotonic()
        step = self._speed * (now - self._last_update)
        self._last_update = now
        for axis in self.AXES:
            error = self._target[axis] - self._position[axis]
            self._position[axis] += float(np.clip(error, -step, step))

    def _moving(self) -> bool:
        return any(abs(self._target[a] - self._position[a]) > 1e-6 for a in self.AXES)

    def read(self, names=None, fresh=True):
        self._advance()
        arrays = {}
        for name in names:
            if name in self._axis_of_readback:
                arrays[name] = np.array([self._position[self._axis_of_readback[name]]])
            elif name == 'motion':
                arrays[name] = np.array(['moving' if self._moving() else 'idle'])
        return _Reading(arrays)

    def _set_target(self, axis, value):
        self._target[axis] = float(value)

    def _stop_axis(self, axis):
        """Freeze the target where the axis currently is, as a real motor's stop would."""
        self._target[axis] = self._position[axis]


def main() -> int:
    app = mkQApp('HardwareModule stage example')
    key = HardwareKey(hardware_class=FakeStage, controller_id=0)
    module = HardwareModule(key, FakeStage)
    module.resize(1100, 600)
    shared_ui = SharedUI(module)  # adds Help, Preferences and a Toolbars visibility menu, as the
    shared_ui.affect_application(module)  # other standalone modules (daq_move.py, daq_viewer.py) do
    shared_ui.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
