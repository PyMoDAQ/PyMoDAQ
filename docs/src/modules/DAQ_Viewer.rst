.. _DAQ_Viewer_module:

DAQ Viewer
==========
This module is to be used to interface any :term:`detector`. It will display hardware settings
and display data as exported by the hardware plugins (see :ref:`data_emission`). The default detector
is a Mock one (a kind of software based
detector generating data and useful to test the program development). Other detectors may be loaded as
plugins, see :ref:`instrument_plugin_doc`.


Introduction
------------
This module has a generic interface comprised of a dockable panel related to the settings and one or more data
viewer panels specific of the type of data to be acquired (see :ref:`data_viewers`). For instance, :numref:`figure_DAQ_Viewer` displays a typical
DAQ_Viewer GUI with a settings dockable panel (left) and a 2D viewer on the right panel.


   .. _figure_DAQ_Viewer:
   
.. figure:: /image/DAQ_Viewer/DAQ_Viewer_pannel.png
   :alt: Viewer panel

   Typical DAQ_Viewer GUI with a dockable panel for settings (left) and a 2D data viewer on the right panel. Red,
   green and purple rectangles highlight respectively the toolbar, the initialization and hardware settings.

Settings
--------

The settings panel is comprised of 3 sections, the top one (red rectangle) displays a toolbar with buttons to grab/snap
data, save them, open other settings sections and quit the application. Two types of settings can be
shown/hidden: for hardware choice/initialization (green rectangle) and advanced settings to control the hardware/software
(purple rectangle).

Toolbar
^^^^^^^

   .. _figure_DAQ_Viewer_toolbar:

.. figure:: /image/DAQ_Viewer/toolbar.PNG
   :alt: Viewer panel

   DAQ_Viewer toolbar


The toolbar, :numref:`figure_DAQ_Viewer_toolbar` allows data acquisition and other actions as described below:

.. |grab| image:: /image/DAQ_Viewer/run2.png
    :width: 10pt
    :height: 10pt

.. |snap| image:: /image/DAQ_Viewer/snap.png
    :width: 10pt
    :height: 10pt

.. |save| image:: /image/DAQ_Viewer/SaveAs.png
    :width: 10pt
    :height: 10pt

.. |snap&save| image:: /image/DAQ_Viewer/Snap&Save.png
    :width: 10pt
    :height: 10pt

.. |open| image:: /image/DAQ_Viewer/Open.png
    :width: 10pt
    :height: 10pt

.. |showsettings| image:: /image/DAQ_Viewer/HLM.png
    :width: 10pt
    :height: 10pt

.. |refresh| image:: /image/DAQ_Viewer/Refresh2.png
    :width: 10pt
    :height: 10pt

.. |do_bkg| image:: /image/DAQ_Viewer/do_bkg.png
    :width: 40pt
    :height: 15pt

.. |take_bkg| image:: /image/DAQ_Viewer/take_bkg.png
    :width: 60pt
    :height: 15pt

.. |ini_det| image:: /image/DAQ_Viewer/ini_det.PNG
    :width: 40pt
    :height: 15pt

.. |quit| image:: /image/DAQ_Move/quit.PNG
    :width: 20pt
    :height: 20pt

.. |log| image:: /image/DAQ_Move/log.PNG
    :width: 20pt
    :height: 20pt

.. |green_led| image:: /image/DAQ_Viewer/green_led.PNG
    :width: 20pt
    :height: 20pt

* |grab|: Start a continuous grab of data. Detector must be initialized.
* |snap|: Start a single grab (snap). Strongly advised for the first time data is acquired after initialization.
* |save|: Save current data
* |snap&save|: Do a new snap and then save the data
* |open|: Load data previously saved with the save button
* |showsettings|: Display or hide initialization and background settings
* |showsettings|: Display or hide hardware/software advanced settings
* |quit|: quit the application
* |log|: open the log in a text editor
* |green_led|: LED reflecting the data grabbed status (green when data has been taken)


Hardware initialization
^^^^^^^^^^^^^^^^^^^^^^^

   .. _figure_DAQ_Viewer_choice:

.. figure:: /image/DAQ_Viewer/hardware_choice.PNG
   :alt: Viewer panel

   Hardware choice, initialization and background management

The second section, :numref:`figure_DAQ_Viewer_choice` allows the choice of the instrument plugin of type detector
selection. They are subdivided by dimensionality of the data they are generating (DAQ2D for cameras, DAQ1D for waveforms,
timeseries... and DAQ0D for detectors generating scalars such as powermeter, voltmeter...). Once selected, the
|ini_det| button will start the initialization using eventual advanced settings. If the initialization is fine,
the corresponding LED will turn green and you'll be able to snap data or take background:


* |take_bkg|: do a specific snap where the data will be internally saved as a background (and saved in a hdf5 file if
  you save data)
* |do_bkg|: use the background previously snapped to correct the displayed (only displayed, saved data are still
  raw data) data.


The last section of the settings (purple rectangle) is a ParameterTree allowing advanced control of the UI and of the
hardware.


.. _viewer_settings:

Main settings
^^^^^^^^^^^^^

Main settings refers to settings common to all instrument plugin. They are mostly related to the UI control.

   .. _figure_DAQ_Viewer_settings:

.. figure:: /image/DAQ_Viewer/settings.PNG
   :alt: settings

   Typical DAQ_Viewer *Main settings*.


* **DAQ type**: readonly string recalling the DAQ type used
* **Detector type**: readonly string recalling the selected plugin
* **Detector Name**: readonly string recalling the given name of the detector (from the preset)
* **Controller ID**: integer used to deal with a controller controlling multiple hardware, see :ref:`multiple_hardware`
* **Show data and process**: boolean for plotting (or not data in the data viewer)
* **Refresh time**: integer used to slow down the refreshing of the display (but not of the eventual saving...)
* **Naverage**: integer to set in order to do data averaging, see :ref:`hardware_averaging`.
* **Show averaging**: in the case of software averaging (see :ref:`hardware_averaging`), if this is set to ``True``,
  intermediate averaging data will be displayed
* **Live averaging**: *show averaging* must be set to ``False``. If set to ``True``, a *live* ``grab`` will perform
  non-stop averaging (current averaging value will be displayed just below).  Could be used to check how much one
  should average, then set *Naverage* to this value
* **Wait time (ms)**: Extra waiting time before sending data to viewer, can be used to cadence DAQ_Scan execution, or data logging
* **Continuous saving**: useful for data logging. Will display new options below in order to set a h5 file to log live data, see :ref:`continuous_saving`.
* **Overshoot options**: useful to protect the experiment. If this is activated, then as soon as any value of the datas exported by this
  detector reaches the *overshoot value*, the module will throw a ``overshoot_signal`` (boolean PyQtSignal). The overshoot manager of the
  *Dashboard* generalize this feature (see :ref:`overshoot_manager`) by triggering actions on actuators if overshoot signals are detected.
  Other features related will soon be added (action triggered on a DAQ_Move, for instance a shutter on a laser beam)
* **Axis options**: only valid for 2D detector. You can add labels, units, scaling and offset (with respect to pixels)
  to both x and y axis of the detector. Redundant with the plugin data export feature (see :ref:`data_emission`)

Data Viewers
------------

Data Viewers presented in section :ref:`data_viewers` are the one used to display data from detectors controlled from
the DAQ_Viewer. By default, one viewer will be set with its type (0D, 1D, 2D, ND) depending on the detector main
dimensionality (DAQ_type: DAQ0D, DAQ1D, DAQ2D...) but in fact the data viewers are set depending on the data exported
from the detector plugin using the `data_grabed_signal` or `data_grabed_signal_temp` signals.

