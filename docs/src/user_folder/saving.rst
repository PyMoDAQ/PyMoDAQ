(to be removed)

.. _saving_doc:


.. _daq_scan_saving:

From DAQ_Scan
-------------

DAQ_Scan module will save your data in **datasets**. Each **dataset** is a unique h5 file and may contain multiple scans. The
idea behind this is to have a unique file for a set of related data (the **dataset**) together with all the meta information:
logger data, module parameters (settings, ROI...) even *png* screenshots of the various panels.

:numref:`figure_h5browser_data` displays the content of a typical **dataset** file containing various scans and how each data
and metadata is used by the H5Browser to display the info to the user.

   .. _figure_h5browser_data:

.. figure:: /image/Utils/h5browser_datas.PNG
   :alt: h5 browser

   h5 browser and arrows to explain how each data or metadata is being displayed


In order to save correctly your datas in custom applications, a utility module is to be used: pymodaq.utils.h5saver,
it will save scans and datas following the rules displayed on :numref:`figure_dataset_layout` below:

   .. _figure_dataset_layout:

.. figure:: /image/Utils/dataset_file_layout.PNG
   :alt: File layout

.. :download:`png <dataset_file_layout.png>`
