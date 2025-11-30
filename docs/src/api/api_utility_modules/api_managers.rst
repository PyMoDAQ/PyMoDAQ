.. _api-managers:

API of the various managers, special classes easing the use of various things such as
QActions and toolbars, Parameters, ControlModules, Presets, Configurations, ROIs...


GUI Managers
************

The ActionManager and Parameter Manager are defined in the ``pymodaq_gui`` package and
ease the developement of GUI. There are the base classes of most GUI in PyMoDAQ, especially
the CustomApp and CustomExt classes.

.. currentmodule:: pymodaq_gui.managers.action_manager

.. autosummary::
    addaction
    QAction
    ActionManager

.. currentmodule:: pymodaq_gui.managers.parameter_manager

.. autosummary::
    ParameterManager


.. _api-managers_action_manager:

.. currentmodule:: pymodaq_gui.managers.action_manager

.. autoclass:: QAction
   :members:

.. autofunction:: addaction


   .. _actionmanager_api:

.. autoclass:: ActionManager
   :members:

.. _api-managers_parameter_manager:

.. currentmodule:: pymodaq_gui.managers.parameter_manager

.. autoclass:: ParameterManager
   :members:


.. _api-managers_module_manager:

Module Managers
***************

The Module Manager is the tool used in all extensions to deal and use
the control modules from the DashBoard.


.. currentmodule:: pymodaq.utils.managers.modules_manager

.. autosummary::
    ModulesManager


.. currentmodule:: pymodaq.utils.managers.modules_manager

.. autoclass:: ModulesManager
   :members:


DashBoard Managers
******************

API of the various managers, special classes easing the experimental orchestration in the DashBoard.

.. currentmodule:: pymodaq.utils.managers.modules_manager

.. autosummary::
    preset_manager.ModulesManager
    configurator.Configurator

.. currentmodule:: pymodaq.utils.managers.preset.preset_manager

.. autoclass:: PresetManager

.. currentmodule:: pymodaq.utils.configurator.Configurator

.. autoclass:: Configurator