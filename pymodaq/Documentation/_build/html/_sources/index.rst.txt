.. DAQ_Pro_Aquisition documentation master file, created by
   sphinx-quickstart on Mon Apr 16 15:21:28 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyMoDAQ's documentation!
===================================

PyMoDAQ, Modular Data Acquisition with Python, is a set of **python** modules used to perform automated measurements.

It is made for the scientist who need to perform various acquisitions without having to write a user/interface for each new experiment. PyMoDAQ interface is fixed, and any new hardware can be added as a small plugin. Preset modes of a given set of actuators and detectors can be written for easy experiment inititialization.

It is divided in three main modules:

* :ref:`DAQ_Scan_module` : This is the module that will initialize all preset actuators and detectors. Then will automate the data acquisition.
* :ref:`DAQ_Move_module` : used to control/drive an actuator (stand alone and/or automated). Any number of these modules can be instantiated.
* :ref:`DAQ_Viewer_module` : used to control/drive a detector (stand alone and/or automated). Any number of these modules can be instantiated.


GitHub repo: https://github.com/CEMES-CNRS

Documentation: http://pymodaq.cnrs.fr/

Based on the ``pyqtgraph`` library : http://www.pyqtgraph.org by Luke Campagnola.

PyMoDAQ is written by Sébastien Weber: sebastien.weber@cemes.fr under a MIT licence.


.. toctree::
   :maxdepth: 5
   :caption: Contents:

   usage/Installation
   usage/Description
   usage/How_to_start
   usage/SynthesisDiagram
   usage/classDiagram
   usage/APIdoc





Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
