DAQ_Move
========

Introduction
------------

| **The DAQ_Move module is the tool permitting to control hardware move sending axis values by signals.**
| 
| The DAQ_Move contain the float value of movement, in case of Kinesis instrument the angle of the cache.
| It contain also a stepper to automate move with a step value and a number of step.
| The distribution of steps is regular.
| Using the hardware implementation of constructors via the .dll files loaded in the python structure, it permit
	to control precisely parameters of the instruments.
| A first generic class DAQ_Move_base regroup the common attributes to all the instruments given by a tree represented as
	a dictionnary list.
| 

We can find the generic associated methods (redefined in each instrument class with correct .dll instructions) :
	 * **get_position_with_scaling** : get the current position
	 * **set_position_with_scaling** : set the current position
	 * **emit_status** : emit the statut signal to parents
	 * **poll_moving** :
	 * **Move_Done** :
	 * **update_settings** : update local settings from a param_tree_changed signal
	 * **commit_settings** : activate the local hardware updates
	 * **send_param_status** : send to the gui thread the updates parameter values to keep User Interface in date.


A paragraph
-----------


Another paragraph
-----------------