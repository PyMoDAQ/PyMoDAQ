"""Try HardwareModule with a fake three-axis stage. Run from packages/pymodaq:

    python examples/hardware_module_stage_example.py

Each axis is one row: a target (a control, with a spinbox and a slider) and its position (a
measurement, linked as the control's readback), like DAQ_Move. The position moves towards the target
at a fixed speed, and only while the device is read. So:
- Ini. opens the stage.
- Move a target with the slider or the spinbox. The device gets the new target at once.
- Grab the position of an axis (Grab, blue LED). Its display follows the target with a delay.
- Motion shows "moving" while any axis is still on its way.

Each target (x, y, z) has its own set callback, so writing one never goes through write() at all:
the plugin does not define it. The positions and motion stay in read(), since they all depend on
one shared _advance() step and would lose that if each had its own get.
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

    Each target's ``set`` writes straight to ``_target``, so the plugin needs no ``write()`` at all.
    """

    params: list = []
    speed = 10.0  # mm/s, the same for every axis

    x = control(units='mm', lo=0, hi=50, epsilon=0.01, label='X', ui_add=('slider',), readback=True,
               set=lambda plugin, value: plugin._set_target('x', value))
    y = control(units='mm', lo=0, hi=50, epsilon=0.01, label='Y', ui_add=('slider',), readback=True,
               set=lambda plugin, value: plugin._set_target('y', value))
    z = control(units='mm', lo=0, hi=10, epsilon=0.01, label='Z', ui_add=('slider',), readback="my_z_readback",
               set=lambda plugin, value: plugin._set_target('z', value))
    motion = measurement(values=['idle', 'moving'], label='Motion')

    AXES = ('x', 'y', 'z')

    def __init__(self):
        self._target = {axis: 0.0 for axis in self.AXES}
        self._position = {axis: 0.0 for axis in self.AXES}
        self._last_update = time.monotonic()
        # the readback names come from the declarations, so any name works
        self._axis_of_readback = {c.readback: c.name for c in Capabilities.from_device(type(self)).controls
                                  if c.readback}

    def open(self, settings):
        self._last_update = time.monotonic()

    def close(self):
        pass

    def _advance(self) -> None:
        """Move every axis towards its target for the time elapsed since the last update."""
        now = time.monotonic()
        step = self.speed * (now - self._last_update)
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
