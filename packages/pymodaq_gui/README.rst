.. ############################################################
..  WARNING: This file is AUTO-GENERATED from README.rst.tpl.
..                  ⚠️ DO NOT EDIT MANUALLY ⚠️
.. ############################################################


PyMoDAQ GUI
###########

.. image:: https://img.shields.io/pypi/v/pymodaq_gui.svg
   :target: https://pypi.org/project/pymodaq_gui/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=dev
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=dev
   :alt: Documentation Status

.. image:: https://codecov.io/gh/PyMoDAQ/PyMoDAQ/branch/dev/graph/badge.svg?token=IQNJRCQDM2 
 :target: https://codecov.io/gh/PyMoDAQ/PyMoDAQ


+-------------+--------------------------+--------------------------+
|  Linux      | PyQt6                    | PySide6                  |
+=============+==========================+==========================+
| Python 3.11 | |311-linux-pyqt6| \*     | |311-linux-pyside6|      |
+-------------+--------------------------+--------------------------+
| Python 3.12 | |312-linux-pyqt6|        | |312-linux-pyside6| \*   |
+-------------+--------------------------+--------------------------+
| Python 3.13 | |313-linux-pyqt6|        | |313-linux-pyside6|      |
+-------------+--------------------------+--------------------------+
| Python 3.14 | |314-linux-pyqt6| \*     | |314-linux-pyside6|      |
+-------------+--------------------------+--------------------------+



.. |311-linux-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.11_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |311-linux-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.11_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |311-linux-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.11_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |312-linux-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.12_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |312-linux-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.12_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |312-linux-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.12_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |313-linux-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.13_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |313-linux-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.13_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |314-linux-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.14_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |313-linux-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.13_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |314-linux-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Linux_3.14_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

+-------------+--------------------------+--------------------------+
|  Windows    | PyQt6                    | PySide6                  |
+=============+==========================+==========================+
| Python 3.11 | |311-windows-pyqt6|      | |311-windows-pyside6|    |
+-------------+--------------------------+--------------------------+
| Python 3.12 | |312-windows-pyqt6| \*   | |312-windows-pyside6|    |
+-------------+--------------------------+--------------------------+
| Python 3.13 | |313-windows-pyqt6|      | |313-windows-pyside6|    |
+-------------+--------------------------+--------------------------+
| Python 3.14 | |314-windows-pyqt6|      | |314-windows-pyside6|    |
+-------------+--------------------------+--------------------------+

\* Combinations marked with a star are tested at each push and pull request. All the others are tested only
weekly (every Sunday) and on manual dispatch, so their badges can be up to a week old. PyQt5 is no longer tested.


.. |311-windows-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.11_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |311-windows-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.11_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |311-windows-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.11_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |312-windows-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.12_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |312-windows-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.12_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |312-windows-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.12_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |313-windows-pyqt5| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.13_pyqt5.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |313-windows-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.13_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |314-windows-pyqt6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.14_pyqt6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |313-windows-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.13_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. |314-windows-pyside6| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_gui/dev/tests_Windows_3.14_pyside6.svg
    :target: https://github.com/PyMoDAQ/PyMoDAQ/actions/workflows/tests-gui.yml

.. figure:: http://pymodaq.cnrs.fr/en/latest/_static/splash.png
   :alt: shortcut

PyMoDAQ__ (Modular Data Acquisition with Python) is a free and open-source Python framework to control scientific
instruments (cameras, spectrometers, motorized stages, power meters, digitizers...) and acquire data, from a
graphical Dashboard or from scripts, with live data viewers, scans, logging and saving in HDF5 files. This package, ``pymodaq_gui``, is its Qt based toolkit of graphical components.

__ https://pymodaq.cnrs.fr/en/latest/

`PyMoDAQ GUI` is a set of utilities (constants, methods and classes) and graphical components
based on the Qt framework that are used to create high level user interfaces.

It contains both simple components to create GUI but also high level ones, for instance to display data objects
such as the one generated using the `pymodaq_data` package.


For instance, you'll find data viewers available out of the box:

.. figure:: https://pymodaq.cnrs.fr/en/latest/_images/data_femto_fs.png

    Specific GUI component to view and manipulate 2D data.



Published under the MIT FREE SOFTWARE LICENSE

GitHub repo: https://github.com/PyMoDAQ

Homepage and documentation: https://pymodaq.cnrs.fr/en/latest/
