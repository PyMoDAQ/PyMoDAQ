.. ############################################################
..  WARNING: This file is AUTO-GENERATED from README.rst.tpl.
..                  ⚠️ DO NOT EDIT MANUALLY ⚠️
.. ############################################################


PyMoDAQ Data
############

.. image:: https://img.shields.io/pypi/v/pymodaq_data.svg
   :target: https://pypi.org/project/pymodaq_data/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://codecov.io/gh/PyMoDAQ/pymodaq_data/branch/5.0.x_dev/graph/badge.svg?token=H32JflMEYR 
 :target: https://codecov.io/gh/PyMoDAQ/pymodaq_data

+-------------+-------------+---------------+
|             | Linux       | Windows       |
+=============+=============+===============+
| Python 3.9  | |39-linux|  | |39-windows|  |
+-------------+-------------+---------------+
| Python 3.10 | |310-linux| | |310-windows| |
+-------------+-------------+---------------+
| Python 3.11 | |311-linux| | |311-windows| |
+-------------+-------------+---------------+
| Python 3.12 | |312-linux| | |312-windows| |
+-------------+-------------+---------------+




.. |39-linux| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_data/5.1.x/tests_Linux_3.9.svg
    :target: https://github.com/PyMoDAQ/pymodaq_data/actions/workflows/tests-data.yml

.. |310-linux| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_data/5.1.x/tests_Linux_3.10.svg
    :target: https://github.com/PyMoDAQ/pymodaq_data/actions/workflows/tests-data.yml

.. |311-linux| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_data/5.1.x/tests_Linux_3.11.svg
    :target: https://github.com/PyMoDAQ/pymodaq_data/actions/workflows/tests-data.yml

.. |312-linux| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_data/5.1.x/tests_Linux_3.12.svg
    :target: https://github.com/PyMoDAQ/pymodaq_data/actions/workflows/tests-data.yml

.. |39-windows| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_data/5.1.x/tests_Windows_3.9.svg
    :target: https://github.com/PyMoDAQ/pymodaq_data/actions/workflows/tests-data.yml

.. |310-windows| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_data/5.1.x/tests_Windows_3.10.svg
    :target: https://github.com/PyMoDAQ/pymodaq_data/actions/workflows/tests-data.yml

.. |311-windows| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_data/5.1.x/tests_Windows_3.11.svg
    :target: https://github.com/PyMoDAQ/pymodaq_data/actions/workflows/tests-data.yml

.. |312-windows| image:: https://raw.githubusercontent.com/PyMoDAQ/PyMoDAQ/badges/pymodaq_data/5.1.x/tests_Windows_3.12.svg
    :target: https://github.com/PyMoDAQ/pymodaq_data/actions/workflows/tests-data.yml




.. figure:: http://pymodaq.cnrs.fr/en/latest/_static/splash.png
   :alt: shortcut


PyMoDAQ__, Modular Data Acquisition with Python, is a set of **python** modules used to interface any kind of
experiments. It simplifies the interaction with detector and actuator hardware to go straight to the data acquisition
of interest.

__ https://pymodaq.readthedocs.io/en/stable/?badge=latest

`PyMoDAQ data`__ is a set of utilities (constants, methods and classes) that are used
for Data Management. It is heavily used with the PyMoDAQ framework but can also be used as a standalone
package for data management in another context.

__ https://pymodaq.cnrs.fr/en/latest/developer_folder/data_management.html

What are Data?
--------------

Data are objects with many characteristics able to properly describe real data taken on an experiment
or calculated from theory:


*  a type: float, int, ...
*  a dimensionality: Data0D, Data1D, Data2D and higher
*  units (dealt with the pint python package)
*  axes
*  actual data as numpy arrays
*  uncertainty/error bars
* ...


.. figure:: https://pymodaq.cnrs.fr/en/latest/_images/data.png

   What is PyMoDAQ's data?.

The `PyMoDAQ Data` package
--------------------------

Because of this variety, `PyMoDAQ Data` introduce a set of objects including metadata (for instance the time of
acquisition) and various methods and properties to manipulate
them during analysis for instance (getting name, slicing, concatenating...),
save them and plot them (given you installed one of the available backend: *matplotlib* or *Qt* (
through the `pymodaq_gui` package)

To learn more, check the documentation__.

__ https://pymodaq.cnrs.fr/en/latest/data_management.html


Published under the MIT FREE SOFTWARE LICENSE

GitHub repo: https://github.com/PyMoDAQ

Documentation: http://pymodaq.cnrs.fr/
