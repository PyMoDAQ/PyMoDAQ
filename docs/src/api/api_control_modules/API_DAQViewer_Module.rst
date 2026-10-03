.. py:currentmodule:: pymodaq.control_modules.daq_viewer

Summary of the classes dealing with the DAQ_Viewer control module:

.. autosummary::

   DAQ_Viewer
   DetectorWorker
   pymodaq.control_modules.daq_viewer_ui.ui_base.DAQ_Viewer_UI


DAQ_Viewer class
****************

This documentation highlights the useful entry and output points that you may use in your applications.

.. autoclass:: pymodaq.control_modules.daq_viewer::DAQ_Viewer
   :members:
   :show-inheritance:

DetectorWorker class
********************
The DetectorWorker class is an object living in the plugin thread and responsible for the communication between DAQ_Viewer
and the plugin itself

.. autoclass:: pymodaq.control_modules.daq_viewer::DetectorWorker
   :members:


The Viewer UI class
*******************

This object is the User Interface of the DAQ_Viewer, allowing easy access to all of the DAQ_Viewer functionnalities
in a generic interface.

.. autoclass:: pymodaq.control_modules.daq_viewer_ui.ui_base::DAQ_Viewer_UI
   :members:
