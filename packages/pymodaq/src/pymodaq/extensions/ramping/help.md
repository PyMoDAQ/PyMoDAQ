# Ramping

The Ramping extension drives one actuator linearly from a start to a stop value in a given duration, while the
selected detectors and actuators are acquired continuously and live, without waiting for the actuator. It is made for
continuous sweeps (temperature, current, voltage, delay line...) where the DAQ_Scan stop-and-measure approach would be too slow.

## Typical workflow

1. Define an experiment in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) and apply it with the Dashboard toolbar of the
   extension: the workflow actions are enabled once it is applied.
2. In the **Settings** dock, choose the ramping actuator, its start and stop values, the duration (or the velocity),
   and the detectors and actuators to record.
3. Press **Init Positions** to move the ramping actuator to its start value, to prepare the setup.
4. Check **Log** to save all the data with time stamps in a h5 file and to display the live histogram, then press
   **Start**: the actuator goes to the start value, then the ramp and the acquisition begin and end after the duration.
5. **Pause** and **Stop** act at any time. The histogram, the data as a function of the ramped value, can be
   recomputed after the ramp with **Update Histogram**, or later from the saved file.

## Good to know

- The extension only sends target values on a time schedule: choose the settings according to what your actuator
  can do (maximum velocity, acceleration) and to the acquisition rate of the detectors.
- Without steps a single move to the stop value is sent and the hardware is expected to ramp by itself (temperature
  controller, power supply...). Its speed must then be consistent with the duration.
- Data still waiting to be saved are written when the ramp is stopped: the extension cannot be closed before.

<!-- end of intro -->

## Full documentation

See the [Ramping documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/ramping.html) for the settings, the ramp parameters and the histogram.
