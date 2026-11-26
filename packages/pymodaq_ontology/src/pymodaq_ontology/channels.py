"""The channels of the instruments of the Dashboard

A *channel* is what an ontology term is assigned to:

* a detector emits data (``DataWithAxes``), each array of which is a channel (its label is the name of the channel)
* an actuator is one channel, named after the module
"""
from dataclasses import dataclass
from typing import Iterable, Optional

from pymodaq_ontology.terms import ACTUATOR, DETECTOR


@dataclass(frozen=True)
class Channel:
    """A channel of an instrument

    The key identifies it in the entry files: ``module/data name/label`` for a detector, ``module`` for an actuator.
    """
    module: str
    kind: str  # DETECTOR or ACTUATOR
    data_name: str = ''
    label: str = ''
    units: str = ''
    last_value: str = ''

    @property
    def key(self) -> str:
        if self.kind == ACTUATOR:
            return self.module
        return f'{self.module}/{self.data_name}/{self.label}'

    @property
    def name(self) -> str:
        """What the user sees as the name of the channel"""
        if self.kind == ACTUATOR:
            return self.module
        return f'{self.data_name}/{self.label}'


def _scalar(array) -> str:
    """The value of an array of one element as text, empty for anything else"""
    try:
        if array.size == 1:
            return f'{float(array.ravel()[0]):.6g}'
    except (TypeError, ValueError, AttributeError):
        pass
    return ''


def detector_channels(data: Iterable) -> list[Channel]:
    """The channels found in data emitted by detectors (``DataWithAxes`` objects, for instance the ``data`` of a
    ``DataToExport``)"""
    channels = []
    for dwa in data:
        labels = list(dwa.labels) if getattr(dwa, 'labels', None) else []
        for index, array in enumerate(dwa.data):
            label = labels[index] if index < len(labels) else f'CH{index:02d}'
            channels.append(Channel(module=dwa.origin, kind=DETECTOR, data_name=dwa.name, label=label,
                                    units=getattr(dwa, 'units', '') or '', last_value=_scalar(array)))
    return channels


def actuator_channels(actuators: Iterable) -> list[Channel]:
    """One channel for each actuator (``DAQ_Move``) given"""
    return [Channel(module=actuator.title, kind=ACTUATOR, units=getattr(actuator, 'units', '') or '',
                    last_value=_scalar(_current_array(actuator)))
            for actuator in actuators]


def _current_array(actuator) -> Optional[object]:
    try:
        return actuator._current_value.data[0]
    except (AttributeError, IndexError, TypeError):
        return None
