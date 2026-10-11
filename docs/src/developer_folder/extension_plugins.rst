.. _extension_plugins:

Extension Plugins
=================

.. toctree::
   :maxdepth: 3
   :caption: Contents:

PyMoDAQ's plugins allows to add functionnalities to PyMoDAQ from external packages. You should be well aware of the
instrument type plugins and somehow of the PID models plugins. Here we are highlighting how to built dashboard
extensions such as the :ref:`DAQ_Scan_module`.

An extension is a user interface that runs inside the Dashboard and uses the instruments (control modules) the
Dashboard already manages, for instance to scan an actuator while recording a detector, or to log their data. The base
class for such an interface is ``CustomExt``: it is ``CustomApp`` (the generic user-interface skeleton also used by
standalone applications and by the Dashboard itself) plus what deals with instruments and the Dashboard. The big
picture, with diagrams, is in :ref:`custom_app_context`.

For your package to be considered as a PyMoDAQ's dashboard extension, you should make sure of a few things:

* The entrypoint in the *pyproject.toml* file should be correctly configured, see :numref:`extension_entrypoint_fig`
* The presence of an *extensions* module at the root of the package
* each module within the *extensions* module will define an extension. It should contains three attributes:

  * EXTENSION_NAME: a string used to display the extension name in the dashboard extension menu
  * CLASS_NAME: a string giving the name of the extension class
  * a class deriving from the ``CustomExt`` base class (see :ref:`custom_app`). ``CustomExt`` itself extends
    ``CustomApp`` with what deals with instruments and the Dashboard (``dashboard``, ``modules_manager``,
    experiment and state managers, Dashboard toolbar)

The *pymodaq_plugins_template* contains already all this, so make sure to start from there when you wish to build an
extension.

  .. _extension_entrypoint_fig:

.. figure:: /image/extensions/entrypoint.png
   :alt: dashboard

   The correct configuration of your package.

The class itself defining the extension derives from the ``CustomExt`` base class (``pymodaq.utils.custom_ext``), which
extends the ``CustomApp`` base class. As such, it's ``__init__`` method
takes two attributes, a ``DockArea`` instance and a ``DashBoard`` instance (the one from which the extension will be
loaded and that contains all the actuators/detectors needed for your extension). The ``DashBoard`` will smoothly
initialize your class when launching it from the menu. Below you'll find a sample of an extension module with an
extension class called ``MyExtension`` (from the *pymodaq_plugins_template* package)


.. code-block::

    EXTENSION_NAME = 'MY_EXTENSION_NAME'
    CLASS_NAME = 'MyExtension'

    class MyExtension(CustomExt):
        # list of dicts enabling the settings tree on the user interface
        params = [
            {'title': 'Main settings:', 'name': 'main_settings', 'type': 'group', 'children': [
                {'title': 'Save base path:', 'name': 'base_path', 'type': 'browsepath',
                 'value': config['data_saving']['h5file']['save_path']},
                {'title': 'File name:', 'name': 'target_filename', 'type': 'str', 'value': "", 'readonly': True},
                {'title': 'Date:', 'name': 'date', 'type': 'date', 'value': QtCore.QDate.currentDate()},
                {'title': 'Do something, such as showing data:', 'name': 'do_something', 'type': 'bool', 'value': False},
                {'title': 'Something done:', 'name': 'something_done', 'type': 'led', 'value': False, 'readonly': True},
                {'title': 'Infos:', 'name': 'info', 'type': 'text', 'value': ""},
                {'title': 'push:', 'name': 'push', 'type': 'bool_push', 'value': False}
            ]},
            {'title': 'Other settings:', 'name': 'other_settings', 'type': 'group', 'children': [
                {'title': 'List of stuffs:', 'name': 'list_stuff', 'type': 'list', 'value': 'first',
                 'limits': ['first', 'second', 'third'], 'tip': 'choose a stuff from the list'},
                {'title': 'List of integers:', 'name': 'list_int', 'type': 'list', 'value': 0,
                 'limits': [0, 256, 512], 'tip': 'choose a stuff from this int list'},
                {'title': 'one integer:', 'name': 'an_integer', 'type': 'int', 'value': 500, },
                {'title': 'one float:', 'name': 'a_float', 'type': 'float', 'value': 2.7, },
            ]},
        ]

        def __init__(self, dockarea, dashboard):
            super().__init__(dockarea, dashboard)
            self.setup_ui()

With such a file in the extensions folder, the dashboard will be able to see it and will list it into its available
extensions. Then you'll have to code the inners of your extension following the ``CustomExt`` class, which extends
``CustomApp`` (see :ref:`custom_app`). The big difference between extensions and Standalone apps resides in the fact that your
dashboard instance is available here, hence all the control modules it contains. You'll be able to use all their
functionalities only focusing on your extension layout!

.. _plugin_models:

Models of the extensions
------------------------

Some extensions delegate the part that depends on your experiment to a *model*: a small class that you write and that
the extension finds in your plugin package. Four extensions use models:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Extension
     - Base class of the model
     - Example in *pymodaq_plugins_mockexamples*
   * - :ref:`PID <PID_module>`
     - ``PIDModelGeneric``
     - ``PIDModelBeamSteering``, ``PIDModelMockHeater``
   * - :ref:`Bayesian <bayesian_extension>` and :ref:`Adaptive <adaptive_extension>`
     - ``OptimizerModelGeneric`` or ``OptimizerModelDefault``
     - ``BayesianModelMock``
   * - :ref:`DataMixer <datamixer_extension>`
     - ``DataMixerModel``
     - ``DataMixerModelFit``
   * - Sequencer, see :ref:`Extending the Sequencer <sequencer_developer>`
     - ``ChoiceModelBase``, registered with the ``@ChoiceModelFactory.register_choice()`` decorator (the model is not
       found by its base class)
     - ``UserInput``, ``ThresholdChoiceModel``, ``TrueChoiceModel`` and ``FalseChoiceModel`` in
       ``pymodaq/extensions/sequencer/models``

To make your models visible:

* set ``models = true`` in the ``[features]`` section of the *pyproject.toml* of your package (this creates the
  ``pymodaq.models`` entry point);
* put each model in its own module of the ``models`` folder at the root of the package (the file name is the name of the
  model in the extension). The class of the module that derives from the base class of the extension is the model.
  It can derive from an intermediate class of your own, and the base class itself or classes imported from other
  modules are ignored.

The package `pymodaq_plugins_mockexamples <https://github.com/PyMoDAQ/pymodaq_plugins_mockexamples>`__ gathers working
examples of models together with the mock actuators and detectors to try them with: start from there rather than from
a blank file, and see the page of each extension for the methods to implement.
