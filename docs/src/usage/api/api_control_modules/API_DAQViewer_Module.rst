.. py:currentmodule:: pymodaq.control_modules.daq_viewer

Summary of the classes dealing with the DAQ_Viewer control module:

.. autosummary::

   DAQ_Viewer
   DAQ_Detector
   DAQ_Viewer_UI


DAQ_Viewer class
****************

This documentation highlights the useful entry and output points that you may use in your applications.

.. autoclass:: pymodaq.control_modules.daq_viewer::DAQ_Viewer
   :members:
   :show-inheritance:

DAQ_Detector class
******************
The Detector class is an object leaving in the plugin thread and responsible for the communication between DAQ_Viewer
and the plugin itself

.. autoclass:: pymodaq.control_modules.daq_viewer::DAQ_Detector
   :members:


The Viewer UI class
*******************

This object is the User Interface of the DAQ_Viewer, allowing easy access to all of the DAQ_Viewer functionnalities
in a generic interface.

.. autoclass:: pymodaq.control_modules.daq_viewer_ui::DAQ_Viewer_UI
   :members:
