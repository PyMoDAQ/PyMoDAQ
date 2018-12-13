Installation
============

.. contents::
   :depth: 1
   :local:
   :backlinks: none

.. highlight:: console

Overview
--------
PyMoDAQ is written in `Python`__ and uses Python 3.5+. It uses the `PyQt5`__ library and the excellent `pyqtgraph`__ package for its user interface. For PyMoDAQ to run smoothly, you need a Python distribution to be installed. Here are some advices.

__ https://docs.python-guide.org/
__ http://doc.qt.io/qt-5/qt5-intro.html
__ http://www.pyqtgraph.org/

Windows
-------
The advised distribution is `WinPython`__ that comes with a full set of python packages for a versatile use of python. Once the distribution installed, you can install PyMoDAQ from the folder downloaded on github (and soon from pypi).
::

   C:\...\PyMoDAQ\python setup.py install

and then to run:
::

   C:\...\PyMoDAQ\DAQ_Scan\python DAQ_scan_main.py


__ https://winpython.github.io/


MacOS
-----
The advised distribution is `Anaconda`__ that comes with a full set of python packages for a versatile use of python. Once the distribution installed, you can install PyMoDAQ from the folder downloaded on github (and soon from pypi).
::

   $ ~/.../PyMoDAQ/python setup.py install

and then to run:

::

   ~/.../PyMoDAQ/DAQ_Scan/python DAQ_scan_main.py

__ https://www.anaconda.com/download/



Linux
-----
The advised distribution is `Anaconda`__ that comes with a full set of python packages for a versatile use of python. Once the distribution installed, you can install PyMoDAQ from the folder downloaded on github (and soon from pypi).
::

   $ ~/.../PyMoDAQ/python setup.py install

and then to run:
::

   ~/.../PyMoDAQ/DAQ_Scan/python DAQ_scan_main.py


__ https://www.anaconda.com/download/#linux
