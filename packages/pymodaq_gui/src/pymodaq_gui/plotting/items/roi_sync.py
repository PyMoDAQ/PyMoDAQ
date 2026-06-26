import dataclasses
from pyqtgraph.parametertree.parameterTypes import SimpleParameter

from typing import Union

import numpy as np

from qtpy import QtCore, QtGui
from pyqtgraph.parametertree.Parameter import registerParameterType

from pymodaq_gui.parameter.pymodaq_ptypes import GroupParameter
from pymodaq_utils.config import GlobalConfig as Config

from pymodaq_data.plotting.utils import PlotColors
from pymodaq_data.post_treatment.process_to_scalar import DataProcessorFactory

from pymodaq_gui.plotting.items.roi import ROIDim, ROI, ROIFactory, LinearROI, mkColor, roi_format, plot_colors
from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode
from pymodaq_gui.parameter.ioxml import optional_int_options, optional_str_options


optional_int_options['index'] = None
optional_str_options['dim'] = None
optional_str_options['descriptor'] = None


data_processors = DataProcessorFactory()
ROI2D_TYPES = ROIFactory.get_descriptors_from_dimensionality(ROIDim.ROI2D)
config = Config()


@dataclasses.dataclass
class ROIParameterOptions:
    color: Union[QtGui.QColor, tuple[int, int, int]] = plot_colors[0]
    zlevel: int = 1
    x: float = 0.
    y: float = 0.
    width: float = 10.
    height: float = 10.
    angle: float = 0.


class RoiParameter(GroupParameter):

    def __init__(self, dim: ROIDim, descriptor: str, index: int = 0, **kwargs):
        kwargs.pop('type', None)
        kwargs.pop('name', None)
        removable = kwargs.pop('removable', True)
        context = kwargs.pop('context', ['Copy'])
        super().__init__(name=roi_format(index), type='roi_group',
                         removable=removable, context=context, **kwargs)
        self.opts['dim'] = dim
        self.opts['descriptor'] = descriptor
        self.opts['index'] = index

        self.roi_dim = dim
        self.index = index
        self.descriptor = descriptor
        if len(self.children()) == 0:
            if dim == ROIDim.ROI1D:
                self.addChildren(self.make_ROIParam1D(descriptor, index))
            elif dim == ROIDim.ROI2D:
                self.addChildren(self.make_ROIParam2D(descriptor, index))

    def to_options(self) -> ROIParameterOptions:
        options = ROIParameterOptions(
            color=self['color'],
            zlevel=self['zlevel'],
            x=self['position', 'x'],
            y=self['position', 'y'],
        )
        if self.roi_dim == ROIDim.ROI2D:
            options.width = self['size', 'width']
            options.height = self['size', 'height']
        return options


    @staticmethod
    def makeChannelsParam(dim=ROIDim.ROI2D):
        if dim == ROIDim.ROI2D:
            child = [{'title': 'Use channel', 'name': 'use_channel', 'type': 'itemselect', 'checkbox': True,
                      'value': dict(all_items=['red', 'green', 'blue'],
                                    selected=['red']),
                      }]
        else:
            child = [{'title': 'Use channel', 'name': 'use_channel', 'type': 'itemselect', 'checkbox': True}]
        return child

    @staticmethod
    def makeDisplayParam(index: int = 0, roi_dim=ROIDim.ROI1D):
        color = list(np.roll(plot_colors, index)[0])
        color = mkColor(color)
        if roi_dim == ROIDim.ROI1D:
            color.setAlpha(50)
        return [{'title': 'Color', 'name': 'color', 'type': 'color', 'value': color},
                {'name': 'zlevel', 'title': 'Z-level', 'type': 'int', 'expanded': False, 'value': 10}]

    @staticmethod
    def makeMathParam(dim: ROIDim = ROIDim.ROI2D):
        return [{'title': 'Math type:', 'name': 'math_function', 'type': 'list',
                 'limits': data_processors.functions_filtered(dim.map_to_datadim())}]

    @staticmethod
    def make_ROIParam2D(descriptor: str, index: int):
        children = []
        children.extend([{'title': 'Type', 'name': 'roi_type', 'type': 'list', 'value': descriptor,
                          'limits': ROI2D_TYPES, 'readonly': False}])
        children.append({'title': 'Process data', 'name': 'process_data', 'type': 'led_push',
                         'value': config.get(('utils', 'plotting', 'process_roi'), True)})
        children.extend(RoiParameter.makeChannelsParam(ROIDim.ROI2D))
        children.extend(RoiParameter.makeMathParam(ROIDim.ROI2D))
        children.extend(RoiParameter.makeDisplayParam(index, ROIDim.ROI2D))

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
        children.extend(RoiParameter.makeChannelsParam(ROIDim.ROI1D))
        children.extend(RoiParameter.makeMathParam(ROIDim.ROI1D))
        children.extend(RoiParameter.makeDisplayParam(index=index, roi_dim=ROIDim.ROI1D))
        children.extend([{'title': 'Position', 'name': 'position', 'type': 'group', 'children': [
            {'title': 'Left', 'name': 'x', 'type': 'float', 'value': 0, 'step': 1},
            {'title': 'Right', 'name': 'y', 'type': 'float', 'value': 10, 'step': 1},
        ]}])

        return children

    def roi_from_param(self, index: int) -> ROI:
        options = self.to_options()
        if self.roi_dim == ROIDim.ROI1D:
            return self.make_ROI(index, self.roi_dim, self.descriptor,
                          pos=(options.x, options.y),
                          color=options.color)
        else:
            return self.make_ROI(index, self.roi_dim, self.descriptor,
                          pos=(options.x, options.y),
                          size=(options.width, options.height),
                          color=options.color,
                          angle=options.angle,
                          )


    def make_ROI(self, index, roi_type: ROIDim, roi_descriptor: str,
                 pos=(0., 0.), size=(10., 10.), **kwargs) -> ROI:
        newindex = index
        if roi_type == ROIDim.ROI1D:
            roi = self.make_ROI1D(newindex, pos, **kwargs)
        elif roi_type == ROIDim.ROI2D:
            roi = self.make_ROI2D(roi_descriptor, newindex, pos, size, **kwargs)
        return roi

    def make_ROI1D(self, index, pos, compute=True, **kwargs) -> ROI:
        """Convenience function to make custom ROI_1D

        Args:
            index (int): Current index of ROI
            pos: Initial position of ROI

        Returns:
            roi: LinearROI
        """
        roi = ROIFactory.create(ROIDim.ROI1D,
                                ROIFactory.get_descriptors_from_dimensionality(ROIDim.ROI1D)[0],
                                index=index, pos=pos, compute=compute, **kwargs)
        # roi.setZValue(-10)
        #roi.setOpacity(0.2)
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

        return ROIFactory.create(ROIDim.ROI2D, descriptor,
                                 index=index, pos=pos,
                                 size=size, name=roi_format(index),
                                 compute=compute, **kwargs)

