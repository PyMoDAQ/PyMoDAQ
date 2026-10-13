"""Tools to develop and maintain PyMoDAQ instrument plugins.

* :mod:`~pymodaq_utils.plugin_tools.contract`: the methods of a plugin (single definition)
* :mod:`~pymodaq_utils.plugin_tools.rules`: the static rules (``PMQxxx`` codes)
* :mod:`~pymodaq_utils.plugin_tools.checks`: the report on a plugin package (``check_plugin`` command)
* :mod:`~pymodaq_utils.plugin_tools.scaffold`: creation of new plugin modules

They read the source files of the plugins and do not import ``pymodaq``. The previous locations
(``pymodaq_utils.plugin_tools.checks``, ``plugin_rules`` and ``plugin_scaffold``) still work.

.. versionadded:: 5.3.5
"""
