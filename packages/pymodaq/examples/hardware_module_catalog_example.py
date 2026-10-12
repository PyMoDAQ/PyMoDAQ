"""Try HardwareModule with a plugin built only to be a reference, not a device to imitate as a
whole. Run from packages/pymodaq:

    python examples/hardware_module_catalog_example.py

Not a fourth step after minimal/spectrometer/stage - those three tell a story, each adding a few
rows at a time; this one has no story, on purpose. Every row here is isolated to show exactly one
get=/set=/setting=/pre_set=/post_set=/readback= combination, so each can be read on its own without
the others' context. Pairs with capabilities_read_write_catalog.md at the repo root: that doc's
tables list every combination and which example demonstrates it.

What to try, and what each one is for:
- calibration_offset: a control whose write is ``set='_apply_offset'`` - the string-sugar form of
  ``set=``, not shown elsewhere (the stage example uses the same sugar's callable form directly,
  never the string). Type a value and press Enter: the plugin rounds it to the nearest 0.5 dB step
  internally, while the raw value you typed is still stored as ``plugin.calibration_offset`` as
  always (that's why it needs ``set=`` instead of just letting storage alone handle it - the stored
  value and the value the plugin actually applies aren't the same number).
- safety_limit: a control with ``pre_set='_check_safety'`` and nothing else - no ``set=``, no
  ``post_set=``. Try a value above 10 V: the write is rejected (the row turns red) before anything
  is stored. Below 10 V, it's just stored - ``pre_set`` alone doesn't need a matching ``post_set``.
- heater_power: a control with *both* ``pre_set=`` and ``post_set=`` together. Above 400 W it's
  rejected unless the (fixed, for this example) interlock flag is set; any accepted write is also
  logged by ``post_set``, which reads ``plugin.heater_power`` back to prove the value was already
  stored by the time it runs.
- filter_position: a control with ``setting=True`` - its write goes through the plugin's own
  ``params`` (the ``filter_position`` entry there) and ``commit_settings``, not through ``set=`` or
  ``write()`` at all. Changing it also still updates ``plugin.filter_position`` automatically, same
  as every other control.
- gain: a measurement with ``get=`` an actual lambda, not the ``True``/string sugar for it - the
  case that needs a real callable because it does more than forward to one plugin method:
  ``20 * log10(plugin._raw_amplitude())``, combining a method call with a calculation inline.
  ``_raw_amplitude`` also depends on ``calibration_offset``, so the two rows interact: change one,
  watch the other's Grab trace move.
- uptime: a measurement with ``get=True`` - the measurement side of that sugar, not shown elsewhere
  (the other examples only use it on controls, where the write side keeps the attribute populated
  for free). A measurement's attribute is never kept live automatically; here the plugin does it
  itself, in ``_advance()``, as a side effect of computing ``gain``'s own reading.
- setpoint: a control with ``get=True`` *and* ``readback=True``, with nothing else - the no-settling-
  lag case (same shape as the spectrometer's ``exposure``): since ``get=True`` already answers "what
  is it doing right now" exactly, the auto-created ``setpoint_readback`` measurement defaults to that
  same answer for free, no plugin code needed for it at all. Also notice it already reads 3.5 V the
  moment Ini. opens the device, before anything is written - a one-shot read right after connecting
  pushes a ``get=``-backed control's real starting value into its own widget, instead of leaving it
  at 0.0, the spinbox's own construction default (``filter_position`` does the same for a
  ``setting=``-backed control, from ``params`` directly, no device read needed at all: it starts on
  'out', not 'in', the selector's first-added item).
- stage_target / stage_actual_position: the opposite, laggy case - a one-axis motor stage, same idea
  as the stage example's axes but named differently on purpose (``readback='stage_actual_position'``,
  not the default ``stage_target_readback``), to show that the readback's name is independent of the
  control's. ``stage_target`` has no ``get`` (there is real settling time to model), so it's answered
  through ``read()`` instead, same as the stage example's axes. Move it with ``epsilon=0.05`` set:
  the row stays pending (orange) until ``stage_actual_position`` catches up; Stop freezes it where it
  currently is.
- channels: a measurement whose ``get='_read_channels'`` returns an already-built ``DataRaw`` -
  two channels a spectrometer would read together, as two labeled curves sharing one Viewer1D, one
  legend, and one real wavelength ``Axis`` (400-700 nm), not just a bare point index. Nothing is
  declared about any of this on the measurement itself: the labels, the fact that there are two
  curves at all, and the axis all come entirely from what ``_read_channels`` returns, the same way
  ``read()``'s own ``DataToExport`` already lets a plugin build whatever ``DataWithAxes`` it wants -
  ``get=`` can answer with one just as well. Show Graph on this row opens one plot with both curves
  moving together, against their shared wavelength axis.
- frame: a measurement with a plain 2D ``shape=(32, 32)`` - a camera-style reading. Nothing else
  changes: a shape with two dimensions picks ``Viewer2D`` automatically (same rule that picks
  ``Viewer0D``/``Viewer1D`` for the others). Show Graph on this row opens a moving Gaussian blob.

Every quantity except ``stage_target`` answers through its own declared keyword without needing
``read()``/``write()`` at all - ``stage_target`` is the one exception, for the reason real settling
always needs one: there is no single attribute or method call that can report "where the axis
actually is right now" without the device being polled over time.
"""
import sys
import time

