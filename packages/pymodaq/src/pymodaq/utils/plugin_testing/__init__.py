"""Tools to test an instrument plugin package, to be used from the test modules of a plugin repository.

* :class:`PluginPackageChecks`: pytest mixin applying the acceptance checks (package layout, entry points, naming,
  mandatory methods, static rules) of :mod:`pymodaq_utils.plugin_checks` to a plugin package. No hardware is needed.
* The helpers of :mod:`pymodaq.utils.plugin_testing.harness` (``make_actuator``, ``move_abs_and_wait``,
  ``grab_and_wait``...) exercise the *behaviour* of a plugin class, usually against a fake controller, without
  hardware and without any visible GUI.

The static checks themselves (``check_plugin`` command, :mod:`pymodaq_utils.plugin_checks`) stay in ``pymodaq_utils``:
they do not import ``pymodaq`` and are therefore fast and free of side effects. Importing this module starts the whole
PyMoDAQ initialization, as importing a plugin does.

.. versionadded:: 5.3.2
    Moved here from ``pymodaq_utils.plugin_testing`` (still importable from there, with a deprecation warning).
"""
from pymodaq.utils.plugin_testing.package_checks import PluginPackageChecks
from pymodaq.utils.plugin_testing.harness import (SignalTimeout, wait_for_signal, make_actuator, make_detector,
                                                  move_abs_and_wait, move_rel_and_wait, move_home_and_wait,
                                                  grab_and_wait, assert_units)

__all__ = ['PluginPackageChecks', 'SignalTimeout', 'wait_for_signal', 'make_actuator', 'make_detector',
           'move_abs_and_wait', 'move_rel_and_wait', 'move_home_and_wait', 'grab_and_wait', 'assert_units']
