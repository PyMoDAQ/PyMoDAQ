  .. _section_how_to_start:

How to Start
============

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Various ways are possible in order to start modules from PyMoDAQ. In all cases after installation of the package
(using ``pip`` or ``setup.py``, see :ref:`section_installation`) all the modules will be installed within the ``site-packages`` folder of python. ``.exe``
files will also be installed in the directory: ``C:\WPy-3710\python-3.7.1.amd64\Scripts`` however they will be usable only if:

1. you manually installed PyMoDAQ (using the  ``python setup.py install`` command)
2. you installed with pip **and** the ``python.exe`` program is in windows ``PATH`` (add ``C:\WPy-3710\python-3.7.1.amd64`` in the ``PATH`` environment variable)

Using installed .exe files as shortcuts:
----------------------------------------

If one of the conditions above is satisfied you can run (from the directory: ``C:\WPy-3710\python-3.7.1.amd64\Scripts``)

* pymodaq_scan.exe : will start the :ref:`DAQ_Scan_module` module
* pymodaq_move.exe : will start a standalone :ref:`DAQ_Move_module` module
* pymodaq_viewer.exe : will start a standalone :ref:`DAQ_Viewer_module` module
* pymodaq_h5browser.exe : will start a standalone :ref:`H5Browser_module` module (to explore h5 files saved from DAQ_Scan or DAQ_Viewer modules)

and you can even even create shortcuts on the desktop (see :numref:`fig_create_shortcut`)

   .. _fig_create_shortcut:

.. figure:: /image/create_shortcut.png
   :alt: create shortcut
   :scale: 100%

   Creating a shortcut from an .exe file


.. _cmdtool_exec:

From command line tool:
-----------------------

Run Winpython (or Anaconda) command line tool (``C:\WPy-3710\WinPython Command Prompt.exe``) and execute either:

*  ``C:\WPy-3710\scripts\pymodaq_scan``
*  ``C:\WPy-3710\scripts\pymodaq_viewer``
*  ``C:\WPy-3710\scripts\pymodaq_move``
*  ``C:\WPy-3710\scripts\pymodaq_h5browser``


Run any module:
---------------

If one of PyMoDAQ's module as an entry point (a ``if __name__='__main__:'`` statement at the end of the script), you can run it with:

*  ``C:\WPy-3710\scripts\python -m pymodaq.daq_scan.daq_scan_main``
*  ``C:\WPy-3710\scripts\python -m pymodaq.daq_viewer.daq_viewer_main``
*  ``C:\WPy-3710\scripts\python -m pymodaq.daq_move.daq_move_main``
*  ``C:\WPy-3710\scripts\python -m pymodaq.daq_utils.h5browser``

etc...

Create a batch/bash file for quick use:
---------------------------------------

Any command line execution can be written (on windows) in a ``.bat`` file, so that when you double click it all text lines within will execute.
For instance, one could write:

..

  |  ``cd C:\WPy-3710\python-3.7.1.amd64``
  |  ``C:\WPy-3710\python-3.7.1.amd64\Scripts\pymodaq_scan``

This will simulate the content of :ref:`cmdtool_exec`, while Python is not registered on windows ``PATH``.
**This is by far the most convenient way for user to start the application** (even if it requires some preparation from the guy installing the package...)