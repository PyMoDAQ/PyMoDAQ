"""
PyMoDAQ Status Color Palette
=============================

Proposal for a community-wide color convention for status indicators
(LEDs, icons, status bars) across all PyMoDAQ modules and plugins.

Rationale
---------
Instrument control software exposes users to many concurrent status
indicators.  When each component chooses its own colors the user must
re-learn the meaning of each indicator.  A shared vocabulary lets users
read the state of the system at a glance.

Colors are resolved from the active ``qt_themes`` theme so that they
adapt to the user's chosen dark or light theme.  Hex fallbacks are
provided for headless contexts or when a theme attribute is absent.

The six states cover the full lifecycle of a PyMoDAQ module or
operation.  The upper three states (warning / error / critical) align
deliberately with Python's ``logging`` severity levels so that the
visual vocabulary is familiar to developers.

Color Definitions
-----------------

+------------------+--------+--------------------+----------------------+
| State            | Color  | logging analogy    | Meaning              |
+==================+========+====================+======================+
| ``off``          | grey   | —                  | Module absent, not   |
|                  |        |                    | initialized, or      |
|                  |        |                    | hardware not yet     |
|                  |        |                    | connected.           |
+------------------+--------+--------------------+----------------------+
| ``idle``         | green  | —                  | Initialized and      |
|                  |        |                    | ready — waiting for  |
|                  |        |                    | a command or trigger.|
+------------------+--------+--------------------+----------------------+
| ``running``      | blue   | —                  | A command is in      |
|                  |        |                    | flight: moving,      |
|                  |        |                    | acquiring, or        |
|                  |        |                    | processing data.     |
+------------------+--------+--------------------+----------------------+
| ``warning``      | yellow | ``logging.WARNING``| A non-fatal issue.   |
|                  |        |                    | Still functional;    |
|                  |        |                    | user attention       |
|                  |        |                    | advised.             |
+------------------+--------+--------------------+----------------------+
| ``error``        | orange | ``logging.ERROR``  | An operation failed. |
|                  |        |                    | Module may still     |
|                  |        |                    | recover.             |
+------------------+--------+--------------------+----------------------+
| ``critical``     | red    | ``logging.CRITICAL``| Unrecoverable fault.|
|                  |        |                    | Timeout, hardware    |
|                  |        |                    | error, or fatal      |
|                  |        |                    | exception.           |
+------------------+--------+--------------------+----------------------+

Usage with MultistateLED
------------------------

.. code-block:: python

    from pymodaq_gui.utils.status_palette import StatusPalette
    from pymodaq_gui.utils.widgets.multistate_led import MultistateLED

    # Full five-state indicator
    led = MultistateLED(states=StatusPalette.as_states())

    # Subset — e.g. a connection indicator without 'warning'
    led = MultistateLED(states=StatusPalette.subset('off', 'idle', 'error'))

Usage in a parameter tree
-------------------------

.. code-block:: python

    from pymodaq_gui.utils.status_palette import StatusPalette

    params = [
        {'name': 'acq_status', 'type': 'action_multistate_led',
         'value': 'off',
         'states': StatusPalette.as_states()},
    ]
"""

from __future__ import annotations

import qt_themes
from qtpy import QtGui


# (state_name, theme_attribute, hex_fallback)
# theme_attribute is the name of the QColor property on a qt_themes Theme object.
_DEFINITIONS: list[tuple[str, str, str]] = [
    ('off',     'grey',   '#808080'),
    ('idle',    'green',  '#00b400'),
    ('running', 'blue', '#c8c800'),
    ('warning', 'yellow', '#dc8200'),
    ('error', 'orange', '#dc8200'),
    ('critical',   'red',    '#c80000'),
]


def _resolve(theme_attr: str, fallback: str) -> QtGui.QColor:
    """Return the theme QColor for *theme_attr*, or *fallback* hex if absent."""
    try:
        color = getattr(qt_themes.get_theme(), theme_attr, None)
        if isinstance(color, QtGui.QColor) and color.isValid():
            return color
    except Exception:
        pass
    return QtGui.QColor(fallback)


class StatusPalette:
    """Standard status color definitions for PyMoDAQ.

    Colors are drawn from the active ``qt_themes`` theme so they adapt
    to dark / light modes.  Each entry resolves to a
    ``(name, QColor)`` pair compatible with
    :class:`~pymodaq_gui.utils.widgets.multistate_led.MultistateLED`.

    The states are ordered from *least active* to *most severe*.
    """

    @classmethod
    def as_states(cls) -> list[tuple[str, QtGui.QColor]]:
        """Return all five states with theme-resolved colors."""
        return [(name, _resolve(attr, fb)) for name, attr, fb in _DEFINITIONS]

    @classmethod
    def subset(cls, *names: str) -> list[tuple[str, QtGui.QColor]]:
        """Return a subset of states in canonical order with theme-resolved colors.

        Parameters
        ----------
        *names:
            State names to include: ``'off'``, ``'idle'``, ``'running'``,
            ``'warning'``, ``'error'``.

        Raises
        ------
        ValueError
            If an unknown name is requested.

        Example
        -------
        >>> StatusPalette.subset('off', 'idle', 'error')
        [('off', QColor(...)), ('idle', QColor(...)), ('error', QColor(...))]
        """
        known = {name: (attr, fb) for name, attr, fb in _DEFINITIONS}
        unknown = set(names) - known.keys()
        if unknown:
            raise ValueError(
                f"Unknown state(s): {sorted(unknown)}. "
                f"Valid states: {list(known)}"
            )
        return [(n, _resolve(*known[n])) for n in names if n in known]

    @classmethod
    def color(cls, name: str) -> QtGui.QColor:
        """Return the theme-resolved QColor for a single state name.

        Useful when you need just the color, e.g. for an icon or stylesheet.
        """
        for n, attr, fb in _DEFINITIONS:
            if n == name:
                return _resolve(attr, fb)
        raise ValueError(
            f"Unknown state {name!r}. Valid states: {[n for n, _, _ in _DEFINITIONS]}"
        )
