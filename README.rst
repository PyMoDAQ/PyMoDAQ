PyMoDAQ
#######

.. image:: https://img.shields.io/pypi/v/pymodaq.svg
   :target: https://pypi.org/project/pymodaq/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://codecov.io/gh/CEMES-CNRS/PyMoDAQ/branch/master/graph/badge.svg?token=IQNJRCQDM2
    :target: https://codecov.io/gh/CEMES-CNRS/PyMoDAQ
    
.. image:: https://github.com/CEMES-CNRS/PyMoDAQ/workflows/Python%20package/badge.svg
    :target: https://github.com/CEMES-CNRS/PyMoDAQ/actions?query=workflow%3A%22Python+package%22

.. figure:: http://pymodaq.cnrs.fr/en/latest/_static/splash.png
   :alt: shortcut


PyMoDAQ, Modular Data Acquisition with Python, is a set of **python** modules used to interface any kind of experiments.
It simplifies the interaction with detector and actuator hardware to go straight to the data acquisition of interest.

It has two purposes:

* First, to provide a complete interface to perform automated measurements or logging data without having to write a user/interface for each
  new experiment, this is under the *Dashboard_module* environment and its extensions.
* Second, to provide various tools (modules) to easily build *custom apps*

It is organised a shown below:

.. figure:: http://pymodaq.cnrs.fr/en/latest/_images/pymodaq_diagram.png
   :alt: overview

   PyMoDAQ's Dashboard and its extensions: DAQ_Scan for automated acquisitions, DAQ_Logger for data logging and many other.


* **Dashboard_module** : This is the module that will initialize actuators and detectors given the need of your
  particular experiment. You configure the dashboard using an interface for quick launch of various configurations.
* **DAQ_Logger_module** : This module lets you log data from one or many detectors defined in the dashboard. You can log data
  in a binary hierarchical hdf5 file or towards a sql database
* **DAQ_Scan_module** : This module lets you configure automated data acquisition from one or many detectors defined
  in the dashboard as a function or one or more actuators defined also in the dashboard.

The detectors and the actuators are represented and manipulated using two control modules:

* **DAQ_Move_module** : used to control/drive an actuator (stand alone and/or automated). Any number of these modules can be instantiated.
* **DAQ_Viewer_module** : used to control/drive a detector (stand alone and/or automated). Any number of these modules can be instantiated.

and many others to simplify any application development.

.. raw:: html

    <iframe width="560" height="315" src="https://www.youtube.com/embed/ZdYpQIZHMCY" frameborder="0" allow="accelerometer;
     autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

Published under the CeCILL-B FREE SOFTWARE LICENSE

GitHub repo: https://github.com/CEMES-CNRS

Documentation: http://pymodaq.cnrs.fr/
