# DashBoard

The DashBoard is the heart of PyMoDAQ: it loads the actuators (DAQ_Move) and detectors (DAQ_Viewer) of an experiment, lets
you drive them by hand, and launches the extensions (DAQ_Scan, DAQ_Logger...) that automate the experiment.

## Typical workflow

1. Define or load an **experiment**, the set of actuators and detectors to use, with the **Tools > Experiment** menu
   (see the [experiment manager](https://pymodaq.cnrs.fr/en/latest/user_folder/dashboard_manager.html#experiment-manager)). Experiments are saved as files.
2. Optionally define or load a **state**, a set of settings for the control modules and some special actions
   (**Tools > State**, see the [state manager](https://pymodaq.cnrs.fr/en/latest/user_folder/dashboard_manager.html#state-manager)).
3. Optionally configure the [overshooter](https://pymodaq.cnrs.fr/en/latest/user_folder/dashboard_manager.html#overshoot-manager) (actions
   triggered when a detected value gets out of bounds) and save the
   [regions of interest](https://pymodaq.cnrs.fr/en/latest/user_folder/dashboard_manager.html#roi-manager) of the viewers.
4. Use the actuators and detectors manually to check and adjust your setup.
5. Start an extension from **Tools > Extensions**: DAQ_Scan to automate a scan, DAQ_Logger to log data in time,
   and the other installed extensions.

## Good to know

- The Dashboard can be started from a terminal with the `dashboard` command, `dashboard -exp <name>` loads an experiment
  at startup and `dashboard -h` lists the other arguments.
- Most extensions show a *Dashboard toolbar* to show/hide the Dashboard and to select experiments and states without
  leaving the extension window.
- When the arrangement of the control modules is modified, a layout file is saved for the experiment and restored at
  the next loading (see the **View** menu).
- Several actuators (or detectors) driven by the same hardware controller share it: one is the *Master* and the others
  are *Slaves* (see [multiple hardware from one controller](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html#multiple-hardware-from-one-controller)).

<!-- end of intro -->

## Full documentation

See the [DashBoard documentation](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) for the menus and the toolbar of the extensions, and the
[control modules](https://pymodaq.cnrs.fr/en/latest/modules/Control_Modules.html) one for the actuators and detectors.
