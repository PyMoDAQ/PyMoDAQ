  .. _section_installation:

Installation
============

.. contents::
   :depth: 1
   :local:
   :backlinks: none

.. highlight:: console

Overview
--------
PyMoDAQ is written in `Python`__ and uses Python 3.5+. It uses the `PyQt5`__ library and the excellent `pyqtgraph`__ package
for its user interface. For PyMoDAQ to run smoothly, you need a Python distribution to be installed. Here are some advices.

__ https://docs.python-guide.org/
__ http://doc.qt.io/qt-5/qt5-intro.html
__ http://www.pyqtgraph.org/

Windows
-------

The advised distribution is `WinPython`__ (WinPython64-3.7.1.0 tested to be working) that comes with a full set of python
packages for a versatile use of python. For best practice, install it on the C drive, for instance: ``C:\WPy-3710`` Once
the distribution installed, you can install PyMoDAQ from the folder downloaded on `github`__ or from `Pypi`__.

__ https://winpython.github.io/
__ https://github.com/CEMES-CNRS/PyMoDAQ
__ https://pypi.org/project/pymodaq/1.0.1/#files

Step by Step manual instructions:
*********************************

* get winpython and install it (choose a destination folder on ``C:\`` directly, for instance ``C:\WPy-3710``
* download the source file from `github`__ or `Pypi`__
* Extract the archive (zip or tar file)
* open Winpython command line tool ``C:\WPy-3710\WinPython Command Prompt.exe``
* cd to the location of the extracted archive: ``cd C:\...\pymodaq\``
* run: ``python setup.py install``

__ https://github.com/CEMES-CNRS/PyMoDAQ
__ https://pypi.org/project/pymodaq/1.0.1/#files


All the modules will then be installed within the ``site-packages`` folder of python. ``.exe`` files will also be installed
in the directory: ``C:\WPy-3710\python-3.7.1.amd64\Scripts`` so that you can run directly:

* pymodaq_scan.exe : will start the :ref:`DAQ_Scan_module` module
* pymodaq_move.exe : will start a standalone :ref:`DAQ_Move_module` module
* pymodaq_viewer.exe : will start a standalone :ref:`DAQ_Viewer_module` module
* pymodaq_h5browser.exe : will start a standalone :ref:`H5Browser_module` module (to explore h5 files saved from DAQ_Scan or DAQ_Viewer modules)

and even create a shortcut on the desktop (see :numref:`fig_create_shortcut`)

   .. _fig_create_shortcut:

.. figure:: /image/create_shortcut.png
   :alt: create shortcut
   :scale: 100%

   Creating a shortcut from an .exe file

Using Pip:
**********

Pymodaq can be downloaded and installed automatically using the command line tool: ``pip``

* get winpython and install it (choose a destination folder on ``C:\`` directly, for instance ``C:\WPy-3710``
* open Winpython command line tool ``C:\WPy-3710\WinPython Command Prompt.exe``
* write the command: ``C:\WPy-3710\scripts\pip install pymodaq``

All the modules will then be installed within the ``site-packages`` folder of python. However the ``.exe`` files will not be executable
so look at :ref:`section_how_to_start` for detailed ways of how to start pymodaq modules.

MacOS
-----
The advised distribution is `Anaconda`__ that comes with a full set of python packages for a versatile use of python.
Once the distribution installed, you can follow the Windows instructions above (but using anaconda command line).


__ https://www.anaconda.com/download/



Linux
-----
The advised distribution is `Anaconda`__ that comes with a full set of python packages for a versatile use of python.
Once the distribution installed, you can follow the Windows instructions above (but using anaconda command line).


__ https://www.anaconda.com/download/



