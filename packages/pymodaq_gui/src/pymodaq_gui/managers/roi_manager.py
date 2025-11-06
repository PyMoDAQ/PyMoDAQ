
import os
import sys
from typing import List, TYPE_CHECKING, Tuple, Union

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QObject, Slot, Signal,QSignalBlocker
from qtpy.QtGui import QIcon, QPixmap
from collections import OrderedDict

import pyqtgraph.Point as Point

from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import ParameterTree, Parameter, ioxml, pymodaq_ptypes
from pyqtgraph.parametertree.parameterTypes.basetypes import GroupParameter

from pymodaq_gui.managers.action_manager import QAction

from pymodaq_utils.utils import plot_colors
from pymodaq_utils.logger import get_module_name, set_logger
from pymodaq_utils.config import Config
from pymodaq_gui.config_saver_loader import get_set_roi_path
from pymodaq_gui.utils import select_file
from pymodaq_gui.plotting.items.roi import ROIFactory, ROI, LinearROI, RectROI, DataDim


import numpy as np
from pathlib import Path
from pymodaq_data.post_treatment.process_to_scalar import DataProcessorFactory
from pymodaq_gui.utils.utils import first_available_integer

data_processors = DataProcessorFactory()

roi_path = get_set_roi_path()
logger = set_logger(get_module_name(__file__))
config = Config()


ROI_NAME_PREFIX = 'ROI_'
ROI2D_TYPES = ROIFactory.get_descriptors_from_dimensionality(DataDim.Data2D)


def roi_format(index):
    return f'{ROI_NAME_PREFIX}{index:02d}'


class ROIScalableGroup(GroupParameter):
    def __init__(self, roi_type = DataDim.Data1D, **opts):
        opts['type'] = 'group'
        opts['addText'] = "Add"
        self.roi_type = roi_type
        if roi_type == DataDim.Data2D:
            opts['addList'] = ROI2D_TYPES
        # self.color_list = ROIManager.color_list
        super().__init__(**opts)

    def addNew(self, typ=''):
        name_prefix = ROI_NAME_PREFIX
        child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]
        if not child_indexes:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

        self.addChild(self.makeChild(newindex, typ))


    def makeChild(self, index, descriptor: str):
        child = {'name': ROIManager.roi_format(index), 'type': 'bool','value':True, 'removable': True, 'renamable': False, 'expanded': False,'context':['Copy',]}
        if self.roi_type == DataDim.Data2D:
            child['children'] = ROIScalableGroup.make_ROIParam2D(descriptor, index)
        elif self.roi_type == DataDim.Data1D:
            child['children'] = ROIScalableGroup.make_ROIParam1D(descriptor, index)
        return child  
    
    @staticmethod
    def makeChannelsParam(dim=DataDim.Data2D):
        if dim == DataDim.Data2D:
            child = [{'title': 'Use channel', 'name': 'use_channel', 'type': 'itemselect', 'checkbox': True,
                      'value': dict(all_items=['red', 'green', 'blue'],
                           selected=['red',]),
                              },]
        else:
            child = [{'title': 'Use channel', 'name': 'use_channel', 'type': 'itemselect','checkbox': True},]
        return child 

    @staticmethod
    def makeDisplayParam(index):
        return [{'name': 'Color', 'type': 'color', 'value': list(np.roll(ROIManager.color_list, index)[0])},
             {'name': 'zlevel', 'title':'Z-level','type': 'int', 'expanded': False, 'value':10},] 
        
    @staticmethod
    def makeMathParam(dim=DataDim.Data2D):
        return [{'title': 'Math type:', 'name': 'math_function', 'type': 'list',
                             'limits': data_processors.functions_filtered(dim)},]
    @staticmethod    
    def make_ROIParam2D(descriptor: str, index):
            children = []    
            children.extend([{'title': 'Type', 'name': 'roi_type', 'type': 'list', 'value': descriptor,
                              'limits': ROI2D_TYPES, 'readonly': False,}])
            children.append({'title': 'Process data', 'name': 'process_data', 'type': 'led_push',
                             'value': config.get(('plotting', 'process_roi'), True),})
            children.extend(ROIScalableGroup.makeChannelsParam(DataDim.Data2D))
            children.extend(ROIScalableGroup.makeMathParam(DataDim.Data2D))
            children.extend(ROIScalableGroup.makeDisplayParam(index))
            children.extend([{'name': 'center', 'type': 'group', 'expanded': False, 'children': [
                    {'name': 'x', 'type': 'float', 'value': 0, 'step': 1,'decimals':6},
                    {'name': 'y', 'type': 'float', 'value': 0, 'step': 1,'decimals':6}
                ]}, ])                
            children.extend([{'name': 'position', 'type': 'group', 'expanded': False, 'children': [
                    {'name': 'x', 'type': 'float', 'value': 0, 'step': 1,'decimals':6},
                    {'name': 'y', 'type': 'float', 'value': 0, 'step': 1,'decimals':6}
                ]}, ])          
            children.extend([
                    {'name': 'size', 'type': 'group', 'expanded': False, 'children': [
                        {'name': 'width', 'type': 'float', 'value': 10, 'step': 1,'decimals':6},
                        {'name': 'height', 'type': 'float', 'value': 10, 'step': 1,'decimals':6}
                    ]},
                    {'name': 'angle', 'type': 'float', 'value': 0, 'step': 1}])    
            return children

    @staticmethod    
    def make_ROIParam1D(descriptor: str, index):
            children = []
            children.append({'title': 'Process data', 'name': 'process_data', 'type': 'led_push',
                             'value': config.get(('plotting', 'process_roi'), True),})
            children.extend(ROIScalableGroup.makeChannelsParam(DataDim.Data1D))
            children.extend(ROIScalableGroup.makeMathParam(DataDim.Data1D))
            children.extend(ROIScalableGroup.makeDisplayParam(index))
            children.extend([{'name': 'position', 'type': 'group', 'children': [
                {'name': 'left', 'type': 'float', 'value': 0, 'step': 1},
                {'name': 'right', 'type': 'float', 'value': 10, 'step': 1}
                    ]}, ])
            
            return children



