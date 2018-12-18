.. _DAQ_Viewer_module:

DAQ Viewer
==========
Module to be used to interface any detector and plot live data and many other features
such as data analysis. The default detectors are the mock ones (a kind of software based
detector generating data useful to test the program). Other detectors may be loaded as
plugins, see section: :ref:`viewer_plugins`.


Introduction
------------
This module has a generic interface comprised of a dockable panel related to the settings and one or more viewers specific of the type of data to be acquired. For instance, :numref:`figure_DAQ_Viewer` displays a typical DAQ_Viewer GUI with a settings dockable panel (left) and a 2D viewer on the right panel.


   
   .. _figure_DAQ_Viewer:
   
.. figure:: /image/DAQ_Viewer/DAQ_Viewer_pannel.png
   :alt: Viewer pannel
   :scale: 100%
   
   Typical DAQ_Viewer GUI with a settings dockable panel (left) and a 2D viewer on the right panel.
   
.. :download:`png <DAQ_Viewer_pannel.png>`


Settings
--------

The settings panel is comprised of 2 sections, the top one displays buttons to select a given hardware (DAQ_type and detector). The bottom one is a Tree type parameter list displaying main settings (Main Settings section) of the module and specific settings of the chosen hardware (Detector Settings section, see Mock plugins for instance).

Hardware initialization
^^^^^^^^^^^^^^^^^^^^^^^

* ``DAQ_type``: either DAQ0D, DAQ1D or DAQ2D respectively for scalar detectors (powermeter for instance), vector detectors (spectrometer for instance) and image like detectors.
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



* |grab|: Start a continuous grabing of data. Detector must be initialized.
* |snap|: Start a single grab (snap). Mandatory for the first time data is acquired after initialization.
* |save|: Save current data
* |snap&save|: Do a new snap and then save the data
* |open|: Load data previously saved with the save button
* |showsettings|: Display or hide the settings Tree
* |refresh|: try to refresh the hardware, for instance the list of COM ports
* Take bkg: do a specific snap where the data will be saved as a background
* Do bkg: use the background previously saved to correct the displayed (only displayed, saved data are still raw data) datas.

Settings Tree
^^^^^^^^^^^^^

Main settings
^^^^^^^^^^^^^

Data Viewers
------------

0D Viewer
^^^^^^^^^

1D Viewer
^^^^^^^^^

2D Viewer
^^^^^^^^^

.. _NDviewer:

ND Viewer
^^^^^^^^^

