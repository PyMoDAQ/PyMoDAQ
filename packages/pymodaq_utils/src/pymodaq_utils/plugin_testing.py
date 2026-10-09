"""Moved to :mod:`pymodaq.utils.plugin_testing`, with the tools to test the behaviour of a plugin.

The pytest mixin was in ``pymodaq_utils`` to avoid the initialization of ``pymodaq`` when importing it. As it is used
in tests that import the plugins (hence ``pymodaq``) anyway, it now sits with the other plugin testing tools. This
module is kept for the plugin repositories written for PyMoDAQ 5.3.1 and will be removed in a later version.

.. versionadded:: 5.3.1
.. deprecated:: 5.3.2
    Use ``from pymodaq.utils.plugin_testing import PluginPackageChecks``.
"""
from pymodaq_utils.warnings import deprecation_msg


def __getattr__(name):
    if name == 'PluginPackageChecks':
        try:
            from pymodaq.utils.plugin_testing import PluginPackageChecks
        except ImportError as e:  # pragma: no cover
            raise ImportError('PluginPackageChecks needs pymodaq >= 5.3.2: pymodaq.utils.plugin_testing') from e
        deprecation_msg('pymodaq_utils.plugin_testing is deprecated, use pymodaq.utils.plugin_testing instead')
        return PluginPackageChecks
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
