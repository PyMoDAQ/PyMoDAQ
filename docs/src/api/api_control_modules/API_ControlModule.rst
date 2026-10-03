.. py:currentmodule:: pymodaq.control_modules.utils

.. autosummary::

   ControlModule
   HardwareWorkerBase
   pymodaq.control_modules.ui_utils.ControlModuleUI



ControlModule base classes
==========================

Both DAQ_Move and DAQ_Viewer control modules share some specificities and inherit from a base class: the `ControlModule`

.. autoclass:: pymodaq.control_modules.utils::ControlModule
   :members:

The hardware plugin of each control module lives in a separate thread, wrapped in a worker deriving from the
`HardwareWorkerBase` class

.. autoclass:: pymodaq.control_modules.utils::HardwareWorkerBase
   :members:


The same is also true for the UI of these modules sharing a common UI base class: the `ControlModuleUI`

.. autoclass:: pymodaq.control_modules.ui_utils::ControlModuleUI
   :members:




