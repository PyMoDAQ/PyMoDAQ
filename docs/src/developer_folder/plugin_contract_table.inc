Actuator (``DAQ_Move_base``)
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 12 48 20

   * - Method
     - Required
     - When it is called, what it does
     - Returns
   * - ``ini_attributes``
     - no
     - called first, in the constructor: declare the attributes (type hints, ``self.controller = None``)
     - 
   * - ``ini_stage``
     - yes
     - initialize the communication when the actuator is initialized; if ``self.is_master`` create the controller, otherwise use the ``controller`` argument (shared with the master)
     - ``(info: str, initialized: bool)``
   * - ``get_actuator_value``
     - yes
     - read the current position from the hardware, on request and after each move
     - a ``DataActuator`` with units (or a float if ``data_actuator_type`` is ``float``)
   * - ``move_abs``
     - yes
     - move to an absolute value (a ``DataActuator``, in the units of the axis)
     - 
   * - ``move_rel``
     - yes
     - move by a relative value (a ``DataActuator``, in the units of the axis)
     - 
   * - ``move_home``
     - no
     - send the actuator to its home position
     - 
   * - ``stop_motion``
     - no
     - stop the motion now; the default does nothing
     - 
   * - ``commit_settings``
     - no
     - a setting of the tree changed in the UI: send it to the hardware
     - 
   * - ``close``
     - yes
     - release the hardware (safe state, close the communication)
     - 

Detector (``DAQ_Viewer_base``)
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 12 48 20

   * - Method
     - Required
     - When it is called, what it does
     - Returns
   * - ``ini_attributes``
     - no
     - called first, in the constructor: declare the attributes (type hints, ``self.controller = None``)
     - 
   * - ``ini_detector``
     - yes
     - initialize the communication when the detector is initialized; if ``self.is_master`` create the controller, otherwise use the ``controller`` argument (shared with the master)
     - ``(info: str, initialized: bool)``
   * - ``grab_data``
     - yes
     - start an acquisition (``Naverage`` averages); send the data with ``self.dte_signal.emit`` (or ``dte_signal_temp``) as a ``DataToExport`` with axes and units
     - 
   * - ``stop``
     - yes
     - stop the acquisition in progress
     - 
   * - ``commit_settings``
     - no
     - a setting of the tree changed in the UI: send it to the hardware
     - 
   * - ``close``
     - yes
     - release the hardware (safe state, close the communication)
     - 

