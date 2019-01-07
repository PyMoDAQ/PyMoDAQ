.. _DAQ_Viewer_module:

DAQ Viewer
==========
This module is to be used to interface any detector. It will display hardware settings
and display data as exported by the hardware plugins (see :ref:`data_emission`). The default detector
is a Mock ones (a kind of software based
detector generating data and useful to test the program development). Other detectors may be loaded as
plugins, see :ref:`plugin_doc`.


Introduction
------------
This module has a generic interface comprised of a dockable panel related to the settings and one or more viewers
specific of the type of data to be acquired (see :ref:`data_viewers`. For instance, :numref:`figure_DAQ_Viewer` displays a typical
DAQ_Viewer GUI with a settings dockable panel (left) and a 2D viewer on the right panel.


   .. _figure_DAQ_Viewer:
   
.. figure:: /image/DAQ_Viewer/DAQ_Viewer_pannel.png
   :alt: Viewer panel

   Typical DAQ_Viewer GUI with a dockable panel for settings (left) and a 2D viewer on the right panel.
   
.. :download:`png <DAQ_Viewer_pannel.png>`


Settings
--------

The settings panel is comprised of 2 sections, the top one displays buttons to select a given hardware
(*DAQ type* and *Detector*), initialize it, grab and save data. The bottom one,
:numref:`figure_DAQ_Viewer_settings`, is a Tree type parameter
list displaying the viewer main settings (:ref:`viewer_settings`) and specific settings of the chosen hardware
(see :ref:`hardware_settings`).

Hardware initialization
^^^^^^^^^^^^^^^^^^^^^^^

* ``DAQ_type``: either *DAQ0D*, *DAQ1D* or *DAQ2D* respectively for scalar detectors (powermeter for instance),
  vector detectors (spectrometer for instance) and image like detectors.
* ``Detector``: list of available hardware plugins of the DAQ_type type.
* ``Ini. Det``: Initialize the hardware with the given settings (see :ref:`plugin_doc` for details on how to set hardware settings.)
* ``Quit``: De-initialize the hardware and quit the application

Data Acquisition
^^^^^^^^^^^^^^^^
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

.. |showsettings| image:: /image/DAQ_Viewer/HLM.ico
    :width: 10pt
    :height: 10pt

.. |refresh| image:: /image/DAQ_Viewer/Refresh2.png
    :width: 10pt
    :height: 10pt

.. |do_bkg| image:: /image/DAQ_Viewer/do_bkg.png
    :width: 30pt
    :height: 15pt

.. |take_bkg| image:: /image/DAQ_Viewer/take_bkg.png
    :width: 30pt
    :height: 15pt

.. |save_sett| image:: /image/DAQ_Viewer/save_settings.png
    :width: 30pt
    :height: 15pt

.. |load_sett| image:: /image/DAQ_Viewer/open_settings.png
    :width: 30pt
    :height: 15pt



* |grab|: Start a continuous grabing of data. Detector must be initialized.
* |snap|: Start a single grab (snap). Mandatory for the first time data is acquired after initialization.
* |save|: Save current data
* |snap&save|: Do a new snap and then save the data
* |open|: Load data previously saved with the save button
* |showsettings|: Display or hide the settings Tree
* |refresh|: try to refresh the hardware, for instance the list of COM ports
* |take_bkg|: do a specific snap where the data will be saved as a background
* |do_bkg|: use the background previously saved to correct the displayed (only displayed, saved data are still raw data) datas.
* |save_sett|: Save in a file the current settings in a file for later recall
* |load_sett|: Recall from a file the settings

The last two options are useful only in stand alone mode. When used with the DAQ_Scan module, all settings are *preset*
using the *preset manager* (see :ref:`preset_manager`).

.. _viewer_settings:

Main settings
^^^^^^^^^^^^^

The first tree section in the settings refers to the acquisition options. The first two items are just a reminder of the type of
detector currently activated.

   .. _figure_DAQ_Viewer_settings:

.. figure:: /image/DAQ_Viewer/settings.png
   :alt: settings

   Typical DAQ_Viewer *Main settings*.


* **DAQ type**: readonly string recalling the DAQ type used
* **Detector type**: readonly string recalling the selected plugin
* **Nviewers**: readonly integer displaying the number of data viewers
* **Controller ID**: integer used to deal with a controller controlling multiple hardware, see :ref:`multiple_hardware`
* **Naverage**: integer to set in order to do data averaging, see :ref:`hardware_averaging`.
* **Show averaging**: in the case of software averaging (see :ref:`hardware_averaging`), if this is set to ``True``, intermediate averaging data will be displayed
* **Live averaging**: *show averaging* must be set tot ``False``. If set to ``True``, a *live* ``grab`` will perform
  non-stop averaging (current averaging value will be displayed just below).  Could be used to check how much one should average, then set *Naverage* to this value
* **Wait time (ms)**: Extra waiting time before sending data to viewer, can be used to cadence DAQ_Scan execution, or data logging
* **Continuous saving**: useful for data logging. Will display new options below in order to set a h5 file to log live data, see :ref:`continuous_saving`.
* **Overshoot options**: useful to protect the experiment. If this is activated, then as soon as any value of the datas exported by this
  detector reaches the *overshoot value*, the module will throw a ``overshoot_signal`` (boolean PyQtSignal) that will **stop the DAQ_Scan execution right away**.
  Other features related will soon be added (action triggered on a DAQ_Move, for instance a shutter on a laser beam)
* **Axis options**: only valid for 2D detector. You can add labels, units, scaling and offset (with respect to pixels)
  to both x and y axis of the detector. Redundant with the plugin data export feature (see :ref:`data_emission`)




