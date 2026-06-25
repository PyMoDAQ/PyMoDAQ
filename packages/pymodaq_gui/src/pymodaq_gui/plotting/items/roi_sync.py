from typing import Union

import numpy as np

from qtpy import QtCore, QtGui
from pyqtgraph.parametertree.Parameter import registerParameterType

from pymodaq_gui.parameter.pymodaq_ptypes import GroupParameter
from pymodaq_utils.config import GlobalConfig as Config

from pymodaq_data.plotting.utils import PlotColors
from pymodaq_data.post_treatment.process_to_scalar import DataProcessorFactory

from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.managers.roi_manager import plot_colors, roi_format
from pymodaq_gui.plotting.items.roi import DataDim, ROI, ROIFactory, LinearROI
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


plot_colors = PlotColors()
data_processors = DataProcessorFactory()
ROI2D_TYPES = ROIFactory.get_descriptors_from_dimensionality(DataDim.Data2D)
config = Config()

ROI_NAME_PREFIX = 'ROI_'

def roi_format(index):
    return f'{ROI_NAME_PREFIX}{index:02d}'


class RoiParameter(GroupParameter):

    def __init__(self, dim: DataDim, descriptor: str, index: int = 0):

        super().__init__(name=roi_format(index), type='group')

        if dim == DataDim.Data1D:
            self.addChildren(self.make_ROIParam1D(descriptor, index))
        elif dim == DataDim.Data2D:
            self.addChildren(self.make_ROIParam2D(descriptor, index))

    @staticmethod
    def makeChannelsParam(dim=DataDim.Data2D):
        if dim == DataDim.Data2D:
            child = [{'title': 'Use channel', 'name': 'use_channel', 'type': 'itemselect', 'checkbox': True,
                      'value': dict(all_items=['red', 'green', 'blue'],
                                    selected=['red']),
                      }]
        else:
            child = [{'title': 'Use channel', 'name': 'use_channel', 'type': 'itemselect', 'checkbox': True}]
        return child

    @staticmethod
    def makeDisplayParam(index: int = 0):
        return [{'title': 'Color', 'name': 'color', 'type': 'color', 'value': list(np.roll(plot_colors, index)[0])},
                {'name': 'zlevel', 'title': 'Z-level', 'type': 'int', 'expanded': False, 'value': 10}]

    @staticmethod
    def makeMathParam(dim: DataDim = DataDim.Data2D):
        return [{'title': 'Math type:', 'name': 'math_function', 'type': 'list',
                 'limits': data_processors.functions_filtered(dim)}]

    @staticmethod
    def make_ROIParam2D(descriptor: str, index: int):
        children = []
        children.extend([{'title': 'Type', 'name': 'roi_type', 'type': 'list', 'value': descriptor,
                          'limits': ROI2D_TYPES, 'readonly': False}])
        children.append({'title': 'Process data', 'name': 'process_data', 'type': 'led_push',
                         'value': config.get(('utils', 'plotting', 'process_roi'), True)})
        children.extend(RoiParameter.makeChannelsParam(DataDim.Data2D))
        children.extend(RoiParameter.makeMathParam(DataDim.Data2D))
        children.extend(RoiParameter.makeDisplayParam(index))

        children.extend([{'title': 'Center', 'name': 'position', 'type': 'group', 'expanded': False, 'children': [
            {'name': 'x', 'type': 'float', 'value': 0, 'step': 1, 'decimals': 6},
            {'name': 'y', 'type': 'float', 'value': 0, 'step': 1, 'decimals': 6},
        ]}])
        children.extend([
            {'name': 'size', 'type': 'group', 'expanded': False, 'children': [
                {'name': 'width', 'type': 'float', 'value': 10, 'step': 1, 'decimals': 6},
                {'name': 'height', 'type': 'float', 'value': 10, 'step': 1, 'decimals': 6},
            ]},
            {'name': 'angle', 'type': 'float', 'value': 0, 'step': 1}])
        return children

    @staticmethod
    def make_ROIParam1D(descriptor: str, index: int):
        children = []
        children.append({'title': 'Process data', 'name': 'process_data', 'type': 'led_push',
                         'value': config.get(('utils', 'plotting', 'process_roi'), True)})
        children.extend(RoiParameter.makeChannelsParam(DataDim.Data1D))
        children.extend(RoiParameter.makeMathParam(DataDim.Data1D))
        children.extend(RoiParameter.makeDisplayParam(index=index))
        children.extend([{'title': 'Position', 'name': 'position', 'type': 'group', 'children': [
            {'title': 'Left', 'name': 'x', 'type': 'float', 'value': 0, 'step': 1},
            {'title': 'Right', 'name': 'y', 'type': 'float', 'value': 10, 'step': 1},
        ]}])

        return children


