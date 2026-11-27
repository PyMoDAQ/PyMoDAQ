"""``setting=``: resolving a ``Quantity``'s domain from the plugin's own settings tree, and finding
a quantity by the setting it's backed by.

Split out of ``capabilities.py`` to keep that module's own size down - self-contained (only
``Capabilities.__post_init__``'s ``setting=`` resolution calls into it, via ``capabilities.py``'s
own re-exports), and Qt-free the same way that module is.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from pymodaq.control_modules.hardware.capabilities import Quantity

__all__ = ['find_param_entry', 'derive_setting_domain', 'in_domain', 'param_resolves_a_domain',
           'quantity_for_setting']


def find_param_entry(params: list, name: str) -> dict | None:
    """The ``params``-style dict named *name*, searched recursively through ``'group'`` children."""
    for entry in params:
        if not isinstance(entry, dict):
            continue
        if entry.get('name') == name:
            return entry
        children = entry.get('children')
        if children:
            found = find_param_entry(children, name)
            if found is not None:
                return found
    return None


def _list_domain(entry: dict) -> list:
    """pyqtgraph's ``'list'`` shows a dict's keys as the choices (see ``parameter_ex.py``'s
    ``dict_list``), or a plain list as itself."""
    limits = entry.get('limits')
    if isinstance(limits, dict):
        return list(limits.keys())
    return list(limits or [])


def _bool_domain(_entry: dict) -> list:
    return [False, True]


def _numeric_bounds(entry: dict) -> tuple[float | None, float | None]:
    # pyqtgraph never cross-populates 'limits' and 'min'/'max' - either or both may be declared,
    # independently, so both are checked rather than assuming one implies the other. Shared by
    # 'float'/'int'/'slide': the extra presentation knobs 'slide' alone carries (log/linear, step,
    # siPrefix) are a representation concern, handled where Qt builds the widget, not here.
    limits = entry.get('limits')
    if limits is not None:
        return limits[0], limits[1]
    return entry.get('min'), entry.get('max')


_DOMAIN_FROM = {'list': _list_domain, 'bool': _bool_domain}
_BOUNDS_FROM = {'float': _numeric_bounds, 'int': _numeric_bounds, 'slide': _numeric_bounds}


def derive_setting_domain(quantity: Quantity, params: list) -> None:
    """Fill in *quantity*'s domain from the settings entry its own ``setting=`` names.

    ``Capabilities.from_device`` resolves copies of the declarations, so this runs once per copy.
    With no *params* (``Capabilities.from_dict``), the domain was serialized with the quantity
    and there is nothing to derive.
    """
    if not params:
        return
    entry = find_param_entry(params, quantity.setting)
    if entry is None:
        raise ValueError(
            f'{quantity.name!r} declares setting={quantity.setting!r}, which is not a param '
            f'name declared anywhere in the plugin')
    ptype = entry.get('type')
    domain_from = _DOMAIN_FROM.get(ptype)
    if domain_from is not None:
        quantity.values = domain_from(entry)
        return
    bounds_from = _BOUNDS_FROM.get(ptype)
    if bounds_from is not None:
        quantity.lo, quantity.hi = bounds_from(entry)
        return
    raise ValueError(
        f'{quantity.name!r} declares setting={quantity.setting!r}, a {ptype!r} param - that type '
        f'has no corresponding Quantity domain')


def param_resolves_a_domain(params: list, name: str) -> bool:
    """Soft check for ``readback``'s auto-creation: unlike declaring ``setting=`` directly, naming
    a readback isn't an explicit request for it, so a miss here falls through to the laggy case
    instead of raising."""
    entry = find_param_entry(params, name)
    if entry is None:
        return False
    ptype = entry.get('type')
    return ptype in _DOMAIN_FROM or ptype in _BOUNDS_FROM


def quantity_for_setting(quantities: Iterable[Quantity], setting: str) -> Quantity | None:
    """The quantity among *quantities* whose ``setting=`` is *setting*, if any.

    Takes the collection as an argument rather than reading off a fixed object: a plugin's
    *instance* capabilities can replace ``Controller.capabilities`` wholesale after ``open()``,
    while ``HardwareModule``'s own rows stay built from whatever it was at construction - callers
    pass whichever collection actually matches what they're resolving against.
    """
    for quantity in quantities:
        if quantity.setting == setting:
            return quantity
    return None


def in_domain(quantity: Quantity, value: object) -> bool:
    """Whether *value* is within *quantity*'s own declared domain (``values``, or ``lo``/``hi``).

    Needed only for a ``setting=``-backed control: its write goes straight to the backing
    ``Parameter`` (see ``capabilities.apply_write``), never through a plugin ``set=``/``write()`` callback
    that could reject an out-of-range value itself, and pyqtgraph's own ``setValue`` doesn't clip
    to ``limits`` or reject a value outside them - it only coerces the value's type.

    ``not value >= lo`` / ``not value <= hi``, never the seemingly-equivalent ``value < lo`` /
    ``value > hi``: a comparison against ``float('nan')`` is always ``False``, so the ``<``/``>``
    form would never catch it and this would silently call a NaN in-domain; negating ``>=``/``<=``
    instead makes that same comparison reject it, same as any other out-of-domain value. May also
    raise (e.g. comparing an incompatible type) - left to the caller, see ``apply_write``.
    """
    if quantity.values:
        return value in quantity.values
    if quantity.lo is not None and not value >= quantity.lo:
        return False
    if quantity.hi is not None and not value <= quantity.hi:
        return False
    return True
