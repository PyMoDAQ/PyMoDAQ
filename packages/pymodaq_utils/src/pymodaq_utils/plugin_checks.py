"""Moved to :mod:`pymodaq_utils.plugin_tools.checks`, this module is an alias kept for existing code.

.. versionadded:: 5.3.1
.. deprecated:: 5.3.5
    Use ``pymodaq_utils.plugin_tools.checks``.
"""
import sys

from pymodaq_utils.plugin_tools import checks as _module

if __name__ == '__main__':  # python -m pymodaq_utils.plugin_checks
    raise SystemExit(_module.main())

sys.modules[__name__] = _module
