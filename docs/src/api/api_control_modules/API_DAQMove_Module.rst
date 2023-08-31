
.. autosummary::

    pymodaq.control_modules.daq_move.DAQ_Move
    pymodaq.control_modules.daq_move.DAQ_Move_Hardware
    pymodaq.control_modules.move_utility_classes.params


The DAQ_Move Class
******************

This documentation highlights the useful entry and output points that you may use in your
applications.

.. autoclass:: pymodaq.control_modules.daq_move::DAQ_Move
   :members: actuator, initialized_state, move_done_bool, get_actuator_value, get_continuous_actuator_value, grab,
    move, move_abs, move_rel, move_home,
    stop_motion, init_hardware_ui, quit_fun, thread_status


The DAQ_Move UI class
*********************

This object is the User Interface of the DAQ_Viewer, allowing easy access to all of the DAQ_Viewer functionnalities
in a generic interface.

.. autoclass:: pymodaq.control_modules.daq_move_ui::DAQ_Move_UI
   :members:


The DAQ_Move Plugin Class
*************************

This object is the base class from which all actuator plugins should inherit. It exposes a few methods, attributes
and signal that could be useful to understand.

.. autoclass:: pymodaq.control_modules.move_utility_classes::DAQ_Move_base
   :members:
