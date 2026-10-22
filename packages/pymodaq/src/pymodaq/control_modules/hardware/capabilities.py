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
from typing import Any, Callable


__all__ = [
    'Access',
    'Domain',
    'Quantity',
    'Capabilities',
    'Action',
    'measurement',
    'control',
    'instr_get',
    'instr_set',
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
    'value', 'stop', 'show_controls', 'selector', 'label',
    'read', 'show_graph', 'snap', 'grab', 'save', 'history', 'slider',
})

# single-representation overrides: default widget -> the one alternative widget= may ask for instead.
# a two-valued discrete control's selector (a dropdown) is the only case so far; grows by one entry if
# a second one ever shows up, rather than a general mechanism built ahead of a second need.
_WIDGET_OVERRIDES = {'selector': 'toggle'}

_DEFAULT_WIDGETS = {
    (Access.CONTROL, Domain.CONTINUOUS): ('value', 'show_controls'),
    (Access.CONTROL, Domain.DISCRETE): ('selector',),
    (Access.MEASUREMENT, Domain.DISCRETE): ('label', 'grab'),
    (Access.MEASUREMENT, Domain.CONTINUOUS, 'scalar'): ('read', 'grab', 'show_graph'),
    (Access.MEASUREMENT, Domain.CONTINUOUS, 'array'): ('snap', 'grab', 'show_graph', 'save'),
}


@dataclass
class Action:
    """A quantity's one declared action: a callback, and how its button looks.

    ``icon`` is passed straight through to the GUI's own icon resolution
    (:func:`pymodaq_gui.utils.styling.create_icon`), so anything it accepts works here too: a Material
    icon name, a path to a png, a registered icon, a Qt theme icon, or a standard pixmap name. Left
    blank, the button shows text only. ``label`` defaults to the action's name, title-cased.

    ``opts`` reaches ``add_action`` directly for anything ``icon``/``label``/``checkable`` don't cover
    (e.g. ``icon_color``, ``icon_checked``, ``rotate``), without this class needing a field for every
    one of its keyword arguments.

    ``checkable=True`` makes the button stay pressed between clicks (e.g. a hardware dark-reference
    toggle, on until clicked again) instead of firing once (e.g. a one-shot calibration). The callback
    then takes the button's new checked state as a second argument, ``callback(plugin, checked)``,
    instead of just ``callback(plugin)`` - the plugin is never left to infer which way a checkable
    action just flipped.

    ``button=False`` registers the action (still callable through ``run_action``, scripting, or
    another trigger such as a ``merge_into`` row) without building a toolbar button for it - for an
    action you don't want cluttering a row but still want reachable. This is the action's own knob for
    that, separate from ``ui_add``/``ui_remove``: those only ever suppress or add a widget the
    declaration would otherwise get for free (see :func:`toolbar_widgets`), and an action is never one
    of those - you only get it by declaring it, so "declared but buttonless" belongs here, not there.

    ``interrupts=True`` means a successful run resolves any write still in flight for this control
    (pending, settling, or unanswered) - not just one named ``'stop'``. ``stop=`` sets it automatically.

    ``actions={'home': callback}`` is shorthand for ``actions={'home': Action(callback)}``.
    """

    callback: Callable
    icon: str = ''
    label: str = ''
    checkable: bool = False
    button: bool = True
    interrupts: bool = False
    opts: dict = field(default_factory=dict)


