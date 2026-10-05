# DAQ_Scan

DAQ_Scan automates data acquisition: it moves one or more actuators through a set of values and saves the data
from the selected detectors at each position, in hierarchical HDF5 files.

## Typical workflow

1. Define or load an experiment in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) first (see the
   [experiment manager](https://pymodaq.cnrs.fr/en/latest/user_folder/dashboard_manager.html#experiment-manager)).
2. In the [**Instrument selection**](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_scan/daq_scan_main.html#selecting-detectors-and-actuators)
   panel, pick the detectors and actuators for the next scan.
3. In the [**Scanner**](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_scan/scanner.html) settings, choose the scan type (1D, 2D, ...) and its subtype, then set the start, stop and
   step values of each actuator.
4. In the [**Live plots selection**](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_scan/daq_scan_main.html#selecting-the-data-to-render-live)
   panel, use the data button to list the data available from the selected
   detectors, and tick what should be plotted live. Nothing is plotted by default.
5. In the [**Save settings**](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_scan/daq_scan_main.html#saving-dataset-and-scans), check what is saved, how and where.
6. Press **Start** to run the scan. **Stop** ends it
   ([scan flow](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_scan/daq_scan_main.html#scan-flow)).

## Good to know

- A dataset is one saved file that can contain several scans, usually for one sample or subject.
- Live plots combine the dimension of the data with the scan dimension. Keep the total at 2 or less, and use
  [regions of interest](https://pymodaq.cnrs.fr/en/latest/user_folder/viewers_usage.html#regions-of-interest) (ROI) to reduce raw data to a plottable form.
- Saved files can be explored with the [H5Browser](https://pymodaq.cnrs.fr/en/latest/data_management/h5browser.html) extension.

<!-- end of intro -->

## Full documentation

See the [DAQ_Scan documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_scan/daq_scan.html)
for scanner types, the [navigator](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_scan/navigator.html) and
[batch scans](https://pymodaq.cnrs.fr/en/latest/extensions_folder/daq_scan/scan_batch.html).
