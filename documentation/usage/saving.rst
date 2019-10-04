.. _saving_doc:

Saving datas
============

Datas saved using PyMoDAQ, either the *DAQ_Scan* or the *DAQ_Viewer* modules, use a binary format
known as *hdf5*. This format was originally developped to save big volume of datas from large instruments.
Its structure is hierarchical (a bit as folder trees) and one can add metadata to all entries in the tree.
For instance, the data type, shape but also some more complex info such as all the settings related to a
module or a plugin. This gives a unique file containing both datas and metadata.

.. _daq_viewer_saving:

From DAQ_Viewer
---------------

Single Datas
************

Datas saved directly from a DAQ_Viewer (for instance the one on :numref:`det1D`) will be recorded in
a h5file whose structure will be represented
like :numref:`single_data` using PyMoDAQ's h5 browser (see :ref:`H5Browser_module`). The various type
of data exported by the viewer are saved in a dedicated entry (*Data0D*, ...) and all channels are recorded
within as subentries. Metadata from the detector settings, the measurement module and the activated ROIs
are also recorded.

   .. _single_data:

.. figure:: /image/DAQ_Viewer/single_data.png
   :alt: single_data

   h5 file content containing saved data from a DAQ_Viewer detector (see :numref:`det1D`)


.. _continuous_saving:

Continuous Saving
*****************
When the *continuous saving* parameter is set, new parameters are appearing on the *DAQ_Viewer* panel
(see :numref:`figure_continuous`).


* *Base path*: indicates where the data will be saved. If it doesn't exist the module will try to create it
* *Base name*: indicates the base name from which the save file will derive
* *Current Path*: *readonly*, complete path of the saved file
* *Do Save*: Initialize the file and logging can start. A new file is created if clicked again.
* *Compression options*: data can be compressed before saving, using one of the proposed library and the given value of compression [0-9], see *pytables* documentation.

   .. _figure_continuous:

.. figure:: /image/DAQ_Viewer/continuous_saving.png
   :alt: continuous

   Continuous Saving options

.. :download:`png <continuous_saving.png>`


The saved file will follow this general structure:

..

  D:\\Data\\2018\\20181220\\Data_20181220_16_58_48.h5


With a base path (``D:\Data`` in this case) followed by a subfolder year, a subfolder day and a filename
formed from a *base name* followed by the date of the day and the time at which you started to log data.
:numref:`figure_continuous_struct` displays the tree structure of such a file, with

   .. _figure_continuous_struct:

.. figure:: /image/DAQ_Viewer/continuous_data_structure.png
   :alt: continuous

   Continuous Saving options

.. :download:`png <continuous_saving.png>`



.. _daq_scan_saving:

From DAQ_Scan
-------------

DAQ_Scan module will save your data in **datasets**. Each **dataset** is a unique h5 file and may contain multiple scans. The
idea behind this is to have a unique file for a set of related data (the **dataset**) together with all the meta information:
logger data, module parameters (settings, ROI...) even *png* screenshots of the various panels.

:numref:`figure_h5browser_data` displays the content of a typical **dataset** file containing various scans and how each data
and metadata is used by the H5Browser to display the info to the user.

   .. _figure_h5browser_data:

.. figure:: /image/Utils/h5browser_datas.png
   :alt: h5 browser

   h5 browser and arrows to explain how each data or metadata is being displayed


In order to sdave correctly your datas in custom applications, a utility module is to be used: pymodaq.daq_utils.h5saver,
it will save scans and datas following the rules displayed on :numref:`figure_dataset_layout` below:

   .. _figure_dataset_layout:

.. figure:: /image/Utils/dataset_file_layout.PNG
   :alt: File layout

.. :download:`png <dataset_file_layout.png>`

Exploring datas
---------------

h5file saved using PyMoDAQ can be explored using the :ref:`H5Browser_module` utility module. Both datas and metadatas can be explored.