def toolbar_widgets(quantity: 'Quantity') -> list[str]:
    """Widgets for a channel group: the defaults of the existing modules, adjusted by the declaration.

    Three different things can change this list, each through its own, single-purpose knob - not one
    shared mechanism wearing three hats:

    - The **representation** - how this quantity's value is shown/edited (``value``, ``selector``,
      ``toggle``, ``label``, ``read``/``snap``) - is exactly one widget, chosen for you from
      ``(access, domain)``. ``widget=`` (see :func:`control`) substitutes a supported alternative for
      it outright; there is nothing to add or remove, since there is only ever one at a time.
    - **Companion views** - ``slider``, ``show_graph``, ``save``, ``history``, ``show_controls`` - are
      additive and synced to the same value, never a replacement for the representation above.
      ``ui_add``/``ui_remove`` are for exactly this: suppressing or adding one of these, never a
      representation and never an action (see below) - a widget this declaration would otherwise get,
      or not get, for free.
    - **Actions** (``actions``/``stop``) aren't a representation of a value at all - they're
      device-specific commands (e.g. a motor axis's stop, or a spectrum's background capture), so they
      never default: a button only appears once the quantity declares one, and a measurement can
      declare one just as a control can - nothing about firing a callback requires a value to write.
      Whether a *declared* action gets a button is the action's own ``button=`` (see :class:`Action`),
      not ``ui_remove`` - you only have the action because you asked for it, so "declared but
      buttonless" belongs where it's declared, not in the same knob that suppresses a free default.
    """
    if quantity.access is Access.MEASUREMENT and quantity.domain is Domain.CONTINUOUS:
        scalar = len(quantity.shape) == 1 and quantity.shape[0] == 1
        defaults = _DEFAULT_WIDGETS[(Access.MEASUREMENT, Domain.CONTINUOUS, 'scalar' if scalar else 'array')]
    else:
        defaults = _DEFAULT_WIDGETS[(quantity.access, quantity.domain)]
    if quantity.widget is not None:
        defaults = tuple(quantity.widget if w in _WIDGET_OVERRIDES else w for w in defaults)
    widgets = [w for w in defaults if w not in quantity.ui_remove]
    widgets += [w for w in quantity.ui_add if w not in widgets]
    if 'read' in widgets and 'snap' in widgets:
        raise ValueError(
            f'{quantity.name!r}: read and snap are the same one-shot representation (scalar vs '
            f'array), never both at once - pick the one matching this quantity\'s shape')
    for name, action in quantity.actions.items():
        if action.button and name not in widgets:
            widgets.append(name)
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
        widget: str | None = None,
        widget_class: type | None = None,
        push: bool = False,
        readback: bool | str = False,
        get: Callable[[Any], Any] | bool | str | None = None,
        set: Callable[[Any, Any], None] | str | None = None,
        pre_set: Callable[[Any, Any], None] | str | None = None,
        post_set: Callable[[Any, Any], None] | str | None = None,
        stop: Callable[[Any], None] | None = None,
        actions: dict[str, Callable | Action] | None = None,
        merge_into: str | None = None,
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
        # None: the default representation for (access, domain). Otherwise, the one alternative
        # representation to substitute for it - see _WIDGET_OVERRIDES and toolbar_widgets.
        self.widget = widget
        # None: the representation's own default Qt class. Otherwise, a class HardwareModule builds
        # instead - see control()'s docstring for why this isn't checked here.
        self.widget_class = widget_class
        self.push = bool(push)
        # True, or the name of the measurement that reports the device's actual value; resolved by Capabilities
        self.readback = readback
        # An explicit (self) -> value getter / (self, value) -> None setter, read()/write() otherwise
        self.get = get
        self.set = set
        # Optional hooks around a write that otherwise needs nothing but storing the value: pre_set
        # runs first (raise to reject, same as set=/write() raising); the value is then stored as
        # plugin.<name> - always, for every control, regardless of set=/write()/neither, see
        # HardwareThread.request_write; post_set runs after, so it can rely on plugin.<name> already
        # holding the new value. Mutually exclusive with set=, the escape hatch for a control that
        # needs to replace this whole shape instead of just hooking into it.
        self.pre_set = pre_set
        self.post_set = post_set
        # Named actions, each its own button in this control's own row (see Action).
        self.actions: dict[str, Action] = {
            name: value if isinstance(value, Action) else Action(callback=value)
            for name, value in (actions or {}).items()
        }
        if stop is not None:
            if self.access is not Access.CONTROL:
                raise ValueError('only a control can have a stop callback')
            self.actions.setdefault(
                'stop', Action(callback=stop, icon='stop_circle', label='Stop', interrupts=True))
        # The name of another control whose own row this one's two values render into, as a checkable
        # action, instead of this control getting a row of its own (e.g. an axis's enable button, right
        # next to its move controls). Resolved against the sibling controls by Capabilities.
        self.merge_into = merge_into
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
        if self.set is not None and self.access is not Access.CONTROL:
            raise ValueError('only a control can have a set callback')
        if (self.pre_set is not None or self.post_set is not None) and self.access is not Access.CONTROL:
            raise ValueError('only a control can have a pre_set/post_set hook')
        if (self.pre_set is not None or self.post_set is not None) and self.set is not None:
            raise ValueError('a control cannot have both pre_set=/post_set= and a set callback: pick one')
        if self.push and self.access is not Access.MEASUREMENT:
            raise ValueError('only a measurement can be pushed by the plugin')
        if self.access is not Access.CONTROL and any(action.interrupts for action in self.actions.values()):
            raise ValueError(
                'only a control can have an interrupts=True action - a measurement has no write to interrupt')
        if self.epsilon < 0:
            raise ValueError(f'epsilon must be non-negative, got {self.epsilon}')
        unknown = (set(self.ui_add) | set(self.ui_remove)) - UI_WIDGETS
        if unknown:
            raise ValueError(f'unknown widgets: {sorted(unknown)}; allowed: {sorted(UI_WIDGETS)}')
        if self.widget is not None:
            if self.access is not Access.CONTROL or len(self.values) != 2:
                raise ValueError("widget= only overrides a two-valued discrete control's representation")
            if self.widget != 'toggle':
                raise ValueError(
                    f"widget={self.widget!r}: 'toggle' is the only supported override, "
                    f"replacing the default 'selector'"
                )
        if self.widget_class is not None:
            if self.access is not Access.CONTROL:
                raise ValueError('only a control has a representation widget to override with widget_class')
            if not isinstance(self.widget_class, type):
                raise ValueError(f'widget_class must be a class, got {self.widget_class!r}')
        if self.merge_into is not None:
            if self.access is not Access.CONTROL:
                raise ValueError('only a control can be merged into another row')
            if len(self.values) != 2:
                raise ValueError(f'a control merged into another row needs exactly two values, got {self.values}')

    def __set_name__(self, owner: type, name: str) -> None:
        if not _IDENTIFIER.match(name):
            raise ValueError(f'{owner.__name__}.{name}: quantity names must be identifiers')
        self.name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        """Makes every quantity a live attribute: ``plugin.position`` reads/writes storage owned
        here, not by the plugin. Class-level access (``Plugin.position``) still returns the
        declaration itself, and ``Capabilities.from_device`` reads ``vars(cls)`` directly, so
        neither is affected.

        Unconditional, for every quantity: before this existed, a never-written ``plugin.<name>``
        returned this object instead of a value - a silent footgun, since nothing forced a plugin to
        initialize it first. For a quantity that doesn't otherwise rely on this storage, this is the
        same storage key plain instance-attribute shadowing already used, so the behavior there is
        unchanged.
        """
        if instance is None:
            return self
        return instance.__dict__.get(self.name)

    def __set__(self, instance: Any, value: Any) -> None:
        instance.__dict__[self.name] = value

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
            'merge_into': self.merge_into,
            'dtype': self.dtype,
            'shape': list(self.shape),
            'lo': self.lo,
            'hi': self.hi,
            'epsilon': self.epsilon,
            'values': list(self.values),
            'docs': self.docs,
            'ui_add': list(self.ui_add),
            'ui_remove': list(self.ui_remove),
            'widget': self.widget,
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
            merge_into=d.get('merge_into'),
            dtype=d.get('dtype', 'float64'),
            shape=tuple(d.get('shape', (1,))),
            lo=d.get('lo'),
            hi=d.get('hi'),
            epsilon=d.get('epsilon', 0.0),
            values=d.get('values', []),
            docs=d.get('docs', ''),
            ui_add=d.get('ui_add', []),
            ui_remove=d.get('ui_remove', []),
            widget=d.get('widget'),
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
    get: Callable[[Any], Any] | bool | str | None = None,
    actions: dict[str, Callable | Action] | None = None,
) -> Quantity:
    """Declare a read-only quantity: a sensor reading, a detector channel, a status.

    ``push=True`` means the plugin sends its readings with ``push_reading`` instead of being polled.

    ``get``, when given, answers a read of this quantity on its own: ``get(plugin)`` returns the value,
    instead of going through ``read(names, fresh)``. A single-channel read (Read, Snap, a one-shot
    subscription) always uses it. A periodic read groups it with other channels sharing the same period
    only for channels without their own ``get``; channels with one are read individually, so declaring
    it opts a channel out of the plugin's batching.

    ``get=True`` is sugar for the common case of a ``get`` that's nothing but
    ``lambda plugin: plugin.<name>`` - answering from the quantity's own attribute (thanks to
    ``Quantity.__get__``, that attribute is live from the moment the class is declared, no ``__init__``
    assignment needed first). There's no equivalent keyword-free default the way a control's write has
    (see :func:`control`'s ``pre_set``/``post_set``), since a measurement is never written, so there's
    nothing that automatically keeps the attribute populated - the plugin still has to assign it itself
    somewhere.

    A string is sugar of a different kind: ``get='_read_temperature'`` is
    ``lambda plugin: plugin._read_temperature()`` - a plugin method, called with no arguments, for a
    value that's genuinely computed rather than just stored (the case ``get=True`` doesn't cover).
    Still needs a real callback (or ``read()``) for anything needing more than one plain call - a
    value built from several internal pieces, or one taking an argument of its own.

    What ``get``/``read`` return is normally a plain array or scalar, which ``HardwareModule`` wraps
    into a single-array, single-label :class:`~pymodaq_data.data.DataWithAxes` on the way to the
    viewer. Either may instead return an already-built ``DataWithAxes``/``DataRaw`` directly - e.g.
    ``DataRaw(name, data=[ch_a, ch_b], labels=['ch_a', 'ch_b'])`` for two channels a spectrometer
    reports together, shown as two labeled curves sharing one plot and legend instead of one dock
    per channel. Nothing is declared here for this: the plotted shape (how many arrays, their
    labels, real axes if any) is exactly whatever the plugin's own return value says, the same way
    ``read()``'s ``DataToExport`` already works - not a separate keyword that would just have to
    repeat what the return value already carries. ``shape`` still describes the single-curve default
    case, used to pick the right dock before the first reading ever arrives.

    ``actions`` adds a button per entry, same as on :func:`control` (see there for the full shape,
    including ``checkable`` and ``button=False``): a measurement can trigger a plugin-side operation
    just as a control can - e.g. a spectrum measurement's one-shot background capture, or a genuine
    hardware toggle such as a firmware dark-reference mode - there is nothing write-specific about an
    action, it needs no value of its own to write.
    """
    return Quantity(Access.MEASUREMENT, units=units, label=label, dtype=dtype, shape=shape,
                    values=values, docs=docs, ui_add=ui_add, ui_remove=ui_remove,
                    push=push, get=get, actions=actions)


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
    widget: str | None = None,
    widget_class: type | None = None,
    readback: bool | str = False,
    get: Callable[[Any], Any] | bool | str | None = None,
    set: Callable[[Any, Any], None] | str | None = None,
    pre_set: Callable[[Any, Any], None] | str | None = None,
    post_set: Callable[[Any, Any], None] | str | None = None,
    stop: Callable[[Any], None] | None = None,
    actions: dict[str, Callable | Action] | None = None,
    merge_into: str | None = None,
) -> Quantity:
    """Declare a readable and writable quantity: a target, with the device's actual value as a readback.

    ``lo``, ``hi`` and ``epsilon`` describe a continuous range (``epsilon`` is the move tolerance).
    ``values`` describes a discrete set instead.

    ``widget`` substitutes the one alternative representation for the default a two-valued discrete
    control otherwise gets: ``'toggle'`` in place of the usual dropdown ``selector``, for a control
    whose two values read better as on/off than as a labelled list (e.g. ``values=['disabled',
    'enabled']``). It replaces the default outright, rather than adding alongside it - unlike
    ``ui_add``/``ui_remove`` below, which are for additive companion widgets, never the representation
    itself.

    ``widget_class`` substitutes the Qt class :mod:`~pymodaq.control_modules.hardware_module` builds for
    this control's representation (the ``value`` spinbox, or the ``selector``/``toggle`` a discrete
    control gets) - e.g. a styled ``QDoubleSpinBox`` subclass, or a custom-painted slider-like widget
    for a two-valued control. Not checked here: this module stays Qt-free on purpose (see
    :mod:`~pymodaq.control_modules.hardware.controller`'s own "no GUI" boundary), and a Qt *property*'s name
    doesn't always match its Python getter method (``QPushButton``'s ``checked`` property reads through
    ``isChecked()``, not ``checked()``), so there's nothing reliable to check without an actual Qt
    instance in hand. The real compatibility check - does the class actually expose the property and
    signal the representation needs - happens where Qt is already in scope, when
    :mod:`~pymodaq.control_modules.hardware_module` builds the widget. Not serialized (a live class
    reference, same as ``get``/``set``/``actions``). A ``slider`` companion widget (``ui_add=('slider',)``)
    isn't covered by this yet - it's a different slot from the representation, an easy follow-up with
    the same mechanism once something needs it.

    ``get`` and ``set`` answer a read or a write of this quantity directly: ``get(plugin)`` returns the
    value, ``set(plugin, value)`` applies it, instead of ``read``/``write``. See :func:`measurement` for
    how ``get`` interacts with periodic batching, and for ``get=True`` - the common case of a control
    with no settling lag answering its read straight from ``plugin.<name>``, the same attribute the
    write side below already stores into for free, so the two end up reading each other for nothing
    more than ``get=True``.

    A write is never only ``write()``/``set()``, though: whichever of ``set`` or ``write()`` actually
    applies the value (if either does - see below), the device thread then always stores it as
    ``plugin.<name>`` too - live immediately, thanks to ``Quantity.__get__``/``__set__``, no
    ``__init__`` assignment needed, so ``plugin.position = 15`` then ``print(plugin.position)`` just
    works. A control declaring none of ``set``/``pre_set``/``post_set`` and backed by no ``write()``
    method needs nothing else at all: the value is stored and nothing more happens, the "just an
    attribute" case. ``write()`` itself is only called when the plugin actually defines it; a plugin
    with nothing left for it to do can simply not define it.

    ``pre_set``/``post_set`` hook into that same write, for the common case that needs a little more
    than plain storage but not a whole ``set=``/``write()`` of its own: ``pre_set(plugin, value)`` runs
    first - raise to reject the write (``write_failed``, same as ``set``/``write()`` raising would);
    ``post_set(plugin, value)`` runs after the value has already been stored, for a side effect that
    can rely on ``plugin.<name>`` already holding it (e.g. turning another setting off above some
    threshold). Either may be given alone. Mutually exclusive with ``set``, which replaces this shape
    entirely instead of hooking into it - needed for a control whose write does something the stored
    value alone can't express (e.g. storing under a different name), or one that must share a single
    hardware transaction with other channels.

    A string on ``get``/``set``/``pre_set``/``post_set`` is sugar for calling a plugin method by name
    instead of writing a lambda that does nothing but forward to it: ``post_set='_clamp_averaging'``
    is ``lambda plugin, value: plugin._clamp_averaging(value)``; ``get``'s string form takes no
    argument instead (``getattr(plugin, name)()``), same as its own string form on :func:`measurement`.
    Still needs a real callback for anything the method call alone doesn't cover - a different
    argument shape, or logic that belongs inline rather than behind a named method.

    ``readback`` declares the measurement that reports the actual value, which the GUI shows in the same row.
    ``True`` names it ``<name>_readback``; a string names it. If a measurement of that name is already
    declared, it is used; otherwise it is created with the units, shape and values of the control, and
    with the control's own ``get`` as its ``get`` too, if it has one (see :func:`_readback_of`) - right
    for a control with no real settling lag, where the control's own answer already is the readback's
    answer. A control with no ``get`` (the laggy case) gets an empty auto-created readback instead,
    answered through ``read()`` the same way the control's own value is.

    ``actions`` adds a button per entry, named after its key, calling ``callback(plugin)``: opt-in,
    for the controls that need one (e.g. a motor axis) - the same kwarg exists on :func:`measurement`
    too, for an action with nothing to write (e.g. a spectrum's background capture). A value can be a
    bare callback (label: the key, title-cased), or an :class:`Action` for an icon, a different label,
    ``checkable=True`` (the callback then also takes the button's new state,
    ``callback(plugin, checked)``), and/or ``button=False`` to register the action without a toolbar
    button for it. ``stop=`` is shorthand for a conventionally-iconed ``'stop'`` entry in ``actions``;
    both may be given together. With ``readback`` and ``epsilon`` set, a write's pending state also
    waits for the readback to settle, so ``stop`` has something meaningful to interrupt - see
    ``device_module_connections.md`` ("Writing and settling", "Actions") for the full
    action/settle/LED interaction and why only ``stop`` clears a pending row.

    ``merge_into`` folds this control into another quantity's own row (a control's or a measurement's)
    as a checkable action, instead of giving it a row of its own - e.g. an axis's enable button next to
    its move controls. Needs exactly two ``values``, the same requirement as ``widget='toggle'`` above;
    still dispatches through the normal write path, only where it is drawn changes. See
    ``device_module_connections.md`` ("merge_into") for the rendering details.
    """
    return Quantity(Access.CONTROL, units=units, label=label, lo=lo, hi=hi, epsilon=epsilon,
                    values=values, docs=docs, ui_add=ui_add, ui_remove=ui_remove, widget=widget,
                    widget_class=widget_class, readback=readback, get=get, set=set,
                    pre_set=pre_set, post_set=post_set, stop=stop, actions=actions, merge_into=merge_into)


