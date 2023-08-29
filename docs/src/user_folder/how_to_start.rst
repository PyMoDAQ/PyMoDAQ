  .. _section_how_to_start:

How to Start
============

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Various ways are possible in order to start modules from PyMoDAQ. In all cases after installation of the package
(using ``pip`` or ``setup.py``, see :ref:`section_installation`) all the modules will be installed within the
``site-packages`` folder of python.


  .. _run_module:

From command line tool:
-----------------------
Open a command line and **activate your environment** (if you're using anaconda, miniconda, venv...):

Load installed scripts
**********************

During its installation, a few scripts have been installed within you environment directory, this means you can start
PyMoDAQ's main functionalities directly writing in your console either:

*  ``dashboard``
*  ``daq_scan``
*  ``daq_logger``
*  ``daq_viewer``
*  ``daq_move``
*  ``h5browser``
*  ``plugin_manager``


Execute a given python file
***************************

If you knwow where, within PyMoDAQ directories, is the python file you want to run you can enter for instance:

*  ``python -m pymodaq.dashboard``
*  ``python -m pymodaq.extensions.daq_scan``
*  ``python -m pymodaq.extensions.daq_logger``
*  ``python -m pymodaq.control_modules.daq_viewer``
*  ``python -m pymodaq.control_modules.daq_move``
*  ``python -m pymodaq.extensions.h5browser``
*  ``python -m pymodaq_plugin_manager.manager``

for PyMoDAQ's main modules. The *-m* option tells python to look within its *site-packages* folder (where you've just
installed pymodaq) In fact if one of PyMoDAQ's file (*xxx.py*) as an entry point (a ``if __name__='__main__:'``
statement at the end of the file), you can run it by calling python over it...



Create windows's shortcuts:
---------------------------

See :ref:`shortcut_section` !