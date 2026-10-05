"""Hardware capability declarations for PyMoDAQ plugins.

:class:`Observable` and :class:`Variable` are purely descriptive metadata objects.
Every :class:`Variable` is also an :class:`Observable` (writable implies readable).
In a :class:`Capabilities` object:

- ``observables`` — read-only quantities (pure detectors, spectrum channels, etc.)
- ``variables``   — read-write quantities (actuator axes, tunable settings, etc.)

The variable hierarchy:

.. code-block:: text

    Observable
      └── Variable                  # unconstrained read-write quantity
            ├── ContinuousVariable  # numeric range + move-done tolerance
            └── DiscreteVariable    # finite enumeration of allowed values

A :class:`DAQ_Viewer` expects at least one observable or variable.
A :class:`DAQ_Move` expects at least one variable.
"""
from __future__ import annotations

from dataclasses import dataclass, field


__all__ = [
    'Observable',
    'Variable',
    'ContinuousVariable',
    'DiscreteVariable',
    'Capabilities',
    'infer_capabilities',
]


# ── Core metadata classes ────────────────────────────────────────────────────

@dataclass
class Observable:
    """Metadata describing a readable hardware quantity.

    Parameters
    ----------
    name : str
        Key used in ``query_data(names=[name])``.
        Must be unique within a :class:`Capabilities` object.
    label : str
        Human-readable label for UI display.
    units : str
        Physical unit string compatible with pint (e.g. ``'nm'``, ``'counts'``, ``'V'``).
    dtype : str
        NumPy dtype string (e.g. ``'float64'``, ``'uint16'``).
    shape : tuple of int or None
        Shape of one data sample. ``(1,)`` for a scalar, ``(1024,)`` for a 1-D array.
        A ``None`` in any position means the dimension length is unknown at declaration
        time (e.g. ``(None,)`` for a variable-length event list).
    """

    name: str
    label: str = ''
    units: str = ''
    dtype: str = 'float64'
    shape: tuple[int | None, ...] = (1,)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            'name': self.name,
            'label': self.label,
            'units': self.units,
            'dtype': self.dtype,
            'shape': list(self.shape),
        }

    @classmethod
    def from_dict(cls, d: dict) -> Observable:
        """Deserialize from a dict produced by :meth:`to_dict`."""
        return cls(
            name=d['name'],
            label=d.get('label', ''),
            units=d.get('units', ''),
            dtype=d.get('dtype', 'float64'),
            shape=tuple(d.get('shape', (1,))),
        )


@dataclass
class Variable(Observable):
    """Unconstrained read-write quantity.

    Every :class:`Variable` is also an :class:`Observable`.
    The ``name`` is the key used in ``change_to(name, value)``.

    For constrained quantities use the subclasses:

    - :class:`ContinuousVariable` — numeric range with move-done tolerance.
    - :class:`DiscreteVariable` — finite enumeration of allowed values.
    """

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['kind'] = 'variable'
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Variable:
        return cls(
            name=d['name'],
            label=d.get('label', ''),
            units=d.get('units', ''),
            dtype=d.get('dtype', 'float64'),
            shape=tuple(d.get('shape', (1,))),
        )


@dataclass
class ContinuousVariable(Variable):
    """Read-write quantity with a continuous numeric range.

    Parameters
    ----------
    lo : float or None
        Lower bound. ``None`` means unbounded (−∞).
    hi : float or None
        Upper bound. ``None`` means unbounded (+∞).
    epsilon : float
        Move-done tolerance for DAQ_Move actors. ``0.0`` means unspecified.
    """

    lo: float | None = None
    hi: float | None = None
    epsilon: float = 0.0

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['kind'] = 'continuous'
        d['lo'] = self.lo
        d['hi'] = self.hi
        d['epsilon'] = self.epsilon
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ContinuousVariable:
        return cls(
            name=d['name'],
            label=d.get('label', ''),
            units=d.get('units', ''),
            dtype=d.get('dtype', 'float64'),
            shape=tuple(d.get('shape', (1,))),
            lo=d.get('lo'),
            hi=d.get('hi'),
            epsilon=d.get('epsilon', 0.0),
        )


@dataclass
class DiscreteVariable(Variable):
    """Read-write quantity restricted to a finite set of values.

    Parameters
    ----------
    choices : list
        Exhaustive list of allowed values (strings, ints, floats, …).
    """

    choices: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['kind'] = 'discrete'
        d['choices'] = list(self.choices)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> DiscreteVariable:
        return cls(
            name=d['name'],
            label=d.get('label', ''),
            units=d.get('units', ''),
            dtype=d.get('dtype', 'float64'),
            shape=tuple(d.get('shape', (1,))),
            choices=list(d.get('choices', [])),
        )


