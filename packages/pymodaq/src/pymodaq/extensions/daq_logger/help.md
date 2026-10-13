# DAQ_Logger

DAQ_Logger logs, as a function of time, the data of the selected detectors and the values of the selected actuators,
in a hierarchical HDF5 file.

## Typical workflow

1. Define or load an experiment in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html), then apply it with the Dashboard toolbar of
   the extension: the workflow actions are enabled once it is applied.
2. In the **Detectors** panel, select the actuators and detectors to log.
3. Select or create the h5 file with the file toolbar.
4. Use **Grab All** to start/stop the acquisition of all the selected modules, then press **Start** to log.
   **Pause** and **Stop** act at any time.

## Good to know

- Each data produced by a detector (when its grab is done) and each actuator value is saved as it arrives, with its
  time stamp. The status bar shows the logging state and the number of saved items.
- Saving is done in the background: the extension cannot be closed while the data are still being written.
- A logging cannot be running when closing the extension: stop it first.
- The logged file can be explored with the [H5Browser](https://pymodaq.cnrs.fr/en/latest/data_management/h5browser.html).

<!-- end of intro -->

## Full documentation

See the [DAQ_Logger documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_logger.html).
