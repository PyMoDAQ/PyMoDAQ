from collections.abc import Mapping
from typing import TYPE_CHECKING, Any
import numpy as np

from qtpy import QtWidgets, QtCore

from serializall import SerializableFactory
from pymodaq_data import DataToExport, DataWithAxes, DataRaw
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()

@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class WaitElt(SeqEltBase):

    elt_name = 'wait'
    children_allowed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.done)

        self._wait_time_ms: int = 100

    @property
    def wait_time(self) -> int:
        return self._wait_time_ms

    @wait_time.setter
    def wait_time(self, value: int):
        self._wait_time_ms = value

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        spin_box = SpinBox(parent=base_widget,
                           value=self.wait_time,
                           int=True, suffix='ms', siPrefix=False)
        base_widget.add_widget_top(spin_box)
        spin_box.sigValueChanged.connect(self.set_wait_time_from_spinbox)
        base_widget.give_focus_to(spin_box)

        return base_widget

    def set_wait_time_from_spinbox(self, spinbox: SpinBox):
        self.wait_time = spinbox.value()

    def _execute(self, dte: DataToExport = None):
        print(f'Starting Wait Timer for {self.wait_time} ms')
        self.timer.setInterval(int(self.wait_time))
        self.timer.start()

    def done(self):
        self.done_signal.emit()

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return {'wait_time': self.wait_time}

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.wait_time = dict_config.pop('wait_time')

    def _eq(self, other: 'WaitElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        if not hasattr(other, 'wait_time'):
            return False
        return self.wait_time == other.wait_time

    def __repr__(self):
        return f'{super().__repr__()} - {self.wait_time}ms'

    def check_set_is_valid(self):
        if self.wait_time is None:
            raise ElementError(f'Wait time of element {self} should not be None')
        if self.wait_time < 0:
            raise ElementError(f'Wait time of element {self} should not be negative')
