"""Hardware capability declarations for PyMoDAQ plugins, written in the pymeasure style.

A device declares its quantities as class attributes::

    class SpectrometerCamera:
        spectrum = measurement(units='counts', shape=(1024,))
        temperature = measurement(units='K')
        exposure = control(units='ms', lo=1, hi=1000, epsilon=0.1)
        trigger = control(values=['internal', 'external'])

The attribute name is the quantity's name, which is the channel name used by
``read`` and ``write``.

Two independent properties describe a quantity:

- **access**: :attr:`Access.MEASUREMENT` (read only) or :attr:`Access.CONTROL` (read and write).
- **domain**: :attr:`Domain.CONTINUOUS` (a range, with optional limits and move tolerance) or
  :attr:`Domain.DISCRETE` (a finite list of ``values``).

Either access can have either domain: a discrete measurement is a status readback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


__all__ = [
    'Access',
    'Domain',
    'Quantity',
    'Capabilities',
    'measurement',
    'control',
    'toolbar_widgets',
    'UI_WIDGETS',
]


class Access(str, Enum):
    """Whether a quantity can be written."""

    MEASUREMENT = 'measurement'
    CONTROL = 'control'


class Domain(str, Enum):
    """What values a quantity can take."""

    CONTINUOUS = 'continuous'
    DISCRETE = 'discrete'


_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

UI_WIDGETS = frozenset({
    'value', 'move_done_led', 'stop', 'show_controls', 'selector', 'label',
    'read', 'show_graph', 'snap', 'grab', 'save', 'history', 'slider',
})

_DEFAULT_WIDGETS = {
    (Access.CONTROL, Domain.CONTINUOUS): ('value', 'move_done_led', 'stop', 'show_controls'),
    (Access.CONTROL, Domain.DISCRETE): ('selector',),
    (Access.MEASUREMENT, Domain.DISCRETE): ('label', 'grab'),
    (Access.MEASUREMENT, Domain.CONTINUOUS, 'scalar'): ('read', 'grab', 'show_graph'),
    (Access.MEASUREMENT, Domain.CONTINUOUS, 'array'): ('snap', 'grab', 'show_graph', 'save'),
}


def toolbar_widgets(quantity: 'Quantity') -> list[str]:
    """Widgets for a channel group: the defaults of the existing modules, adjusted by the declaration."""
    if quantity.access is Access.MEASUREMENT and quantity.domain is Domain.CONTINUOUS:
        scalar = len(quantity.shape) == 1 and quantity.shape[0] == 1
        defaults = _DEFAULT_WIDGETS[(Access.MEASUREMENT, Domain.CONTINUOUS, 'scalar' if scalar else 'array')]
    else:
        defaults = _DEFAULT_WIDGETS[(quantity.access, quantity.domain)]
    widgets = [w for w in defaults if w not in quantity.ui_remove]
    widgets += [w for w in quantity.ui_add if w not in widgets]
    return widgets


class Quantity:
    """A declared readable (and possibly settable) quantity.

    Created by :func:`measurement` or :func:`control` and assigned as a class attribute,
    which sets :attr:`name`.  Limits, tolerance and ``values`` are validated on construction.
    """

    def __init__(
        self,
        access: Access,
        *,
        units: str = '',
        label: str = '',
        dtype: str = 'float64',
        shape: tuple[int | None, ...] = (1,),
        lo: float | None = None,
        hi: float | None = None,
        epsilon: float = 0.0,
        values: tuple | list = (),
        docs: str = '',
        ui_add: tuple | list = (),
        ui_remove: tuple | list = (),
        push: bool = False,
        readback: bool | str = False,
    ) -> None:
        self.access = Access(access)
        self.units = units
        self.label = label
        self.dtype = dtype
        self.shape = tuple(shape)
        self.lo = lo
        self.hi = hi
        self.epsilon = float(epsilon)
        self.values = list(values)
        self.docs = docs
        self.ui_add = tuple(ui_add)
        self.ui_remove = tuple(ui_remove)
        self.push = bool(push)
        # True, or the name of the measurement that reports the device's actual value; resolved by Capabilities
        self.readback = readback
        self.name: str | None = None
        self._validate()

    def _validate(self) -> None:
        if any(dim is not None and dim < 1 for dim in self.shape):
            raise ValueError(f'shape dimensions must be positive or None, got {self.shape}')
        if self.values and (self.lo is not None or self.hi is not None or self.epsilon != 0.0):
            raise ValueError('a quantity has either values (discrete) or lo/hi/epsilon (continuous), not both')
        if self.lo is not None and self.hi is not None and self.lo > self.hi:
            raise ValueError(f'lo ({self.lo}) is greater than hi ({self.hi})')
        if self.readback and self.access is not Access.CONTROL:
            raise ValueError('only a control can have a readback')
        if self.push and self.access is not Access.MEASUREMENT:
            raise ValueError('only a measurement can be pushed by the plugin')
        if self.epsilon < 0:
            raise ValueError(f'epsilon must be non-negative, got {self.epsilon}')
        unknown = (set(self.ui_add) | set(self.ui_remove)) - UI_WIDGETS
        if unknown:
            raise ValueError(f'unknown widgets: {sorted(unknown)}; allowed: {sorted(UI_WIDGETS)}')

    def __set_name__(self, owner: type, name: str) -> None:
        if not _IDENTIFIER.match(name):
            raise ValueError(f'{owner.__name__}.{name}: quantity names must be identifiers')
        self.name = name

    @property
    def domain(self) -> Domain:
        return Domain.DISCRETE if self.values else Domain.CONTINUOUS

    def __repr__(self) -> str:
        return f'Quantity({self.name!r}, access={self.access.value!r}, domain={self.domain.value!r})'

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            'name': self.name,
            'access': self.access.value,
            'domain': self.domain.value,
            'units': self.units,
            'label': self.label,
            'readback': self.readback,
            'dtype': self.dtype,
            'shape': list(self.shape),
            'lo': self.lo,
            'hi': self.hi,
            'epsilon': self.epsilon,
            'values': list(self.values),
            'docs': self.docs,
            'ui_add': list(self.ui_add),
            'ui_remove': list(self.ui_remove),
            'push': self.push,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Quantity:
        """Rebuild a quantity from a dict produced by :meth:`to_dict`."""
        quantity = cls(
            Access(d['access']),
            units=d.get('units', ''),
            label=d.get('label', ''),
            readback=d.get('readback', False),
            dtype=d.get('dtype', 'float64'),
            shape=tuple(d.get('shape', (1,))),
            lo=d.get('lo'),
            hi=d.get('hi'),
            epsilon=d.get('epsilon', 0.0),
            values=d.get('values', []),
            docs=d.get('docs', ''),
            ui_add=d.get('ui_add', []),
            ui_remove=d.get('ui_remove', []),
            push=d.get('push', False),
        )
        quantity.name = d['name']
        return quantity


def measurement(
    *,
    units: str = '',
    label: str = '',
    dtype: str = 'float64',
    shape: tuple[int | None, ...] = (1,),
    values: tuple | list = (),
    docs: str = '',
    ui_add: tuple | list = (),
    ui_remove: tuple | list = (),
    push: bool = False,
) -> Quantity:
    """Declare a read-only quantity: a sensor reading, a detector channel, a status.

    ``push=True`` means the plugin sends its readings with ``push_reading`` instead of being polled.
    """
    return Quantity(Access.MEASUREMENT, units=units, label=label, dtype=dtype, shape=shape,
                    values=values, docs=docs, ui_add=ui_add, ui_remove=ui_remove, push=push)


def control(
    *,
    units: str = '',
    label: str = '',
    lo: float | None = None,
    hi: float | None = None,
    epsilon: float = 0.0,
    values: tuple | list = (),
    docs: str = '',
    ui_add: tuple | list = (),
    ui_remove: tuple | list = (),
    readback: bool | str = False,
) -> Quantity:
    """Declare a readable and writable quantity: a target, with the device's actual value as a readback.

    ``lo``, ``hi`` and ``epsilon`` describe a continuous range (``epsilon`` is the move tolerance).
    ``values`` describes a discrete set instead.

    ``readback`` declares the measurement that reports the actual value, which the GUI shows in the same row.
    ``True`` names it ``<name>_readback``; a string names it. If a measurement of that name is already
    declared, it is used; otherwise it is created with the units, shape and values of the control.
    """
    return Quantity(Access.CONTROL, units=units, label=label, lo=lo, hi=hi, epsilon=epsilon,
                    values=values, docs=docs, ui_add=ui_add, ui_remove=ui_remove, readback=readback)


def _readback_of(control: Quantity) -> Quantity:
    """The measurement that reports *control*'s actual value: same units, shape and values, no limits."""
    readback = Quantity(Access.MEASUREMENT, units=control.units,
                        label=f'{control.label} readback' if control.label else '',
                        dtype=control.dtype, shape=control.shape, values=control.values)
    readback.name = control.readback
    return readback


