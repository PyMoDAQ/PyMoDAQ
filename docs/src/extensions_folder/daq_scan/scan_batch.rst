.. _scan_batch:

Scan Batch Manager
------------------

If the *Scan Batch Manager* is activated, a new menu entry will appear: *Batch Configs*, that let the user
define, modify or load scan batch configurations. When loaded, a particular configuration will
be displayed in the batch window. This window (see :numref:`scanbatch`) displays (in a tree) a list of scans to perform.
Each scan is defined by a set of actuators/detectors to use and scan settings (*Scan1D*, *Linear*... just as described in
:ref:`settings_paragraph`).

   .. _scanbatch:

.. figure:: /image/DAQ_Scan/scanbatch.png
   :alt: scanbatch

   An example of a Scan Batch configuration displaying several scans to perform

A new start button |startbatch| will also appear on the main window to start the currently loaded
scan batch.

.. |startbatch| image:: /image/DAQ_Scan/start_scanbatch.PNG
    :width: 20pt
    :height: 20pt