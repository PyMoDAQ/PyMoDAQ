import pyqtgraph as pg

from  pymodaq_data.data import Axis
from pymodaq_utils import utils

AXIS_POSITIONS = ['top', 'bottom', 'right', 'left']


class AxisItem_Scaled(pg.AxisItem):
    """
    Subclass of pg.AxisItem enabling scaling of the tick values with respect to the linked viewbox
    """

    def __init__(self, *args, scaling=1, offset=0, **kwargs):
        """
        ==============  ===============================================================
        **Arguments:**
        orientation     one of 'left', 'right', 'top', or 'bottom'
        scaling         multiplicative coeff applied to the ticks
        offset          offset applied to the ticks after scaling
        maxTickLength   (px) maximum length of ticks to draw. Negative values draw
                        into the plot, positive values draw outward.
        linkView        (ViewBox) causes the range of values displayed in the axis
                        to be linked to the visible range of a ViewBox.
        showValues      (bool) Whether to display values adjacent to ticks
        pen             (QPen) Pen used when drawing ticks.
        ==============  ===============================================================
        """
        super().__init__(*args, **kwargs)
        self._scaling = scaling
        self._offset = offset

    def axis_data(self, Npts):
        return utils.linspace_step_N(self.axis_offset, self.axis_scaling, Npts)

    def set_scaling_and_label(self, axis_info: Axis):
        self.setLabel(axis_info.label, axis_info.units)
        self.axis_offset = axis_info.offset
        self.axis_scaling = axis_info.scaling

    @property
    def axis_label(self):
        return self.labelText

    @axis_label.setter
    def axis_label(self, label: str):
        self.setLabel(text=label, units=self.axis_units)

    @property
    def axis_units(self):
        return self.labelUnits

    @axis_units.setter
    def axis_units(self, units: str):
        self.setLabel(text=self.axis_label, units=units)

    @property
    def axis_scaling(self):
        return self._scaling

    @axis_scaling.setter
    def axis_scaling(self, scaling_factor=1):
        self._scaling = scaling_factor
        self.linkedViewChanged()

    @property
    def axis_offset(self):
        return self._offset

    @axis_offset.setter
    def axis_offset(self, offset=0):
        self._offset = offset
        self.linkedViewChanged()

    def linkedViewChanged(self, view=None, newRange=None):
        if view is None:
            if self.linkedView() is not None:
                view = self.linkedView()
            else:
                return

        if self.orientation in ['right', 'left']:
            if newRange is None:
                newRange = [pos * self._scaling + self._offset for pos in view.viewRange()[1]]
            else:
                newRange = [pos * self._scaling + self._offset for pos in newRange]
        else:
            if newRange is None:
                newRange = [pos * self._scaling + self._offset for pos in view.viewRange()[0]]
            else:
                newRange = [pos * self._scaling + self._offset for pos in newRange]

        super().linkedViewChanged(view, newRange=newRange)