def instr_get(method: Callable[[Any], Any], attr: str = 'controller') -> Callable[[Any], Any]:
    """Bridge ``get=`` to a method of a *composed* instrument object, by direct reference.

    For a plugin that holds its real driver as an attribute (``self.controller`` by default - the
    same name ``ini_stage``/``ini_detector`` already use for the old-style control modules, so a
    bare ``controller: MyInstr`` class-level annotation still gives IDE autocompletion on it)
    rather than inheriting from it. ``control()``/``measurement()`` are evaluated in the class
    body, before any instance - and so ``self.controller`` - exists, so *method* has to be the
    driver class's own method, referenced directly (``MyInstr.get_trigger``, never
    ``self.controller.get_trigger`` - there is no ``self`` at that point to write it with); *attr*
    is looked up on the actual plugin instance only once *method* is actually called::

        class MySpectrometer:
            controller: MyInstr  # type hint only, for autocompletion - no runtime effect

            def open(self, settings):
                self.controller = MyInstr(resource_name)  # assigned here, not __init__

            trigger = control(values=['internal', 'external'],
                               get=instr_get(MyInstr.get_trigger),
                               set=instr_set(MyInstr.set_trigger))

    When the driver's own attribute already shares the quantity's name (e.g. a pymeasure
    property), reach into its ``fget``/``fset`` instead of a plain method -
    ``instr_get(SomePymeasureInstrument.trigger.fget)`` - as long as the PyMoDAQ-facing quantity
    is declared under a *different* name; declaring it under the identical name would instead
    replace that attribute outright (see ``hardware/README.md``, "Wrapping an existing instrument
    object").

    If the plugin inherits from the driver class instead of composing it, skip this wrapper
    entirely and pass *method* straight to ``get=``: ``getter(plugin)`` already resolves, since
    ``plugin`` then *is* an instance of the driver class.
    """
    return lambda plugin: method(getattr(plugin, attr))


