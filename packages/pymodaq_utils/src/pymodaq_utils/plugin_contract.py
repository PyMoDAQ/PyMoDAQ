"""The contract of an instrument plugin: the methods a plugin class has to (or should) override.

This is the single place where these lists are defined. The static rules (:mod:`pymodaq_utils.plugin_rules`), the
checks (:mod:`pymodaq_utils.plugin_checks`), the plugin tests and the documentation read them from here, so they
cannot disagree.

.. versionadded:: 5.3.4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Kind = Literal['move', 'viewer']


@dataclass(frozen=True)
class PluginMethod:
    """One method of an actuator or detector plugin

    Parameters
    ----------
    name: str
        name of the method in the plugin class
    kind: 'move' or 'viewer'
        actuator (``DAQ_Move_base``) or detector (``DAQ_Viewer_base``)
    mandatory: bool
        if True, a plugin that does not override it is wrong (error). Otherwise the base class has a default
        that does nothing or raises ``NotImplementedError``: override it when the instrument can do it.
    purpose: str
        when it is called and what it has to do
    returns: str
        what it has to return ('' if nothing)
    """
    name: str
    kind: Kind
    mandatory: bool
    purpose: str
    returns: str = ''


PLUGIN_METHODS: tuple[PluginMethod, ...] = (
    PluginMethod('ini_attributes', 'move', False,
                 'called first, in the constructor: declare the attributes (type hints, ``self.controller = None``)'),
    PluginMethod('ini_stage', 'move', True,
                 'initialize the communication when the actuator is initialized; if ``self.is_master`` create the '
                 'controller, otherwise use the ``controller`` argument (shared with the master)',
                 '``(info: str, initialized: bool)``'),
    PluginMethod('get_actuator_value', 'move', True,
                 'read the current position from the hardware, on request and after each move',
                 'a ``DataActuator`` with units (or a float if ``data_actuator_type`` is ``float``)'),
    PluginMethod('move_abs', 'move', False,
                 'move to an absolute value (a ``DataActuator``, in the units of the axis)'),
    PluginMethod('move_rel', 'move', False,
                 'move by a relative value (a ``DataActuator``, in the units of the axis)'),
    PluginMethod('move_home', 'move', False, 'send the actuator to its home position'),
    PluginMethod('stop_motion', 'move', False, 'stop the motion now; the default does nothing'),
    PluginMethod('commit_settings', 'move', False,
                 'a setting of the tree changed in the UI: send it to the hardware'),
    PluginMethod('close', 'move', True, 'release the hardware (safe state, close the communication)'),
    PluginMethod('ini_attributes', 'viewer', False,
                 'called first, in the constructor: declare the attributes (type hints, ``self.controller = None``)'),
    PluginMethod('ini_detector', 'viewer', True,
                 'initialize the communication when the detector is initialized; if ``self.is_master`` create the '
                 'controller, otherwise use the ``controller`` argument (shared with the master)',
                 '``(info: str, initialized: bool)``'),
    PluginMethod('grab_data', 'viewer', True,
                 'start an acquisition (``Naverage`` averages); send the data with ``self.dte_signal.emit`` '
                 '(or ``dte_signal_temp``) as a ``DataToExport`` with axes and units'),
    PluginMethod('stop', 'viewer', True, 'stop the acquisition in progress'),
    PluginMethod('commit_settings', 'viewer', False,
                 'a setting of the tree changed in the UI: send it to the hardware'),
    PluginMethod('close', 'viewer', True, 'release the hardware (safe state, close the communication)'),
)


def methods_of(kind: Kind) -> tuple[PluginMethod, ...]:
    """All the methods of the contract of an actuator ('move') or of a detector ('viewer')"""
    return tuple(m for m in PLUGIN_METHODS if m.kind == kind)


def mandatory_methods(kind: Kind) -> tuple[str, ...]:
    """Names of the methods that a plugin has to override"""
    return tuple(m.name for m in methods_of(kind) if m.mandatory)


def recommended_methods(kind: Kind) -> tuple[str, ...]:
    """Names of the other methods of the contract: to override when the instrument can do it"""
    return tuple(m.name for m in methods_of(kind) if not m.mandatory)


def contract_as_rst() -> str:
    """The contract as two reStructuredText tables, to be included in the documentation"""
    out = []
    for kind, title in (('move', 'Actuator (``DAQ_Move_base``)'), ('viewer', 'Detector (``DAQ_Viewer_base``)')):
        out += [title, '-' * len(title), '',
                '.. list-table::', '   :header-rows: 1', '   :widths: 20 12 48 20', '',
                '   * - Method', '     - Required', '     - When it is called, what it does', '     - Returns']
        for m in methods_of(kind):
            out += [f'   * - ``{m.name}``', f'     - {"yes" if m.mandatory else "no"}',
                    f'     - {m.purpose}', f'     - {m.returns}']
        out.append('')
    return '\n'.join(out)
