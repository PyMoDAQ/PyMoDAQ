PyMoDAQ
#######

.. image:: https://img.shields.io/pypi/v/pymodaq.svg
   :target: https://pypi.org/project/pymodaq/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://codecov.io/gh/PyMoDAQ/PyMoDAQ/branch/pymodaq-dev/graph/badge.svg?token=IQNJRCQDM2
    :target: https://codecov.io/gh/PyMoDAQ/PyMoDAQ

====== ========== ======= ======
Python Qt Backend OS      Passed
====== ========== ======= ======
3.8    Qt5        Linux   |38Qt5|
3.9    Qt5        Linux   |39Qt5|
3.10   Qt5        Linux   |310Qt5|
3.11   Qt5        Linux   |311Qt5|
3.8    Qt5        Windows |38Qt5win|
3.8    PySide2    Linux   |38pyside|
3.9    Qt6        Linux   |39Qt6|
====== ========== ======= ======


.. |38Qt5| image:: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp38pyqt5.yml/badge.svg?branch=pymodaq-dev
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp38pyqt5.yml

.. |39Qt5| image:: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp39pyqt5.yml/badge.svg?branch=pymodaq-dev
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp39pyqt5.yml

.. |310Qt5| image:: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp310pyqt5.yml/badge.svg?branch=pymodaq-dev
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp310pyqt5.yml

.. |311Qt5| image:: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp311pyqt5.yml/badge.svg?branch=pymodaq-dev
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp311pyqt5.yml

.. |38Qt5win| image:: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp38pyqt5_win.yml/badge.svg?branch=pymodaq-dev
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp38pyqt5_win.yml

.. |38pyside| image:: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp38pyside2.yml/badge.svg?branch=pymodaq-dev
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp38pyside2.yml

.. |39Qt6| image:: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp39pyqt6.yml/badge.svg?branch=pymodaq-dev
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/Testp39pyqt6.yml



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