import numpy as np
from pymodaq_data.data import Axis, DataRaw
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


def _stop_stage(plugin) -> float:
    """``stop=`` takes a real callable, not the string sugar ``get=``/``set=``/``pre_set=``/
    ``post_set=`` have - so this is a plain function taking ``plugin`` explicitly, the same shape
    the stage example's own ``stop_axis`` closure uses, not a bound method. Freezes ``stage_target``
    where the axis currently is, like a real motor's stop. Returning the new target lets the GUI
    show it too, instead of silently freezing it only on the plugin's side.
    """
    plugin._advance_stage()
    plugin._stage_target = plugin._stage_position
    return plugin._stage_target


class CatalogDevice:
    """One row per keyword combination - see the module docstring for what each one shows.

    ``_interlock_ok`` stands in for a real interlock relay's own status; fixed ``True`` here since
    wiring up a toggle for it would just be another ``control()``, already shown elsewhere, and
    would distract from what this one row (``heater_power``) is actually demonstrating.
    """

    params: list = [
        {'name': 'filter_position', 'type': 'list', 'limits': ['in', 'out'], 'value': 'out',
         'tip': 'Backed by the filter_position control (setting=True): written through here, not write()'},
    ]

    calibration_offset = control(units='dB', lo=-20, hi=20, label='Calibration offset',
                                 docs='Write dispatch: set=\'_apply_offset\' (string sugar)',
                                 set='_apply_offset')
    safety_limit = control(units='V', lo=0, hi=12, label='Safety limit',
                           docs='pre_set alone: rejects above 10 V, nothing else',
                           pre_set='_check_safety')
    heater_power = control(units='W', lo=0, hi=500, label='Heater power',
                           docs='pre_set and post_set together',
                           pre_set='_check_power_range', post_set='_log_power_change')
    filter_position = control(values=['in', 'out'], label='Filter position',
                              docs='setting=True: routes through params, not write()',
                              setting=True)
    gain = measurement(units='dB', label='Gain', docs='get= a real lambda, not True/string sugar',
                       get=lambda plugin: np.array([20 * np.log10(max(plugin._raw_amplitude(), 1e-9))]))
    uptime = measurement(units='s', label='Uptime', docs='get=True on a measurement', get=True)
    setpoint = control(units='V', lo=-10, hi=10, label='Setpoint',
                       docs='get=True and readback=True together: no settling lag, so the auto-'
                            'created readback defaults to the same get=True answer for free',
                       get=True, readback=True)
    stage_target = control(units='mm', lo=0, hi=50, epsilon=0.05, label='Stage target',
                           docs='Laggy case: readback is a differently-named measurement, '
                                'answered through read() since there is no single get= for it',
                           readback='stage_actual_position', set='_set_stage_target',
                           stop=_stop_stage)
    channels = measurement(units='counts', shape=(64,), label='Two channels',
                           docs='get= returning a ready-made DataRaw: two channels, one Viewer1D',
                           get='_read_channels')
    frame = measurement(units='counts', shape=(32, 32), label='Camera frame',
                        docs='A plain 2D shape: Viewer2D is picked automatically, nothing else needed',
                        get='_read_frame')

    def __init__(self):
        self._start = time.monotonic()
        self._elapsed_s = 0.0
        self.uptime = np.array([0.0])
        self._offset = 0.0  # what _apply_offset actually applies; calibration_offset itself still
        # stores the raw value you typed, automatically, same as every other control
        self._interlock_ok = True  # pretend a real interlock relay reports this; fixed here for the example
        self._power_log: list = []
        self._filter_changes = 0
        self.calibration_offset = 0.0
        self.safety_limit = 0.0
        self.heater_power = 0.0
        self.filter_position = 'out'  # differs from 'in', the selector's own first-added item -
        # see the module docstring on setpoint/filter_position for what that's demonstrating
        self.setpoint = 3.5  # likewise differs from 0.0, the spinbox's own construction default
        self._stage_target = 0.0
        self._stage_position = 0.0
        self._stage_last_update = time.monotonic()

    def open(self, settings):
        self._start = time.monotonic()
        self._stage_last_update = time.monotonic()

    def close(self):
        pass

    def read(self, names=None, fresh=True):
        """Only ``stage_actual_position`` ever reaches this - every other quantity answers through
        its own declared ``get``/``set``/``setting``, so there is nothing else for this to serve.
        """
        self._advance_stage()
        arrays = {}
        for name in names:
            if name == 'stage_actual_position':
                arrays[name] = np.array([self._stage_position])
        return _Reading(arrays)

    def _advance(self) -> None:
        """Wall-clock elapsed time, and the one place ``uptime`` - a measurement, so nothing stores
        it for free the way a control's write does - gets kept live. Called from ``_raw_amplitude``
        rather than from ``read()``, since neither ``gain`` nor ``uptime`` goes through it.
        """
        self._elapsed_s = time.monotonic() - self._start
        self.uptime = np.array([self._elapsed_s])

    def _raw_amplitude(self) -> float:
        self._advance()
        return 2.0 + np.sin(self._elapsed_s) * (1 + self._offset / 20)

    def _apply_offset(self, value: float) -> None:
        """Rounds to the nearest 0.5 dB step - the reason this needs ``set=`` instead of letting the
        automatic storage alone handle it: what the device actually applies isn't the raw value.
        """
        self._offset = round(value * 2) / 2

    def _check_safety(self, value: float) -> None:
        if value > 10:
            raise ValueError('safety_limit above 10 V needs a manual override, not a plain write')

    def _check_power_range(self, value: float) -> None:
        if value > 400 and not self._interlock_ok:
            raise ValueError('heater_power above 400 W needs the interlock closed')

    def _log_power_change(self, value: float) -> None:
        # post_set runs after storage, so plugin.heater_power already holds `value` here too -
        # reading it back instead of using the argument is the point being demonstrated
        self._power_log.append(self.heater_power)

    def _set_stage_target(self, value: float) -> None:
        self._stage_target = float(value)

    def _advance_stage(self) -> None:
        now = time.monotonic()
        step = 10.0 * (now - self._stage_last_update)  # fixed 10 mm/s, no speed setting here
        self._stage_last_update = now
        error = self._stage_target - self._stage_position
        self._stage_position += float(np.clip(error, -step, step))

    def _read_channels(self) -> DataRaw:
        """Two channels at once, as a real spectrometer would report them together: two emission
        peaks on a noisy baseline, same idea as the spectrometer example's own ``spectrum`` (a
        shape plus noise, not a bare deterministic curve) - sharing one real wavelength ``Axis``,
        not just a point index, which a plain ``get=`` value has no way to carry at all. Builds and
        returns the full ``DataRaw`` itself; there is nothing declared on ``channels`` for any of
        this - the curves, their labels and the axis are exactly whatever this method returns.
        """
        self._advance()
        wavelength = np.linspace(400, 700, 64)  # nm - a real spectrometer's own calibration
        baseline = 0.3
        noise_std = 0.05
        # ch_a: a fixed emission line at 500 nm. ch_b: a second line, slowly drifting (e.g. thermal
        # wander in a real grating) and weaker - two detector channels that read differently, not
        # the same signal twice.
        ch_a = baseline + 3.0 * np.exp(-(wavelength - 500) ** 2 / (2 * 12 ** 2))
        peak_b = 600 + 15 * np.sin(self._elapsed_s / 3)
        ch_b = baseline + 1.5 * np.exp(-(wavelength - peak_b) ** 2 / (2 * 18 ** 2))
        return DataRaw('channels',
                       data=[ch_a + np.random.normal(0, noise_std, 64),
                             ch_b + np.random.normal(0, noise_std, 64)],
                       units='counts', labels=['ch_a', 'ch_b'],
                       axes=[Axis('wavelength', units='nm', data=wavelength, index=0)])

    def _read_frame(self) -> np.ndarray:
        """One plain 2D array - a Gaussian blob drifting in a circle. Nothing about this is
        different from any other ``get=``: ``frame``'s declared ``shape=(32, 32)`` is what picks
        ``Viewer2D``, the same as a 1D shape picks ``Viewer1D``.
        """
        self._advance()
        y, x = np.mgrid[0:32, 0:32]
        cx = 16 + 8 * np.sin(self._elapsed_s)
        cy = 16 + 8 * np.cos(self._elapsed_s)
        return np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 6 ** 2))

    def commit_settings(self, param):
        if param.name() == 'filter_position':
            self._filter_changes += 1


def main() -> int:
    app = mkQApp('HardwareModule catalog example')  # applies the PyMoDAQ theme and style
    key = HardwareKey(hardware_class=CatalogDevice, controller_id=0)
    module = HardwareModule(key, CatalogDevice)
    module.resize(1100, 550)
    shared_ui = SharedUI(module)  # adds Help, Preferences and a Toolbars visibility menu, as the
    shared_ui.affect_application(module)  # other standalone modules (daq_move.py, daq_viewer.py) do
    shared_ui.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
