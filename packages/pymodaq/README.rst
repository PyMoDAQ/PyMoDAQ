.. ############################################################
..  WARNING: This file is AUTO-GENERATED from README.rst.tpl.
..                  ⚠️ DO NOT EDIT MANUALLY ⚠️
.. ############################################################


PyMoDAQ
#######

.. image:: https://img.shields.io/pypi/v/pymodaq.svg
   :target: https://pypi.org/project/pymodaq/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://codecov.io/gh/PyMoDAQ/PyMoDAQ/graph/badge.svg?token=IQNJRCQDM2
 :target: https://codecov.io/gh/PyMoDAQ/PyMoDAQ



+-------------+-------------------+------------------+---------------------+
|  Linux      | PyQt5             | PyQt6            | PySide6             |
+=============+===================+==================+=====================+
| Python 3.9  | |39-linux-pyqt5|  | |39-linux-pyqt6| | |39-linux-pyside6|  |
+-------------+-------------------+------------------+---------------------+
| Python 3.10 | |310-linux-pyqt5| ||310-linux-pyqt6| | |310-linux-pyside6| |
+-------------+-------------------+------------------+---------------------+
| Python 3.11 | |311-linux-pyqt5| ||311-linux-pyqt6| | |311-linux-pyside6| |
+-------------+-------------------+------------------+---------------------+
| Python 3.12 | |312-linux-pyqt5| ||312-linux-pyqt6| | |312-linux-pyside6| |
+-------------+-------------------+------------------+---------------------+


.. |39-linux-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.9_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |39-linux-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.9_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |39-linux-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.9_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |310-linux-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.10_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |310-linux-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.10_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |310-linux-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.10_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |311-linux-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.11_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |311-linux-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.11_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |311-linux-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.11_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |312-linux-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.12_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |312-linux-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.12_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |312-linux-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Linux_3.12_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml


+-------------+---------------------+--------------------+-----------------------+
|  Windows    | PyQt5               | PyQt6              | PySide6               |
+=============+=====================+====================+=======================+
| Python 3.9  | |39-windows-pyqt5|  | |39-windows-pyqt6| | |39-windows-pyside6|  |
+-------------+---------------------+--------------------+-----------------------+
| Python 3.10 | |310-windows-pyqt5| ||310-windows-pyqt6| | |310-windows-pyside6| |
+-------------+---------------------+--------------------+-----------------------+
| Python 3.11 | |311-windows-pyqt5| ||311-windows-pyqt6| | |311-windows-pyside6| |
+-------------+---------------------+--------------------+-----------------------+
| Python 3.12 | |312-windows-pyqt5| ||312-windows-pyqt6| | |312-windows-pyside6| |
+-------------+---------------------+--------------------+-----------------------+

.. |39-windows-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.9_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |39-windows-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.9_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |39-windows-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.9_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |310-windows-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.10_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |310-windows-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.10_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |310-windows-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.10_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |311-windows-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.11_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |311-windows-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.11_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |311-windows-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.11_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |312-windows-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.12_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |312-windows-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.12_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml

.. |312-windows-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq/5.1.x/tests_Windows_3.12_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-pymodaq.yml




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

The main component is the **Dashboard** : This is a graphical component that will initialize actuators and detectors given
the need of your particular experiment. You configure the dashboard using an interface for quick launch of various
configurations (numbers and types of control modules).

The detectors and the actuators are represented and manipulated using two control modules:

* **DAQ_Move_module** : used to control/drive an actuator (stand alone and/or automated).
  Any number of these modules can be instantiated in the Dashboard
* **DAQ_Viewer_module** : used to control/drive a detector (stand alone and/or automated).

Any number of these modules can be instantiated in the Dashboard.

The Dashboard allows you to start dedicated extensions that will make use of the control modules:

* **DAQ_Logger_module** : This module lets you log data from one or many detectors defined in the dashboard. You can log data
  in a binary hierarchical hdf5 file or towards a sql database
* **DAQ_Scan_module** : This module lets you configure automated data acquisition from one or many detectors defined
  in the dashboard as a function or one or more actuators defined also in the dashboard.

and many others to simplify any application development.

Published under the MIT FREE SOFTWARE LICENSE

GitHub repo: https://github.com/PyMoDAQ

Documentation: http://pymodaq.cnrs.fr/
