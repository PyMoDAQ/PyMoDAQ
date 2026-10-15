"""The Qt widget built for a control's own representation ('value'/'selector'/'toggle'), and the
registry of what each one needs - kept separate from :mod:`~pymodaq.control_modules.hardware_module`
itself, the same way :mod:`pymodaq_gui.plotting.data_viewers.viewer`'s ``ViewerFactory`` keeps its own
builders apart from whatever widget ends up consuming a viewer.

:class:`RepresentationFactory` (built on :class:`~pymodaq_utils.factory.ObjectFactory`, the same base
class ``ViewerFactory`` uses) registers one :class:`RepresentationRule` per representation kind, each
through its own ``@RepresentationFactory.register(...)``-decorated function below - adding a fourth
kind means registering a new one, not editing a shared dict.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from qtpy import QtWidgets

from pymodaq_utils.factory import ObjectFactory

from pymodaq.control_modules.hardware.capabilities import Quantity

__all__ = ['RepresentationRule', 'RepresentationFactory', 'representation_of']


def _toggle_text(widget: QtWidgets.QAbstractButton, value: Any) -> None:
    widget.setText(str(value))


@dataclass(frozen=True)
class RepresentationRule:
    """How one control representation ('value'/'selector'/'toggle') is built: the default Qt class,
    the Qt property that holds the device value, and the signal meaning "the user committed an edit"
    - deliberately explicit, not auto-detected from Qt's own property-change notify signal, because
    that's the wrong signal here: a spinbox's registered NOTIFY for 'value' is valueChanged, which
    fires on every keystroke, not editingFinished, which is what a write actually wants (see
    device_module_status.md for why the write direction needs "committed," not "changed").

    ``to_widget``/``from_widget`` convert between the device value and the widget property's own
    value, where they differ (a selector's property is an index, a toggle's is a bool) - identity for
    a plain float passthrough ('value'). ``extra_setter``, when given, runs after the property setter
    for anything the property alone doesn't cover (a toggle's own button text).

    ``widget_class=`` (see :func:`~pymodaq.control_modules.hardware.capabilities.control`) substitutes
    ``default_class`` with any class exposing the same property and signal - checked in
    :mod:`~pymodaq.control_modules.hardware_module`, not in ``capabilities.py``, since that module
    stays Qt-free and a Qt property's name doesn't always match its Python getter
    (``QPushButton.checked`` reads through ``isChecked()``, not ``checked()``), so there is nothing
    reliable to check without an actual instance.
    """

    default_class: type
    property_name: str
    commit_signal: str
    to_widget: Callable[[Any, Quantity], Any] = staticmethod(lambda value, quantity: value)
    from_widget: Callable[[Any, Quantity], Any] = staticmethod(lambda value, quantity: value)
    extra_setter: Callable[[QtWidgets.QWidget, Any], None] | None = None


class RepresentationFactory(ObjectFactory):
    """One :class:`RepresentationRule` per representation kind, each registered on its own below -
    not one central dict something else has to find and edit to add a fourth kind."""


@RepresentationFactory.register('value')
def _value_representation(**_ignored) -> RepresentationRule:
    return RepresentationRule(
        default_class=QtWidgets.QDoubleSpinBox, property_name='value', commit_signal='editingFinished')


@RepresentationFactory.register('selector')
def _selector_representation(**_ignored) -> RepresentationRule:
    return RepresentationRule(
        default_class=QtWidgets.QComboBox, property_name='currentIndex', commit_signal='activated',
        to_widget=lambda value, quantity: quantity.values.index(value),
        from_widget=lambda index, quantity: quantity.values[index])


@RepresentationFactory.register('toggle')
def _toggle_representation(**_ignored) -> RepresentationRule:
    return RepresentationRule(
        default_class=QtWidgets.QPushButton, property_name='checked', commit_signal='toggled',
        to_widget=lambda value, quantity: quantity.values.index(value) == 1,
        from_widget=lambda checked, quantity: quantity.values[1 if checked else 0],
        extra_setter=_toggle_text)


def representation_of(quantity: Quantity) -> str:
    """Which single widget this control's value is shown/edited through - the same choice
    :func:`~pymodaq.control_modules.hardware.capabilities.toolbar_widgets` already makes: 'value' for a
    continuous control, 'selector' for a discrete one, or 'toggle' when ``widget='toggle'`` asked
    for the two-valued override."""
    if not quantity.values:
        return 'value'
    return quantity.widget or 'selector'
