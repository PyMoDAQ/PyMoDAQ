"""Moved to :mod:`pymodaq_utils.plugin_tools.rules`, this module is an alias kept for existing code.

.. versionadded:: 5.3.1
.. deprecated:: 5.3.4
    Use ``pymodaq_utils.plugin_tools.rules``.
"""
import sys

from pymodaq_utils.plugin_tools import rules as _module

if __name__ == '__main__':  # python -m pymodaq_utils.plugin_rules
    raise SystemExit(_module.main())

sys.modules[__name__] = _module
