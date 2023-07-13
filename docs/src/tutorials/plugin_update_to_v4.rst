.. _plugin_update_to_v4:

Updating your instrument plugin for PyMoDAQ 4
=============================================

What's new in PyMoDAQ 4
***********************
The main modification in PyMoDAQ 4 concerning the instrument :term:`plugins<plugin>` is related to the hierarchy
of the :term:`modules<module>` in the source code, see :ref:`whats_new`.

What should be modified
***********************

Mostly the only things to be modified are imports that should reflect the new package layout. This includes
import in obvious files, for instance imports in the ``DAQ_Move_template`` plugin, see :numref:`import_daq_move`.

.. _import_daq_move:

.. figure:: /image/plugin_tov4/import_new.png

    New imports

Some imports are a bit more insidious. Indeed, often there is no specific code in the ``__init__.py`` files we see
everywhere in our modules. But in the plugins, there is a bit of initialization code, see for
instance :numref:`hidden_imports`

.. _hidden_imports:

.. figure:: /image/plugin_tov4/hidden_import_new.png

    New imports hidden in the __init__.py files

And that's it, they should be working now!

But to make things very neat, your detector instrument plugins should
emit no more lists of DataFromPlugins objects but a DataToExport emitted using new signals, see :ref:`data_emission`.

