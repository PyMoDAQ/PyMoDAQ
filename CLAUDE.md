# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PyMoDAQ (Modular Data Acquisition with Python) is a Qt-based framework to drive lab experiments: hardware is
interfaced through small plugins (actuators / detectors), and PyMoDAQ provides the GUI, threading, data model,
HDF5 saving and higher-level extensions (scans, PID, logging, optimisation...). Supported Python: 3.10–3.13.
Branches and PR targets:
- `dev` is the development branch: new features target `dev`.
- `5.2.x` is the current release branch: bugfixes may target it.
- When a new minor version is released (e.g. the future `5.3.x`), a branch with that name is created and becomes the new
  latest/main release branch. Older `5.x.y` branches are kept to receive hotfix patches if needed.

## Repository layout

Monorepo of five independently published packages under `packages/<name>/` (each with `src/<name>/`,
`tests/`, its own `pyproject.toml` built with hatchling + hatch-vcs). Dependency order (lower depends on nothing above):

1. `pymodaq_utils` – config (TOML, template in `resources/config_template.toml`), logger, enums, serialization,
   factories, entry-point discovery (`packages.py`, `utils.py`)
2. `pymodaq_data` – the data model (`data.py`: `Axis`, `DataWithAxes`/`DataRaw`/`DataCalculated`,
   `DataToExport`, pint units via `Q_`/`Unit`), HDF5 backends (`h5modules`), slicing
3. `pymodaq_scripting` – client to drive a running Dashboard from another process
4. `pymodaq_gui` – Qt toolkit: pyqtgraph-based `Parameter` trees and custom ptypes, data viewers, managers
   (ROI, action, parameter managers), h5 browser
5. `pymodaq` – control modules, Dashboard, extensions, TCP/IP and LECO remote control, scanners

When changing an API in a lower package, check usages in the packages above it. `README.rst` files are
**generated from `README.rst.tpl`** by CI – edit the `.tpl`, never the `.rst`.

## Commands

Install all packages in editable mode (order matters, the script handles it):

```bash
python install-packages.py -d                 # editable + dev extras
python install-packages.py -d -u pymodaq_data # only up to a given package
python install-packages.py -d -qt pyside6     # choose Qt backend (pyqt5/pyqt6/pyside6)
```

Tests (pytest + pytest-qt; root `pyproject.toml` sets `--import-mode=importlib` and `testpaths = packages`):

```bash
pytest packages/pymodaq_data                                   # one package
pytest packages/pymodaq/tests/control_modules/daq_move_test.py::TestMethods::test_overriden    # single test
pytest packages/pymodaq -m "not leco"                          # as in CI (LECO tests need a running coordinator)
```

CI runs each package from its own directory (`cd packages/<pkg> && pytest`) on Windows + Ubuntu (xvfb), with
`QT_API`/`PYTEST_QT_API` set to `pyqt6` and `pyside6` – code must stay backend-agnostic: always import Qt via `qtpy`.

Lint: CI only fails on `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`. Ruff is configured in
the root `pyproject.toml` (line length 120) but not enforced.

Entry points (console scripts of `pymodaq`): `dashboard`, `daq_move`, `daq_viewer`, `daq_scan`, `daq_logger`, `pymodaq`.

## Architecture

**Plugins are external.** Hardware support lives in separate `pymodaq_plugins_*` distributions discovered through
importlib entry points (groups `pymodaq.plugins`, `pymodaq.instruments`, `pymodaq.extensions`, `pymodaq.scanners`,
`pymodaq.models`, `pymodaq.pid_models`). `pymodaq_plugins_mock` is a hard dependency and is what tests use.

**Control modules** (`pymodaq/control_modules/`): `DAQ_Move` (actuator) and `DAQ_Viewer` (detector) both derive from
`ControlModule` (`utils.py`). Each module owns a UI (built by a factory in `daq_move_ui/` / `daq_viewer_ui/`), and
runs its hardware plugin inside a `HardwareWorkerBase` subclass (`ActuatorWorker`, `DetectorWorker`) living in a
`QThread`. Plugins derive from `DAQ_Move_base` / `DAQ_Viewer_base` (both from `PluginBase`, `plugin_base.py`) and
implement template methods (`ini_stage`/`ini_detector`, `move_abs`, `grab_data`, `commit_settings`, `close`...).

**Communication is via Qt signals carrying `ThreadCommand`** (`pymodaq_utils.utils.ThreadCommand`: a command name
plus attributes). Command vocabularies are enums in `control_modules/thread_commands.py`
(`ThreadStatus`, `ThreadStatusMove`, `ControllerStatus`...). UI → module → worker and back all go through
`thread_status`/`process_ui_cmds` dispatchers; add new commands to these enums rather than using raw strings.

**Master/slave controllers**: several modules can share one hardware controller and one thread
(`ControllerAndThread`, `QThreadProxy` in `control_modules/utils.py`); the master initializes it, slaves reuse it.

**Settings** are pyqtgraph `Parameter` trees declared as lists of dicts (`params = [{'title', 'name', 'type',
'value', 'children'...}]`). Common mandatory parameters are injected by `comon_parameters_fun` (actuators) /
`comon_parameters` (viewers). Legacy group names (`multiaxes` → `controller`, `multi_status` →
`controller_status`) are transparently translated by `_BackCompatGroupParameter` in `plugin_base.py`.

**Data flow**: actuators exchange `DataActuator`, detectors emit `DataToExport` (a collection of
`DataWithAxes`), always with pint units. Units mismatches raise `DataUnitError`. Saving goes through `H5Saver` and
module savers (`pymodaq_gui.h5modules.saving`, `pymodaq/utils/h5modules/module_saving.py`).

**Dashboard** (`dashboard.py`) loads a *preset* of control modules, managed through the `ModulesManager` (`utils/managers/modules`),
and launches **extensions** (`extensions/`: scan, logger, PID, ramping, sequencer, data_mixer, bayesian/adaptive
optimisers built on `optimizers_base`, console, h5browser). Extensions receive the Dashboard and act on its
modules; third-party extensions register through the `pymodaq.extensions` entry point.

**Remote control**: TCP/IP (`utils/tcp_ip`) and LECO (`utils/leco`, pyleco) let control modules be driven from
other processes; `pymodaq_scripting` is the client side.

## Conventions

- Backward compatibility with existing external plugins matters: keep old names working through shims and emit
  `deprecation_msg` / `DeprecationWarning` instead of breaking them.
- Use `pymodaq_utils.config` (`config('pymodaq', 'actuator', ...)`) for defaults rather than hard-coded values;
  new config keys go into the package's `config_template.toml`.
- Loggers: `logger = set_logger(get_module_name(__file__))`. Docstrings: NumPy style.