# ── Deserialization dispatcher ────────────────────────────────────────────────

_KIND_MAP = {
    'variable': Variable,
    'continuous': ContinuousVariable,
    'discrete': DiscreteVariable,
}


def _variable_from_dict(d: dict) -> Variable:
    """Deserialize a Variable subclass using the ``'kind'`` discriminator."""
    kind = d.get('kind', 'variable')
    cls:Variable = _KIND_MAP.get(kind, Variable)
    return cls.from_dict(d)


# ── Capabilities container ────────────────────────────────────────────────────

@dataclass
class Capabilities:
    """Hardware capabilities declared or inferred for a plugin.

    Serializes to/from a JSON-compatible dict so it can be returned by the
    ``get_capabilities()`.

    Parameters
    ----------
    observables : list of Observable
        Read-only quantities (detector channels, sensor readings, …).
    variables : list of Variable
        Read-write quantities (actuator axes, tunable parameters, …).
    """

    observables: list[Observable] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'observables': [o.to_dict() for o in self.observables],
            'variables': [v.to_dict() for v in self.variables],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Capabilities:
        observables = [Observable.from_dict(o) for o in d.get('observables', [])]
        variables = [_variable_from_dict(v) for v in d.get('variables', [])]
        return cls(observables=observables, variables=variables)

    def has_observables(self) -> bool:
        """True if the actor exposes at least one readable quantity."""
        return bool(self.observables or self.variables)

    def has_variables(self) -> bool:
        """True if the actor exposes at least one writable quantity."""
        return bool(self.variables)


# ── Inference from existing plugin attributes ────────────────────────────────

def infer_capabilities(plugin) -> Capabilities:
    """Return the :class:`Capabilities` of a hardware plugin.

    If the plugin declares a ``capabilities`` class attribute that is already a
    :class:`Capabilities` instance, it is returned directly (opt-in path).

    Otherwise capabilities are inferred from the plugin's class attributes using
    duck typing

    * **Actuator heuristic** — plugin has ``_controller_units`` or ``_axis_names`` →
      one :class:`ContinuousVariable` named after each axis (or ``'position'`` for
      single-axis).
    * **Detector fallback** — one :class:`Observable` named ``'data'``.

    Parameters
    ----------
    plugin :
        Any plugin instance or class.  Inspected via ``getattr`` only.

    Returns
    -------
    Capabilities
    """
    caps = getattr(plugin, 'capabilities', None)
    if isinstance(caps, Capabilities):
        return caps

    controller_units = getattr(plugin, '_controller_units', None)
    axis_names = getattr(plugin, '_axis_names', None)
    epsilons = getattr(plugin, '_epsilons', None)

    if controller_units is not None or axis_names is not None:
        return _infer_move_capabilities(controller_units, axis_names, epsilons)

    # Detector fallback
    return Capabilities(
        observables=[Observable(name='data', label='Data', units='', shape=(1,))],
        variables=[],
    )


def _infer_move_capabilities(
    controller_units,
    axis_names,
    epsilons,
) -> Capabilities:
    """Build :class:`Capabilities` for an actuator from its class attributes."""

    # Normalise axis_names → list[str]
    if axis_names is None:
        names = ['position']
    elif isinstance(axis_names, dict):
        names = list(axis_names.keys())
    elif isinstance(axis_names, list):
        names = axis_names if axis_names else ['position']
    else:
        names = [str(axis_names)]

    # Normalise controller_units → list[str] aligned with names
    if isinstance(controller_units, str):
        units_list = [controller_units] * len(names)
    elif isinstance(controller_units, dict):
        units_list = [controller_units.get(n, '') for n in names]
    elif isinstance(controller_units, list):
        units_list = list(controller_units) + [''] * max(0, len(names) - len(controller_units))
    else:
        units_list = [''] * len(names)

    # Normalise epsilons → list[float] aligned with names
    if epsilons is None:
        steps = [0.0] * len(names)
    elif isinstance(epsilons, (int, float)):
        steps = [float(epsilons)] * len(names)
    elif isinstance(epsilons, dict):
        steps = [float(epsilons.get(n, 0.0)) for n in names]
    elif isinstance(epsilons, list):
        steps = [float(e) for e in epsilons] + [0.0] * max(0, len(names) - len(epsilons))
    else:
        steps = [0.0] * len(names)

    variables = [
        ContinuousVariable(name=name, label=name, units=units_list[i], epsilon=steps[i])
        for i, name in enumerate(names)
    ]
    # Variables are also readable, so they appear only in variables;
    # has_observables() returns True when variables is non-empty.
    return Capabilities(observables=[], variables=variables)