registerParameterType('roi', RoiParameter, override=True)


class ROISync(QtCore.QObject):

    def __init__(self, roi_type: DataDim,
                 color: Union[QtGui.QColor, tuple[int, int, int]] = plot_colors[0],
                 zlevel=1,
                 x=0, y=0,
                 width=10, height=10,
                 angle=0
                 ):
        super().__init__()
        self.roi_type = roi_type
        initial_value = {
            'color': color,
            'zlevel': zlevel,
            'x': x,
            'y': y,
        }
        if self.roi_type == DataDim.Data2D:
            initial_value.update({
                'width': width,
                'height': height,
                'angle': angle
            },
            )

        self.entries_sync = WidgetSync(
            initial_value=initial_value,
            validator=self.validator)

    def validator(self, value: dict) -> dict:
        for key in value:
            if isinstance(value[key], (ROI, LinearROI)):
                if key in ('x', 'y') and self.roi_type == DataDim.Data2D:
                    if key == 'x':
                        value[key] = getattr(value[key], 'center')()[0]
                    else:
                        value[key] = getattr(value[key], 'center')()[1]
                else:
                    value[key] = getattr(value[key], key)()
            elif isinstance(value[key], QtGui.QColor) and self.roi_type == DataDim.Data1D:
                value[key].setAlphaF(0.3)
        return value

    def sync_entries_with(self, roi: ROI, roi_parameter: RoiParameter):
        roi_property_map = {
            'color': {
                'setter': roi.set_color,
                'mode': SyncMode.FROM_SYNC,
            },
            'zlevel': {
                'setter': roi.setZValue,
                'mode': SyncMode.FROM_SYNC,
            },
        }

        parameter_property_map = {
            'color': {'param': roi_parameter.child('color')},
            'zlevel': {'param': roi_parameter.child('zlevel')},
            'x': {'param': roi_parameter.child('position', 'x')},
            'y': {'param': roi_parameter.child('position', 'y')},
        }

        if self.roi_type == DataDim.Data1D:
            roi_property_map.update({
                'x': {
                    'signal': roi.sigRegionChangeFinished,
                    'getter':  roi.x,
                    'setter': roi.set_x,
                    'mode': SyncMode.BIDIRECTIONAL,
                },
                'y': {
                    'signal': roi.sigRegionChangeFinished,
                    'getter': roi.y,
                    'setter': roi.set_y,
                    'mode': SyncMode.BIDIRECTIONAL,
                },})

        if self.roi_type == DataDim.Data2D:
            parameter_property_map.update({
                'width': {'param': roi_parameter.child('size', 'width')},
                'height': {'param': roi_parameter.child('size', 'height')},
                'angle': {'param': roi_parameter.child('angle')},
            },
            )

            roi_property_map.update({
                'x': {
                    'signal': roi.sigRegionChangeFinished,
                    'getter': lambda: roi.center()[0],
                    'setter': lambda cx: roi.set_center((cx, roi.center()[1])),
                    'mode': SyncMode.BIDIRECTIONAL,
                },
                'y': {
                    'signal': roi.sigRegionChangeFinished,
                    'getter': lambda: roi.center()[1],
                    'setter': lambda cy: roi.set_center((roi.center()[0], cy)),
                    'mode': SyncMode.BIDIRECTIONAL,
                },
                'width': {
                    'signal': roi.sigRegionChangeFinished,
                    'getter': roi.width,
                    'setter': roi.set_width,
                    'mode': SyncMode.BIDIRECTIONAL,
                },
                'height': {
                    'signal': roi.sigRegionChangeFinished,
                    'getter': roi.height,
                    'setter': roi.set_height,
                    'mode': SyncMode.BIDIRECTIONAL,
                },
                'angle': {
                    'signal': roi.sigRegionChangeFinished,
                    'getter': roi.angle,
                    'setter': lambda angle: roi.setAngle(angle, center=(0.5, 0.5)),
                    'mode': SyncMode.BIDIRECTIONAL,
                },
                })

        self.entries_sync.bind_properties(
            roi,
            property_map=roi_property_map
        )
        self.entries_sync.bind_parameter(
            roi_parameter,
            property_map=parameter_property_map
        )

    def make_ROI(self, index, roi_type: DataDim, roi_descriptor: str, view_range = ((0, 10), (0, 10))) -> ROI:
        newindex = index
        if roi_type == DataDim.Data1D:

            pos = view_range[0]
            pos = view_range[0] + np.diff(view_range)*np.array([2,4])/6
            roi = self.make_ROI1D(newindex, pos)
        elif roi_type == DataDim.Data2D:
            xrange, yrange = view_range
            width = np.max(((xrange[1] - xrange[0]) / 10, 2))
            height = np.max(((yrange[1] - yrange[0]) / 10, 2))
            pos = [int(np.mean(xrange) - width / 2), int(np.mean(yrange) - width / 2)]
            roi = self.make_ROI2D(roi_descriptor, index=newindex, pos=pos, size=[width, height])
        return roi

    def make_ROI1D(self, index, pos, compute=True, **kwargs) -> ROI:
        """Convenience function to make custom ROI_1D

        Args:
            index (int): Current index of ROI
            pos: Initial position of ROI

        Returns:
            roi: LinearROI
        """
        roi = ROIFactory.create(DataDim.Data1D,
                                ROIFactory.get_descriptors_from_dimensionality(DataDim.Data1D)[0],
                                index=index, pos=pos, compute=compute, **kwargs)
        # roi.setZValue(-10)
        roi.setOpacity(0.2)
        return roi

    def make_ROI2D(self, descriptor: str, index, pos, size, compute=True, **kwargs) -> ROI:
        """Convenience function to make custom ROI_2D

        Args:
            descriptor (str): name of 2D ROI
            index (int): Current index of ROI
            pos: Initial position of ROI
            size: Initial size of ROI

        Returns:
            roi: pg.ROI
        """

        return ROIFactory.create(DataDim.Data2D, descriptor,
                                 index=index, pos=pos,
                                 size=size, name=roi_format(index),
                                 compute=compute, **kwargs)


