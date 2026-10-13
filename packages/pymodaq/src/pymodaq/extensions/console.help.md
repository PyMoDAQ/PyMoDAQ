# Console

The Console is an IPython console running inside PyMoDAQ, to interact with the Dashboard and its control modules with
python commands.

## Typical workflow

1. Define an experiment in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) and apply it with the Dashboard toolbar of the
   extension.
2. Type python commands in the console. The objects `dashboard` (the Dashboard) and `mods` (the manager of its
   control modules) are available once the experiment is applied, together with `numpy` as `np`.

## Good to know

- `mods` gives access to the actuators and detectors loaded in the Dashboard, to move or grab them from the console.
- For inline plots use the `%matplotlib` magic command.
- To drive PyMoDAQ from another process, see the [scripting package](https://pymodaq.cnrs.fr/en/latest/user_folder/scripting.html).

<!-- end of intro -->

## Full documentation

See the [Console documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/console.html).