These two signals emit a
list of `DataFromPlugins` objects. The **length** of this list will set the **number of dedicated data viewers**. In
general one, but think about data from a Lockin amplifier generating an amplitude in volt and a phase in degrees.
They are unrelated physical values better displayed in separated axes or viewers. The `DataFromPlugins`'s attribute
`dim` (a string either equal to `Data0D`, `Data1D`, `Data2D`, `DataND`) will determine the data viewer type to set.

This code in a plugin

.. code-block:: python

    self.data_grabed_signal.emit([
        DataFromPlugins(name='Mock1', data=data1, dim='Data0D'),
        DataFromPlugins(name='Mock2', data=data2, dim='Data2D')])

will trigger two separated viewers displaying respectively 0D data and 2D data.

Other utilities
---------------

There are other functionalities that can be triggered in specific conditions. Among those, you'll find:

* The LCD screen to display 0D Data
* The ROI_select button and ROI on a Viewer2D


Saving data
-----------

Data saved from the DAQ_Viewer are data objects has described in :ref:`data_objects` and their saving mechanism
use one of the objects defined in :ref:`module_savers`. There are three possibilities to save data within the
DAQ_Viewer.

*  The first one is a direct one using the snapshots buttons to save current or new data from the
   detector, it uses a ``DetectorSaver`` object to do so. The private method triggering the saving is ``_save_data``.
*  The second one is the continuous saving mode. It uses a ``DetectorEnlargeableSaver`` object to *continuously*
   save data within enlargeable arrays. Methods related to this are: ``append_data`` and ``_init_continuous_save``
*  The third one is not used directly from the ``DAQ_Viewer`` but triggered by extensions such as the ``DAQ_Scan``.
   Data are indexed within an already defined array using a ``DetectorExtendedSaver``. Methods related to this are:
   ``insert_data`` and some code in the ``DAQ_Scan``, see below.

.. code-block::

    for det in self.modules_manager.detectors:
        det.module_and_data_saver = module_saving.DetectorExtendedSaver(det, self.scan_shape)
    self.module_and_data_saver.h5saver = self.h5saver  # will update its h5saver and all submodules's h5saver


Snapshots
^^^^^^^^^

Datas saved directly from a DAQ_Viewer (for instance the one on :numref:`det1D`) will be recorded in
a h5file whose structure will be represented
like :numref:`detector_saver_content` using PyMoDAQ's h5 browser.


.. _continuous_saving:

Continuous Saving
^^^^^^^^^^^^^^^^^
When the *continuous saving* parameter is set, new parameters are appearing on the *DAQ_Viewer* panel
(see :numref:`figure_continuous`). This is in fact the settings associated with the ``H5Saver`` object used under the hood,
see :ref:`h5saver_module`.


* *Base path*: indicates where the data will be saved. If it doesn't exist the module will try to create it
* *Base name*: indicates the base name from which the save file will derive
* *Current Path*: *readonly*, complete path of the saved file
* *Do Save*: Initialize the file and logging can start. A new file is created if clicked again.
* *Compression options*: data can be compressed before saving, using one of the proposed library and the given value of compression [0-9], see *pytables* documentation.

   .. _figure_continuous:

.. figure:: /image/DAQ_Viewer/continuous_saving.PNG
   :alt: continuous

   Continuous Saving options

.. :download:`png <continuous_saving.png>`


The saved file will follow this general structure:

..

  D:\\Data\\2018\\20181220\\Data_20181220_16_58_48.h5


With a base path (``D:\Data`` in this case) followed by a subfolder year, a subfolder day and a filename
formed from a *base name* followed by the date of the day and the time at which you started to log data.
:numref:`figure_continuous_struct` displays the tree structure of such a file, with two nodes (prefixed as
enlargeable, *EnlData*) and a navigation axis corresponding to the timestamps at the time of each snapshot taken
once the continuous saving has been activated (ticking the ``Do Save`` checkbox)

   .. _figure_continuous_struct:

.. figure:: /image/DAQ_Viewer/continuous_data_structure.PNG
   :alt: continuous

   Continuous Saving options

.. :download:`png <continuous_saving.png>`
