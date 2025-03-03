  .. _section_backup_environments:

Environment backups
===================

PyMoDAQ keeps track of your virtual environment packages and save pip-compatible backups that can be used to transfer or to revert
to a working environment

A new environment is kept only if different from the last backup. The oldest ones are deleted, according to the 
*limit* value kept in the configuration. Three parameters controlling backups are defined in the configuration file:

.. code-block:: toml

   	...
	[backup]
	keep_backup = true        # should PyMoDAQ keep backups of environments' installed packages?
	folder = "environments"   # where to keep the backup (relative to local config path)
	limit = 25                # how many to keep (maximum)
	...

These backups files are saved in PyMoDAQ's local configuration folder, using the general following path:

``/home/<username>/.pymodaq/<folder value from config>/<environment_name>``


Backup structure
----------------
Backup files are structured in a simple way to be compatible with pip, but start with two commented lines to provide additional information:

* the first one is the python executable path used to launch PyMoDAQ
* the second one is the python executable version

For example:

.. code-block::

	# executable: /home/mairain/.virtualenvs/pymodaq-dev/bin/python
	# version: 3.12.3 (main, Jan 17 2025, 18:03:48) [GCC 13.3.0]

	PySide6==6.8.1
	PySide6_Addons==6.8.1
	PySide6_Essentials==6.8.1
	...


The filename also gives information about when a backup was created by being named using the following pattern ``<year><month><day><hour><minute><second>_environment.txt``. 
It is therefore not recommended to rename backup files, as it may mess up ranking them by creation date.

A backup created on January 31rd 2025 at 11:24:05 would be ``20250131112405_environment.txt``


Restore or transfer a working environment
------------------------------------------

If PyMoDAQ doesn't start after updating/modifying the packages in your virtual environment, or if you want to transfer a working
environment, you can try using a backup to install. Using ``mamba``, and a backup file declaring python version ``3.12.3``:

* Create a new environment using the same python version as the one in your backup file ``mamba create -n pymodaq_newenv python=3.12.3``
* Activate the environment ``mamba activate pymodaq_newenv``
* Install packages from the backup file ``pip install -r 20250131112405_environment.txt``
* Call the ``dashboard`` command, it should open PyMoDAQ dashboard