class ROIManager(QObject):

    new_ROI_signal = Signal(str)
    remove_ROI_signal = Signal(str)
    roi_value_changed = Signal(str, tuple)
    color_signal = Signal(list)
    roi_update_children = Signal(list)
    roi_changed = Signal()
    color_list = np.array(plot_colors)

    def __init__(self, viewer_widget=None, ROI_type=DataDim.Data1D):
        super().__init__()
        self.ROI_type = ROI_type
        self.roiwidget = QtWidgets.QWidget()
        self.viewer_widget = viewer_widget  # either a PlotWidget or a ImageWidget
        self._ROIs: OrderedDict[str, ROI] = OrderedDict([])
        self.setupUI()

    @staticmethod
    def roi_format(index):
        logger.warning(f'ROIManager.roi_format is deprecated, use roi_format')
        return roi_format(index)
    
    @property
    def ROIs(self):
        return self._ROIs
    
    def __len__(self):
        return len(self._ROIs)

    def get_roi_from_index(self, index: int) -> ROI:
        return self.ROIs[roi_format(index)]

    def _set_roi_from_index(self, index: int, roi):
        self.ROIs[roi_format(index)] = roi

    def get_roi(self, roi_key):
        if roi_key in self.ROIs:
            return self.ROIs[roi_key]
        else:
            raise KeyError(f'{roi_key} is not a valid ROI identifier for {self.ROIs}')

    def emit_colors(self):
        self.color_signal.emit([self._ROIs[roi_key].color for roi_key in self._ROIs])

    def add_roi_programmatically(self, descriptor: str = ROI2D_TYPES[0]):
        self.settings.child('ROIs').addNew(descriptor)

    def remove_roi_programmatically(self, index: int):
        self.settings.child('ROIs').removeChild(self.settings.child('ROIs', roi_format(index)))

    def setupUI(self):

        vlayout = QtWidgets.QVBoxLayout()
        self.roiwidget.setLayout(vlayout)

        self.toolbar = QtWidgets.QToolBar()
        vlayout.addWidget(self.toolbar)

        self.save_ROI_pb = QAction(QIcon(QPixmap("icons:save_ROI.png")), 'Save ROIs')
        self.load_ROI_pb = QAction(QIcon(QPixmap("icons:load_ROI.png")), 'Load ROIs')
        self.clear_ROI_pb = QAction(QIcon(QPixmap("icons:clear_ROI.png")), 'Clear ROIs')
        self.toolbar.addActions([self.save_ROI_pb, self.load_ROI_pb, self.clear_ROI_pb])


        self.roitree = ParameterTree()
        vlayout.addWidget(self.roitree)
        self.roiwidget.setMinimumWidth(250)
        self.roiwidget.setMaximumWidth(300)

        params = [
            {'title': 'Measurements:', 'name': 'measurements', 'type': 'table', 'value': OrderedDict([]), 'Ncol': 2,
             'header': ["LO", "Value"]},
            ROIScalableGroup(roi_type=self.ROI_type, name="ROIs")]
        self.settings = Parameter.create(title='ROIs Settings', name='rois_settings', type='group', children=params)
        self.roitree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.roi_tree_changed)
        self.settings_signalBlocker = QSignalBlocker(self.settings)
        self.settings_signalBlocker.unblock()

        self.save_ROI_pb.triggered.connect(self.save_ROI)
        self.load_ROI_pb.triggered.connect(lambda: self.load_ROI(None))
        self.clear_ROI_pb.triggered.connect(self.clear_ROI)

    def get_ROI_indexes(self,):
        return [roi.index for roi in self.ROIs.values()]

    def roi_tree_changed(self, param, changes):

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':  # new roi to create
                par: Parameter = data[0]
                roi = self.make_ROI(par)                
                self.add_ROI(roi)
                self.emit_colors()
                self.roi_changed.emit()

            elif change == 'value':
                if param.name() in putils.iter_children(self.settings.child('ROIs'), []):
                    parent_name = putils.get_param_path(param)[putils.get_param_path(param).index('ROIs')+1]
                    if parent_name in self._ROIs.keys():
                        roi_changed = self._ROIs[parent_name]                                    
                        self.update_roi(roi_changed, param)
                    self.roi_value_changed.emit(parent_name, (param, param.value()))
                if param.name() == 'Color':
                    self.emit_colors()
            elif change == 'parent':
                if 'ROI' in param.name():
                    self.remove_ROI(self.ROIs[param.name()])

            elif change == 'contextMenu':  # MenuSel
                if data=='Copy':
                    self.copy_ROI(self.ROIs[param.name()])                    

    def make_ROI(self, param: Parameter):
        newindex = int(param.name()[-2:])
        pos = self.viewer_widget.plotItem.vb.viewRange()
        if self.ROI_type == DataDim.Data1D:
            descriptor = ''
            pos = pos[0]
            pos = pos[0] + np.diff(pos)*np.array([2,4])/6
            roi = self.make_ROI1D(newindex, pos, brush=param['Color'],
                                  compute=param['process_data'])
        elif self.ROI_type == DataDim.Data2D:
            descriptor = param.child('roi_type').value()
            xrange,yrange=pos                    
            width = np.max(((xrange[1] - xrange[0]) / 10, 2))
            height = np.max(((yrange[1] - yrange[0]) / 10, 2))
            pos = [int(np.mean(xrange) - width / 2), int(np.mean(yrange) - width / 2)]
            roi = self.make_ROI2D(descriptor, index=newindex, pos=pos,size=[width, height],
                                  pen=param['Color'], compute=param['process_data'])

        return roi

    def add_ROI(self, roi):
        # Connection roi signals to relevant function
        roi.sigRegionChangeFinished.connect(lambda: self.roi_changed.emit())
        roi.sigRegionChangeFinished.connect(self.update_roi_tree)
        roi.sigRemoveRequested.connect(self.remove_ROI)
        roi.sigCopyRequested.connect(self.copy_ROI)        
        roi.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton) 
        roi.sigDoubleClicked.connect(self.expand_roi_tree)
        # Updating tree
        self.update_roi_tree(roi)
        # Adding to dictionnary
        self.ROIs[roi.key()] = roi
        # Adding to viewer
        self.viewer_widget.plotItem.addItem(roi)  
        # Emitting signal
        self.new_ROI_signal.emit(roi.key())

    def expand_roi_tree(self, roi,):
        # Expand roi tree when roi gets double selected
        param = self.settings.child(*('ROIs', roi_format(roi.index)))
        isExpanded = not param.opts['expanded']
        param.setOpts(expanded=isExpanded)

    def make_ROI1D(self, index, pos, compute=True, **kwargs):
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

    def make_ROI2D(self, descriptor: str, index, pos, size, compute=True, **kwargs):
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
    
    def remove_ROI(self, roi):
        """Function to remove roi from dict and widget

        Args:
            roi (pg.ROI): roi to be removed
        """
        roi_group = self.settings.child('ROIs')
        for param in roi_group.children():                
                if roi.key() == param.name():
                    self.settings_signalBlocker.reblock()
                    roi_group.removeChild(param)
                    self.settings_signalBlocker.unblock()
        roi = self.ROIs.pop(roi.key())
        self.viewer_widget.plotItem.removeItem(roi)
        self.remove_ROI_signal.emit(roi.key())
        self.emit_colors()

    def copy_ROI(self, roi: ROI):
        """Method to copy a ROI and add it to the parameter tree and to the viewer widget
        The method extracts the parameters of the copied ROI, create a new parameter, a new ROI and update it with the settings from the copied parameter
        Args:
            roi (ROI): the ROI to be copied
        """
        index = first_available_integer(self.get_ROI_indexes()) 
        
        roi_group = self.settings.child('ROIs')
        #Copy parameter and edit name
        param_roi = self.get_parameter(roi)
        param = param_roi.saveState() # Transforming parameter in dict
        param['name'] = roi_format(index) # Changing name   
        param = Parameter.create(**param) # Transforming dict in parameter
        self.settings_signalBlocker.reblock()
        roi_group.addChild(param)
        self.settings_signalBlocker.unblock()
        new_roi = self.make_ROI(param)

        param_to_update = putils.iter_children_params(param_roi,[],filter_name=('roi_type',),filter_type=('group',)) # Parameters to update
        # [self.update_roi(new_roi,p) for p in reversed(param_to_update)]     
        self.add_ROI(new_roi)
        [self.update_roi(new_roi,p) for p in reversed(param_to_update)]     


    def update_use_channel(self, channels: List[str], index=None):
        """Function to update the selected channels. If no index is given, the channels are applied to all ROIs.

        Args:
            channels (List[str]): channels list from a viewer
            index (int, optional): ROI index. Defaults to None.
        """
        if index is not None:   
            param = self.settings.child('ROIs', roi_format(index), 'use_channel')
            param.setValue(dict(all_items=channels,
                        selected=channels))
        else:
            for ind in range(len(self)): 
                param = self.settings.child('ROIs', roi_format(ind), 'use_channel')
                param.setValue(dict(all_items=channels,
                        selected=channels))   
                    
    def update_roi(self, roi: ROI, param: Parameter):
        par = self.get_parameter(roi)
        roi.signalBlocker.reblock()
        parent_name = param.parent().opts['name']

        if param.name() == roi.key():
            roi.doShow(param.value())
        elif param.name() == 'roi_type':
            state = roi.saveState()
            self.viewer_widget.plotItem.removeItem(roi)            
            if self.ROI_type =='2D':
                roi = self.make_ROI2D(roi_type=param.value(),index=roi.index,pos=state['pos'],size=state['size'],angle=state['angle'],pen=roi.pen)                
                self.add_ROI(roi)
        elif param.name() == 'Color':
            roi.setPen(param.value())
            self.emit_colors()
        elif parent_name == 'center':
            center = roi.center()
            pos = self.update_roi_pos(center, param)
            if self.ROI_type =='1D':
                roi.set_positions()
                pos.sort()
            else:
                roi.set_center(pos)
        elif parent_name == 'position':
            position = roi.pos()
            pos = self.update_roi_pos(position, param)
            if self.ROI_type =='1D':
                pos = np.sort(pos) #Subclass pg.Point to implement sort?
                roi.setPos(pos) 
                self.settings_signalBlocker.reblock()
                par.child(*('position', 'left')).setValue(pos[0])
                par.child(*('position', 'right')).setValue(pos[1])         
                self.settings_signalBlocker.unblock()
            roi.setPos(pos)          
        elif param.name() == 'angle':
            roi.setAngle(param.value(),center=[0.5,0.5])
        elif param.name() == 'zlevel':
            roi.setZValue(param.value())
        elif param.name() == 'width':
            size = roi.size()
            roi.setSize((param.value(), size[1]))
        elif param.name() == 'height':
            size = roi.size()
            roi.setSize((size[0], param.value()))
        elif param.name() == 'process_data':
            roi.compute = param.value()

        self.update_roi_tree(roi)
        roi.signalBlocker.unblock()

    def update_roi_pos(self, pos, param):
        if param.name() == 'x' or param.name() == 'left':
            poss = Point(param.value(), pos[1])
        elif param.name() == 'y' or param.name() == 'right':         
            poss = Point(pos[0], param.value())                   
        return poss
    
    def get_parameter(self, roi):
        if type(roi) is int:
            par =  self.settings.child(*('ROIs', roi_format(roi)))
        else:
            par = self.settings.child(*('ROIs', roi.key()))
        return par

    @Slot(type(ROI))
    def update_roi_tree(self, roi):
        par = self.get_parameter(roi)        

        if isinstance(roi, LinearROI):
            pos = roi.getRegion()
        else:
            pos = roi.pos()
            size = roi.size()
            angle = roi.angle()
            center = roi.center()
            Zvalue = roi.zValue()

        self.settings_signalBlocker.reblock()
        if isinstance(roi, LinearROI):
            par.child(*('position', 'left')).setValue(pos[0])
            par.child(*('position', 'right')).setValue(pos[1])
        if not isinstance(roi, LinearROI):
            par.child(*('position', 'x')).setValue(pos.x())
            par.child(*('position', 'y')).setValue(pos.y())
            par.child(*('center', 'x')).setValue(center.x())
            par.child(*('center', 'y')).setValue(center.y())        
            par.child(*('size', 'width')).setValue(size.x())
            par.child(*('size', 'height')).setValue(size.y())
            par.child('angle').setValue(angle)
            par.child('zlevel').setValue(Zvalue)
        self.settings_signalBlocker.unblock()

    def save_ROI(self):

        try:
            data = ioxml.parameter_to_xml_string(self.settings.child(('ROIs')))
            path = select_file(start_path=Path.home(), ext='xml', save=True, force_save_extension=True)

            if path != '':
                with open(path, 'wb') as f:
                    f.write(data)
        except Exception as e:
            print(e)

    def clear_ROI(self):
        keys = [roi.key() for roi in self._ROIs.values()]
        for roi_key in keys:
            self.settings.child(*('ROIs', roi_key)).remove()

    def load_ROI(self, path=None, params=None):
        try:
            if params is None:
                if path is None:
                    path = select_file(start_path=Path.home(), save=False, ext='xml', filter='XML files (*.xml)')
                    if path != '':
                        params = Parameter.create(title='Settings', name='settings', type='group',
                                                  children=ioxml.XML_file_to_parameter(path))

            if params is not None:
                self.clear_ROI()
                QtWidgets.QApplication.processEvents()

                for param in params:
                    if 'roi_type' in putils.iter_children(param, []):
                        self.settings.child('ROIs').addNew(param.child('roi_type').value())
                    else:
                        self.settings.child('ROIs').addNew()
                QtWidgets.QApplication.processEvents()
                self.set_roi(self.settings.child('ROIs').children(), params)
        except Exception as e:
            logger.exception(str(e))

    def set_roi(self, roi_params, roi_params_new):
        for child, new_child in zip(roi_params, roi_params_new):
            if new_child.value():
                child.setValue(new_child.value())
            self.set_roi(child.children(), new_child.children())


