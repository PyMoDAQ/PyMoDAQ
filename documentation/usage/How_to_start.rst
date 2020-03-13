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

Open a command line and activate your environment (if you're using anaconda or miniconda) and execute either:

*  ``python -m pymodaq.dashboard``
*  ``python -m pymodaq.daq_viewer.daq_viewer_main``
*  ``python -m pymodaq.daq_move.daq_move_main``
*  ``python -m pymodaq.daq_utils.h5browser``

for PyMoDAQ's main modules. The *-m* option tells python to look within its *site-packages* folder (where you've just
installed pymodaq) In fact if one of PyMoDAQ's file (*xxx.py*) as an entry point (a ``if __name__='__main__:'``
statement at the end of the file), you can run it by calling python over it...



Create windows's shortcuts:
---------------------------

See :ref:`shortcut_section` !