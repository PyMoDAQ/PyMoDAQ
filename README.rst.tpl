PyMoDAQ
#######

.. figure:: http://pymodaq.cnrs.fr/en/latest/_static/splash.png
   :alt: PyMoDAQ Logo

PyMoDAQ (Modular Data Acquisition with Python) is a free and open-source Python framework to control scientific
instruments and acquire data, officially supported by the CNRS. It is a set of **python** modules used to interface any
kind of experiments: cameras, spectrometers, motorized stages, power meters, digitizers... Support for an instrument
comes from small plugins (``pip install pymodaq_plugins_<name>``).

With PyMoDAQ you can:

- drive detectors and actuators from a graphical Dashboard, without writing any interface
- see data of any dimension (a value, a waveform, an image, a hyperspectral cube) live, whatever the instrument
- scan actuators while acquiring data, log signals, lock a parameter with a feedback loop, optimize...
- save everything, with axes and units, in HDF5 files
- control the same instruments from a Python script or a remote computer
- write the plugin of a new instrument in a few dozen lines

Start with the `common questions <https://pymodaq.cnrs.fr/en/latest/user_folder/common_questions.html>`_ or see how
PyMoDAQ `compares with other tools <https://pymodaq.cnrs.fr/en/latest/user_folder/alternatives.html>`_ (PyVISA, PyMeasure,
QCoDeS, NOMAD CAMELS, Bluesky...).


This is the main repository README. Below are links to the README files for each one of the five individual packages:

Packages
--------

- `PyMoDAQ <packages/pymodaq/README.rst>`_ the main software
- `pymodaq_gui <packages/pymodaq_gui/README.rst>`_ providing qt-based tools to build PyMoDAQ-like GUIs
- `pymodaq_data <packages/pymodaq_data/README.rst>`_  providing tools to manage data obtained by PyMoDAQ (but not only)
- `pymodaq_utils <packages/pymodaq_utils/README.rst>`_ providing utilities used by the other packages
- `pymodaq_scripting <packages/pymodaq_scripting/README.rst>`_ providing utilities used to communicate with a DashBoard form a script in another process


Each package directory can be navigated to for more detailed information about its goal. A link to the official documentation is also provided at the end of each README.


Requirements
--------

PyMoDAQ supports Python versions that are still considered `alive <https://devguide.python.org/versions/>`_ (not end-of-life per the Python devguide) and have been released for at least a year. Other python versions may still work but we cannot guarantee it.
For now, this reflects into testing support for Python 3.10 - 3.13


We usually recommend to use the python distribution that left or will soon leave bugfix status: python 3.12-3.13

Published under the MIT FREE SOFTWARE LICENSE

GitHub repo: https://github.com/PyMoDAQ

Documentation: http://pymodaq.cnrs.fr/