if __name__ == '__main__':
    import sys
    from qtpy import QtWidgets
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq_gui.parameter import ParameterTree

    app = mkQApp('RoiSync')

    from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D, generate_uniform_data
    from pymodaq_gui.plotting.widgets import ImageWidget
    from pyqtgraph import PlotWidget

    widget_viewer = QtWidgets.QWidget()
    viewer = Viewer2D(widget_viewer)
    im = viewer.view.image_widget

    sync_2D = ROISync(DataDim.Data2D)
    sync_1D = ROISync(DataDim.Data1D)

    tree_2D = ParameterTree()
    tree_1D = ParameterTree()

    roi_2D = ROIFactory.create(DataDim.Data2D, 'EllipseROI')
    roi_2D_param = RoiParameter(DataDim.Data2D, 'EllipseROI')

    roi_1D = ROIFactory.create(DataDim.Data1D, 'LinearROI')
    roi_1D_param = RoiParameter(DataDim.Data1D, 'LinearROI', index=2)

    tree_2D.setParameters(roi_2D_param)
    tree_1D.setParameters(roi_1D_param)

    dwa = generate_uniform_data()
    viewer.show_data(dwa)

    im.plotItem.addItem(roi_2D)
    im.plotItem.addItem(roi_1D)
    widget_viewer.show()
    tree_2D.show()
    tree_1D.show()

    sync_2D.sync_entries_with(roi_2D, roi_2D_param)
    sync_1D.sync_entries_with(roi_1D, roi_1D_param)

    sync_1D.entries_sync.set_value(sync_1D.entries_sync.value, emit=True)
    sync_2D.entries_sync.set_value(sync_2D.entries_sync.value, emit=True)

    sys.exit(app.exec())