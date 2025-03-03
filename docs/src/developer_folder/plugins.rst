.. _plugins:

Plugins
=======

A :term:`plugin` is a python package whose name is of the type: *pymodaq_plugins_apluginname* containing functionalities
to be added to PyMoDAQ

.. note::
    A plugin may contains added functionalities such as:

    * **Classes to add a given instrument**: allows a given instrument to be added programmatically
      in a :ref:`control_modules` graphical interface
    * **Instrument drivers** located in a `hardware` folder: contains scripts/classes to ease communication
      with the instrument. Could be third party packages such as Pymeasure
    * **PID models** located in a `models` folder: scripts and classes defining the behaviour of a given PID loop
      including several actuators or detectors,
      see :ref:`pid_model`
    * **Extensions** located in a `extensions` folder: scripts and classes allowing to build extensions on top of
      the :ref:`Dashboard_module`

    Entry points python mechanism is used to let know PyMoDAQ of installed Instrument, PID models or extensions plugins

The best way to start creating a PyMoDAQ plugin is to use the template one on `github`__ and read this `tutorial`__.


__ https://github.com/PyMoDAQ/pymodaq_plugins_template
__ https://pymodaq.cnrs.fr/en/latest/tutorials/new_plugin.html

Each new functionality type can be activated within a plugin from the *pyproject.toml* file (see below) within the
features section.

.. figure:: /image/plugin_development/pyproject_toml.png
   :alt: pyproject.toml

   Content of a *pyproject.toml* file



.. toctree::
   :maxdepth: 2
   :caption: Contents:

   /developer_folder/configuration
   /developer_folder/instrument_plugins
   /developer_folder/extension_plugins
