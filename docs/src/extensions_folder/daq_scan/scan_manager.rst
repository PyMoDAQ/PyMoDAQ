.. _scan_manager:

Scan Manager
------------

The *Scan Manager* allows to define a complete scan once, save it under a name and call it later on. It is one of the
managers sharing the same structure as the *DashBoard Managers* (see :ref:`dashboard_manager`): a GUI to create, copy,
save, reload, delete and execute *entries*, here scans, saved as ``.scan`` files in the ``scans`` folder of the PyMoDAQ
configuration folder (see :ref:`configfile`).

.. note::

   The Scan Manager is meant to define the scans that the *Sequencer* will call, in order to chain scans with other
   actions (see :ref:`sequencer_extension`). The corresponding scan element of the Sequencer does not exist yet.

A scan entry contains:

* the actuators and detectors selected for the scan
* the *Scanner* settings: scan type, subtype and the start, stop, step... values of each actuator (see
  :ref:`daq_scan_scanner`)
* a selection of the other settings of the DAQ_Scan (time flow, scan options, plotting options...) and of the h5 saver
  (see :ref:`settings_paragraph`) together with their values
* whether the scan should be started once all the settings have been applied

Using a scan
++++++++++++

The Scan Manager toolbar (see :numref:`scan_manager_toolbar_fig`) is part of the DAQ_Scan window. Its first button opens
the Scan Manager window, the list gives access to the saved scans and the last button executes the selected scan.

   .. _scan_manager_toolbar_fig:

.. figure:: /image/DAQ_Scan/scan_manager_toolbar.png
   :alt: Scan Manager toolbar

   The Scan Manager toolbar of the DAQ_Scan: open the manager, list of the saved scans and execute the selected one.

Executing a scan applies, one after the other, the selection of the actuators and detectors, the scanner settings and the
selected settings. A window displays the progress and flags the entries that could not be applied (for instance a module
that is not part of the experiment loaded in the Dashboard). If the scan entry has been defined to do so, the scan is then
started, exactly as if the **Start** button of the toolbar had been pressed. If not, the DAQ_Scan is only configured and
the scan can be started manually.

Defining a scan
+++++++++++++++

.. TODO: add a screenshot of the Scan Manager window here (needs the ProbeData bug of the Scan Manager fixed).
   Check the numbered steps below against it.

The Scan Manager window is divided in numbered steps:

#. **Configure a Scan**: select the actuators and the detectors and set the scanner, as in the DAQ_Scan main window
   (see :ref:`daq_scan_scanner`).
#. **Get Data To Plot**: click on the *ProbeData* button to probe the selected detectors and list the data they generate
   in the *Plot 0Ds* and *Plot 1Ds* options, then select the data to be plotted live (see :ref:`daq_scan_live_data`).
#. **Select Settings to Apply**: browse the settings tree and use the *Add* arrow to put in the *Settings to Apply* table
   the settings (and their current value) that should be set when the scan is executed. The table can be reordered
   (*Move up* / *Move down*) and settings can be removed (*Remove*). The *Show All Settings* button displays all the
   settings (the ones that can be configured are in green).
#. **Settings to Apply**: the table of the settings that will be applied.
#. **Start Scan... or not**: the *Start Scan* button of the toolbar below the table defines if the scan should be started
   when the entry is executed.

Then save the scan with the *Save* button of the manager toolbar, after having created it with *New* (or *Copy*).