registerParameterType('roi_group', RoiParameter, override=True)


class ROISync(QtCore.QObject):

    def __init__(self, roi_dim: ROIDim,
                 roi_options=ROIParameterOptions()):

        super().__init__()
        self.roi_dim = roi_dim
        initial_value = {
            'color': roi_options.color,
            'zlevel': roi_options.zlevel,
            'x': roi_options.x,
            'y': roi_options.y,
        }
        if self.roi_dim == ROIDim.ROI2D:
            initial_value.update({
                'width': roi_options.width,
                'height': roi_options.height,
                'angle': roi_options.angle
            },
            )

        self.entries_sync = WidgetSync(
            initial_value=initial_value,
            validator=self.validator)

    @classmethod
    def sync_from_param(cls, param: RoiParameter):
        return cls(param.roi_dim, roi_options=param.to_options())

    def validator(self, value: dict) -> dict:
        for key in value:
            if isinstance(value[key], (ROI, LinearROI)):
                if key in ('x', 'y') and self.roi_dim == ROIDim.ROI2D:
                    if key == 'x':
                        value[key] = getattr(value[key], 'center')()[0]
                    else:
                        value[key] = getattr(value[key], 'center')()[1]
                else:
                    value[key] = getattr(value[key], key)()
            elif isinstance(value[key], QtGui.QColor) and self.roi_dim == ROIDim.ROI1D:
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

        if self.roi_dim == ROIDim.ROI1D:
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

        if self.roi_dim == ROIDim.ROI2D:
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



if __name__ == '__main__':
    import sys
    from qtpy import QtWidgets
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq_gui.parameter import ParameterTree

    app = mkQApp('RoiSync')

    from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D, generate_uniform_data


    widget_viewer = QtWidgets.QWidget()
    viewer = Viewer2D(widget_viewer)
    im = viewer.view.image_widget

    sync_2D = ROISync(ROIDim.ROI2D)
    sync_1D = ROISync(ROIDim.ROI1D)

    tree_2D = ParameterTree()
    tree_1D = ParameterTree()

    roi_2D = ROIFactory.create(ROIDim.ROI2D, 'EllipseROI')
    roi_2D_param = RoiParameter(ROIDim.ROI2D, 'EllipseROI')

    roi_1D = ROIFactory.create(ROIDim.ROI1D, 'LinearROI')
    roi_1D_param = RoiParameter(ROIDim.ROI1D, 'LinearROI', index=2)

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