@dataclass
class Capabilities:
    """The quantities a device offers: measurements (read) and controls (read and write).

    Built from a device class with :meth:`from_device`, or from a dict with :meth:`from_dict`.
    """

    measurements: list[Quantity] = field(default_factory=list)
    controls: list[Quantity] = field(default_factory=list)

    def __post_init__(self) -> None:
        names = [q.name for q in self.measurements + self.controls]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f'quantity names must be unique, duplicated: {duplicates}')
        measured = {q.name for q in self.measurements}
        for control in self.controls:
            if not control.readback:
                continue
            if control.readback is True:
                control.readback = f'{control.name}_readback'
            if control.readback not in measured:
                self.measurements.append(_readback_of(control))
                measured.add(control.readback)

    @classmethod
    def from_device(cls, device: type | Any) -> Capabilities:
        """Collect the quantities declared on *device* and its base classes."""
        klass = device if isinstance(device, type) else type(device)
        declared: dict[str, Quantity] = {}
        for base in reversed(klass.__mro__):
            for name, value in vars(base).items():
                if isinstance(value, Quantity):
                    declared[name] = value
        quantities = list(declared.values())
        return cls(
            measurements=[q for q in quantities if q.access is Access.MEASUREMENT],
            controls=[q for q in quantities if q.access is Access.CONTROL],
        )

    def to_dict(self) -> dict:
        return {
            'measurements': [q.to_dict() for q in self.measurements],
            'controls': [q.to_dict() for q in self.controls],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Capabilities:
        return cls(
            measurements=[Quantity.from_dict(q) for q in d.get('measurements', [])],
            controls=[Quantity.from_dict(q) for q in d.get('controls', [])],
        )

    def has_measurements(self) -> bool:
        return bool(self.measurements)

    def has_controls(self) -> bool:
        return bool(self.controls)
