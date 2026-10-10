"""Try HardwareModule with a fake three-axis stage. Run from packages/pymodaq:

    python examples/hardware_module_stage_example.py

Step 3 of 3: builds on hardware_module_example.py (get/set, a plugin setting) by adding a readback,
settling, Stop and Enable. If this one feels like a lot at once, start with
hardware_module_minimal_example.py (step 1) and hardware_module_example.py (step 2) first.

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
- Each axis starts disabled: its own control (merge_into=<axis>), rendered as a checkable action right
  in the axis's own row, next to Stop, rather than as a row of its own. Moving a disabled axis is
  rejected (write_failed), turning that axis's row red - click Enable first.

Each target (x, y, z) has its own set and stop callback, so writing or stopping one never goes through
write() at all: the plugin does not define it. The positions and motion stay in read(), since they all
depend on one shared _advance() step and would lose that if each had its own get.

x/x_enable, y/y_enable and z/z_enable are near-identical: a target plus its enable, differing only in
the axis name, its range and (for z) its readback name. Rather than writing that shape out three times
(three pairs of lambdas just to curry the axis in), _axis_controls below builds it once and is called
once per axis - the closures over axis still exist, same as a lambda would need, but they're written
in exactly one place instead of copy-pasted, and the declarations read as plain data (name, range).
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


def _axis_controls(axis, lo, hi, *, readback=True):
    """The enable and target controls for one axis of the stage: the shared shape, built once
    here instead of copy-pasted per axis below. Assumes the plugin keeps ``_enabled``, ``_target``
    and ``_position`` dicts keyed by axis name, as :class:`FakeStage` does.
    """

    def set_target(plugin, value):
        if not plugin._enabled[axis]:
            raise RuntimeError(f'{axis} is disabled')  # write_failed: the enable action's row turns red
        plugin._target[axis] = float(value)

    def stop_axis(plugin):
        """Freeze the target where the axis currently is, as a real motor's stop would.

        Returning the new target lets the GUI show it too (the spinbox and slider follow), instead of
        silently freezing it only on the plugin's side.
        """
        plugin._target[axis] = plugin._position[axis]
        return plugin._target[axis]

    def set_enabled(plugin, value):
        plugin._enabled[axis] = value == 'enabled'

    enable = control(values=['disabled', 'enabled'], merge_into=axis, label='Enable', set=set_enabled)
    target = control(units='mm', lo=lo, hi=hi, epsilon=0.01, label=axis.upper(), ui_add=('slider',),
                     readback=readback, set=set_target, stop=stop_axis)
    return enable, target


class FakeStage:
    """Three axes. Each target is a control whose readback, ``<axis>_readback``, is its position.

    Each target's ``set`` writes straight to ``_target``, and ``stop`` freezes it where the axis
    currently is, so the plugin needs no ``write()`` at all. See :func:`_axis_controls` above for
    how ``x``/``x_enable`` etc. are actually built.

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

    x_enable, x = _axis_controls('x', 0, 50)
    y_enable, y = _axis_controls('y', 0, 50)
    z_enable, z = _axis_controls('z', 0, 10, readback='my_z_readback')
    motion = measurement(values=['idle', 'moving'], label='Motion')

    AXES = ('x', 'y', 'z')

    def __init__(self):
        self._target = {axis: 0.0 for axis in self.AXES}
        self._position = {axis: 0.0 for axis in self.AXES}
        self._enabled = {axis: False for axis in self.AXES}  # matches the enable control's default
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