def instr_set(method: Callable[[Any, Any], None], attr: str = 'controller') -> Callable[[Any, Any], None]:
    """The ``set=``/``pre_set=``/``post_set=`` mirror of :func:`instr_get` - see there."""
    return lambda plugin, value: method(getattr(plugin, attr), value)


def _readback_of(control: Quantity) -> Quantity:
    """The measurement that reports *control*'s actual value: same units, shape and values, no limits.

    Only auto-created when nothing of that name was declared already (see the loop that calls this);
    a plugin that needs the readback answered differently from the control just declares it itself,
    which skips this entirely.

    Defaults its ``get`` to the control's own ``get``, if it has one: a control answering its own read
    directly (rather than through ``read()``) is, by that same choice, saying there's nothing for a
    separate readback to report that it doesn't already - the common case for a quantity with no real
    settling lag (e.g. ``exposure``). A control with no ``get`` (the laggy case - a motor's target vs.
    its actual position, read separately through ``read()``) gets no default here either, since there
    is no single callable to copy; the plugin answers the readback itself, through ``read()``, as the
    stage example already does.
    """
    readback = Quantity(Access.MEASUREMENT, units=control.units,
                        label=f'{control.label} readback' if control.label else '',
                        dtype=control.dtype, shape=control.shape, values=control.values,
                        get=control.get)
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
        # get=True is sugar for the common case of answering a read straight from the quantity's own
        # attribute; a string on get/set/pre_set/post_set is sugar for calling a plugin method by
        # name instead of writing a one-line lambda just to forward to it - both resolved here,
        # before anything below, so _readback_of (next) sees a real callable to default a readback's
        # own get to, same as a hand-written lambda would give it.
        for quantity in self.measurements + self.controls:
            if quantity.get is True:
                quantity.get = lambda plugin, name=quantity.name: getattr(plugin, name)
            elif isinstance(quantity.get, str):
                quantity.get = lambda plugin, method=quantity.get: getattr(plugin, method)()
            if isinstance(quantity.set, str):
                quantity.set = lambda plugin, value, method=quantity.set: getattr(plugin, method)(value)
            if isinstance(quantity.pre_set, str):
                quantity.pre_set = lambda plugin, value, method=quantity.pre_set: getattr(plugin, method)(value)
            if isinstance(quantity.post_set, str):
                quantity.post_set = lambda plugin, value, method=quantity.post_set: getattr(plugin, method)(value)
        measured = {q.name for q in self.measurements}
        controlled = {q.name for q in self.controls}
        readback_owner: dict[str, str] = {}
        for control in self.controls:
            if not control.readback:
                continue
            if control.readback is True:
                control.readback = f'{control.name}_readback'
            if control.readback in readback_owner:
                raise ValueError(
                    f'readback {control.readback!r} is declared by both '
                    f'{readback_owner[control.readback]!r} and {control.name!r}'
                )
            if control.readback in controlled:
                # a readback can reuse an existing *measurement* (see the docstring on `control`),
                # but reusing a control's name would silently alias a writable quantity as if it
                # were this control's read-only readback - almost certainly not what either
                # declaration intended, and not caught by the checks above since this name only
                # exists once this loop generates it, after the blanket duplicate-name check already ran
                raise ValueError(
                    f'{control.name!r} declares readback {control.readback!r}, which is itself a '
                    f'declared control'
                )
            readback_owner[control.readback] = control.name
            if control.readback not in measured:
                self.measurements.append(_readback_of(control))
                measured.add(control.readback)
        # the target's own row is just where this control's button is drawn; a measurement's row
        # is as good a home for it as another control's, since the write still goes through this
        # control's own set path either way (e.g. a channel's enable, merged into that
        # measurement's row rather than getting a row of its own)
        by_name = {q.name: q for q in self.measurements + self.controls}
        for control in self.controls:
            if control.merge_into is None:
                continue
            if control.merge_into == control.name:
                raise ValueError(f'{control.name!r} cannot merge into its own row')
            target = by_name.get(control.merge_into)
            if target is None:
                raise ValueError(
                    f'{control.name!r} merges into {control.merge_into!r}, which is not a declared quantity'
                )
            if target.merge_into is not None:
                raise ValueError(
                    f'{control.name!r} merges into {control.merge_into!r}, which itself merges into '
                    f'{target.merge_into!r}: merges cannot chain'
                )

    @classmethod
    def from_device(cls, device: type | Any) -> Capabilities:
        """Collect the quantities declared on *device* and its base classes."""
        klass = device if isinstance(device, type) else type(device)
        declared: dict[str, Quantity] = {}
        # __mro__ runs most-derived class first, object last; reversed() walks it base-to-derived
        # so a subclass's own Quantity overwrites same-named dict entry last, same as normal
        # attribute lookup - a subclass redeclaring a parent's control/measurement wins.
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
