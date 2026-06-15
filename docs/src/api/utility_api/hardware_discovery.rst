.. _hardware_discovery_API:

Hardware Discovery
******************

PyMoDAQ provides a shared, process-lifetime cache for enumerating hardware
resources. Each backend is queried at most once per process; every plugin that
imports from :mod:`pymodaq_plugins_utils.hardware` reuses the same cached result.

Both ``pyvisa`` and ``pyserial`` are **optional** dependencies. If a backend
is not installed, the corresponding functions return empty lists silently —
no exception is raised.

.. seealso::

   :ref:`hardware_discovery_plugin` in the plugin development tutorial for
   migration examples.

Base cache class
++++++++++++++++

.. autoclass:: pymodaq_plugins_utils.hardware.base.HardwareCache
   :members:

VISA resources
++++++++++++++

.. automodule:: pymodaq_plugins_utils.hardware.visa
   :members:

Serial ports
++++++++++++

.. automodule:: pymodaq_plugins_utils.hardware.serial_ports
   :members:

Package helpers
+++++++++++++++

.. automodule:: pymodaq_plugins_utils.hardware
   :members:
