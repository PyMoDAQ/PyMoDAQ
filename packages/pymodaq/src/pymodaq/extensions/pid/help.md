# PID

The PID extension keeps a parameter of your experiment (a temperature, the length of an interferometer, the pointing of
a beam...) at a setpoint: it reads the detectors, computes the error with a *model*, and sends the corrections to the
actuators with a PID filter.

## Typical workflow

1. Define an experiment with the actuators and detectors to use in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) and apply it
   with the Dashboard toolbar of the extension.
2. In the settings, select the **Model class** (it defines the detectors read, the actuators driven and the setpoints),
   set its parameters and **initialize the model**.
3. **Initialize the PID**, then start the loop with the **Play** button: the corrections are computed but not applied
   while the **Pause** button is checked.
4. Uncheck **Pause** to apply the corrections to the actuators.
5. Tune the PID with the setpoints, the output limits and the Kp, Ki and Kd constants, and follow the result in the
   input/output plot and the stability value.

## Good to know

- The corrections are limited below 100 Hz because the feedback runs on a computer: use an analog solution if you need
  faster. The time per loop displayed is the minimum sample time you can ask for, it mostly depends on the detector
  acquisition time.
- The output limits only protect the system from too large corrections, they do not slow the correction down (use Kp
  for that). Start with Kp = 1, Ki = 0, Kd = 0.
- Setpoints can be changed automatically in time, for instance to scan a sample while keeping a stable position.
- You can write your own model, see *How to write a PID model?* in the documentation.

<!-- end of intro -->

## Full documentation

See the [PID module documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/pid_module.html) for a complete example, the configuration of the
PID and how to write a model.