class ROISaver:
    def __init__(self, msgbox=False, det_modules=[]):

        self.roi_presets = None
        self.detector_modules = det_modules

        if msgbox:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("ROI Manager?")
            msgBox.setInformativeText("What do you want to do?")
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
            modify_button = msgBox.addButton('Modify', QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == modify_button:
                path = select_file(start_path=roi_path, save=False, ext='xml')
                if path != '':
                    self.set_file_roi(str(path))
            else:  # cancel
                pass

    def set_file_roi(self, filename, show=True):
        """

        """

        children = ioxml.XML_file_to_parameter(filename)
        self.roi_presets = Parameter.create(title='roi', name='rois', type='group', children=children)

        det_children = [child for child in self.roi_presets.children() if 'det' in child.opts['name']]
        det_names = [child.child('detname').value() for child in self.roi_presets.children() if
                     'det' in child.opts['name']]
        det_module_names = [det.title for det in self.detector_modules]
        for ind_det, det_roi in enumerate(det_children):
            det_module = self.detector_modules[det_module_names.index(det_names[ind_det])]
            viewer_children = [child for child in det_roi.children() if 'viewer' in child.opts['name']]
            for ind_viewer, viewer in enumerate(det_module.viewers):
                rois_params = [child for child in viewer_children[ind_viewer].children() if 'ROI' in child.opts['name']]
                if len(rois_params) > 0:
                    if hasattr(viewer, 'roi_manager'):
                        if hasattr(viewer, 'activate_roi'):  # because for viewer 0D it is irrelevant
                            viewer.activate_roi()
                        viewer.roi_manager.load_ROI(params=rois_params)
                        QtWidgets.QApplication.processEvents()

        if show:
            self.show_rois()

    def set_new_roi(self, file=None):
        if file is None:
            file = 'roi_default'

        self.roi_presets = Parameter.create(name='roi_settings', type='group', children=[
            {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': file}, ])

        for ind_det, det in enumerate(self.detector_modules):
            det_param = Parameter.create(name=f'det_{ind_det:03d}', type='group', children=[
                {'title': 'Det Name:', 'name': 'detname', 'type': 'str', 'value': det.title}, ])

            for ind_viewer, viewer in enumerate(det.ui.viewers):
                viewer_param = Parameter.create(
                    name=f'viewer_{ind_viewer:03d}', type='group',
                    children=[
                        {'title': 'Viewer:', 'name': 'viewername', 'type': 'str',
                         'value': det.ui.viewer_docks[ind_viewer].name()}, ])

                if hasattr(viewer, 'roi_manager'):
                    viewer_param.addChild(
                        {'title': 'ROI type:', 'name': 'roi_type', 'type': 'str',
                         'value': viewer.roi_manager.settings.child('ROIs').roi_type})
                    viewer_param.addChildren(viewer.roi_manager.settings.child('ROIs').children())
                det_param.addChild(viewer_param)
            self.roi_presets.addChild(det_param)

        ioxml.parameter_to_xml_file(self.roi_presets, os.path.join(roi_path, file))
        self.show_rois()

    def show_rois(self):
        """

        """
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        tree.setParameters(self.roi_presets, showTop=False)

        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)

        buttonBox.addButton('Save', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about this manager')
        res = dialog.exec()

        if res == QtWidgets.QDialog.DialogCode.Accepted:
            # save managers parameters in a xml file
            # start = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
            # start = os.path.join("..",'daq_scan')
            ioxml.parameter_to_xml_file(
                self.roi_presets, os.path.join(
                    roi_path, self.roi_presets.child('filename').value()))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    from pymodaq_gui.plotting.widgets import ImageWidget
    from pyqtgraph import PlotWidget

    im = ImageWidget()
    im = PlotWidget()
    prog = ROIManager(im, DataDim.Data2D)
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout()
    widget.setLayout(layout)
    layout.addWidget(im)
    layout.addWidget(prog.roiwidget)
    widget.show()
    prog.add_roi_programmatically(ROI2D_TYPES[0])
    prog.add_roi_programmatically(ROI2D_TYPES[1])
    prog.add_roi_programmatically(ROI2D_TYPES[2])
    sys.exit(app.exec_())