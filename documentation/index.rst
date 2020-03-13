.. DAQ_Pro_Aquisition documentation master file, created by
   sphinx-quickstart on Mon Apr 16 15:21:28 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyMoDAQ's documentation!
===================================

Announcement: Training session in Toulouse, France 22/23/24 Juin 2020:

   .. _flyer:

.. figure:: /image/Flyer_PyMoDAQ.png
   :alt: Flyer_femto

   Training session announcement

PyMoDAQ, Modular Data Acquisition with Python, is a set of **python** modules used to interface any kind of experiments.
It simplifies the interaction with detector and actuator hardware to go straight to the data acquisition of interest.

It has two purposes:

* First, to provide a complete interface to perform automated measurements or logging data without having to write a user/interface for each
  new experiment, this is under the :ref:`Dashboard_module` environment and its two extensions.
* Second, to provide various tools (modules) to easily build a :ref:`custom_app`

It is divided in three main modules:

* :ref:`Dashboard_module` : This is the module that will initialize actuators and detectors given the need of your
  particular experiment. You configure the dashboard using an interface for quick launch of various configurations.
* :ref:`DAQ_Logger_module` : This module lets you log data from one or many detectors defined in the dashboard. You can log data
  in a binary hierarchical hdf5 file or towards a sql database
* :ref:`DAQ_Scan_module` : This module lets you configure automated data acquisition from one or many detectors defined
  in the dashboard as a function or one or more actuators defined also in the dashboard.

The detectors and the actuators are represented and manipulated using two generic modules:

* :ref:`DAQ_Move_module` : used to control/drive an actuator (stand alone and/or automated). Any number of these modules can be instantiated.
* :ref:`DAQ_Viewer_module` : used to control/drive a detector (stand alone and/or automated). Any number of these modules can be instantiated.

and many others to simplify any application development.

Information
***********

GitHub repo: https://github.com/CEMES-CNRS

Documentation: http://pymodaq.cnrs.fr/

List of available plugins: https://docs.google.com/spreadsheets/d/1wfMfvLwTitZd2R2m1O5i6wVEaX1lJBahP2HUbxVdidg

Based on the ``pyqtgraph`` library : http://www.pyqtgraph.org by Luke Campagnola.

PyMoDAQ is written by Sébastien Weber: sebastien.weber@cemes.fr under a CeCILL-B license.

PDF version of this documentation: http://pymodaq.cnrs.fr/_static/PyMoDAQ.pdf

Contribution
************

If you want to contribute see this page: :ref:`contributors`


They use it
***********
See :ref:`feedback`


Citation
********

By using PyMoDAQ, you are being asked to cite it (this website) when publishing results obtained with the help of its interface.
In that way, you're also helping in its promotion and amelioration.

Changelog
*********

Please see :doc:`the changelog </changelog>`.

.. toctree::
   :maxdepth: 5
   :caption: Contents:

   usage/Features
   usage/Installation
   usage/How_to_start
   usage/Description
   usage/CustomApp
   usage/tcpip
   usage/Feedback
   usage/Contributors
   usage/APIdoc

..   usage/classDiagram
   usage/APIdoc



Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
