import dataclasses
from collections import OrderedDict
import os
from pathlib import Path
import sys
from typing import List, Union, Dict

import numpy as np

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import QObject, Slot, Signal,QSignalBlocker
from qtpy.QtGui import QIcon, QPixmap

from pyqtgraph.parametertree.parameterTypes.basetypes import GroupParameter

from pymodaq_utils.utils import find_objects_in_list_from_attr_name_val
from pymodaq_utils.logger import get_module_name, set_logger
from pymodaq_utils.config import GlobalConfig as Config

from pymodaq_data.plotting.utils import PlotColors
from pymodaq_data.post_treatment.process_to_scalar import DataProcessorFactory

from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import ParameterTree, Parameter, ioxml
from pymodaq_gui.managers.action_manager import QAction
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.config import get_set_roi_path
from pymodaq_gui.utils.utils import first_available_integer
from pymodaq_gui.plotting.items.roi_sync import (roi_format, ROISync, RoiParameter,
                                                 ROIFactory, ROI, ROIDim)
from pymodaq_gui.utils.file_io import select_file

data_processors = DataProcessorFactory()

roi_path = get_set_roi_path()
logger = set_logger(get_module_name(__file__))
config = Config()
plot_colors = PlotColors()

ROI_NAME_PREFIX = 'ROI_'
ROI2D_TYPES = ROIFactory.get_descriptors_from_dimensionality(ROIDim.ROI2D)


class ROIScalableGroup(GroupParameter):
    def __init__(self, roi_dim=ROIDim.ROI1D, **opts):
        opts['type'] = 'scalable_roigroup_parameter'
        opts['addText'] = "Add"
        self.roi_dim = roi_dim
        if roi_dim == ROIDim.ROI2D:
            opts['addList'] = ROI2D_TYPES
        # self.color_list = ROIManager.color_list
        super().__init__(**opts)

    def addNew(self, descriptor=''):
        name_prefix = ROI_NAME_PREFIX
        child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]
        if not child_indexes:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

        self.addChild(RoiParameter(self.roi_dim, descriptor, newindex))

registerParameterType('scalable_roigroup_parameter', ROIScalableGroup)


class ROIParameterManager(ParameterManager):
    def __init__(self, roi_dim=ROIDim.ROI1D):
        super().__init__(settings_name='roi_parameters',
                         action_list=("save", "update", "load", "clear", "search"))
        self.roi_dim = roi_dim
        self.settings.addChild(ROIScalableGroup(self.roi_dim,
                                                name='rois',
                                                title='ROIs'))

    @property
    def rois_setting(self) -> ROIScalableGroup:
        return self._settings.child('rois')

    def clear_settings_slot(self):
        try:
            for child in self.rois_setting.children():
                child.remove()
        except KeyError:
            pass

    def set_settings(self, settings: Union[Parameter, List[Dict[str, str]], Path]):
        """ If empty create the standard structure otherwise empty the ROIs and readd them  one by one
        for the ROI to reflects the param changes"""
        if not hasattr(self, '_settings') or 'rois' not in [child.name() for child in self._settings.children()]:
            super().set_settings(settings)
        else:
            settings = self.create_parameter(settings)
            self.clear_settings_slot()
            for child in settings.child('rois').children():
                self.rois_setting.addChild(child.saveState())


class ROIMeta:

    def __init__(self, param: RoiParameter):
        self.index = param.index
        self.param = param
        self.sync = ROISync.sync_from_param(param)
        self.roi = param.roi_from_param(param.index)
        self.sync.sync_entries_with(self.roi, self.param)


class ROIViewerManager(ROIParameterManager, QtCore.QObject):

    new_ROI_signal = Signal(int)
    remove_ROI_signal = Signal(int)
    # roi_value_changed = Signal(str, tuple)
    color_signal = Signal(list)
    # roi_update_children = Signal(list)
    roi_changed = Signal()
    # color_list = np.array(plot_colors)

    params = []

    def __init__(self, view_box=None, roi_dim=ROIDim.ROI1D):
        QtCore.QObject.__init__(self)
        ROIParameterManager.__init__(self, roi_dim)

        self.view_box: ViewBox = view_box  # a viewbox to add ROI into!
        self._ROIs: list[ROIMeta] = []

    @property
    def roiwidget(self):
        """ For backcompatibility """
        return self.settings_tree

    def emit_colors(self):
        colors = [roi_meta.param['color'] for roi_meta in self._ROIs]
        for color in colors:
            color.setAlpha(255)
        self.color_signal.emit(colors)

    @property
    def ROIs(self) -> list[ROIMeta]:
        return self._ROIs
    
    def __len__(self):
        return len(self._ROIs)

    def get_roi_from_index(self, index: int) -> ROIMeta:
        return find_objects_in_list_from_attr_name_val(self._ROIs, 'index', index)[0]

    def add_roi_programmatically(self, descriptor: str = ROI2D_TYPES[0]):
        self.rois_setting.addNew(descriptor)

    def remove_roi_programmatically(self, index: int):
        self.rois_setting.removeChild(self.get_roi_from_index(index).param)

    def get_ROI_indexes(self):
        return [roi.index for roi in self.ROIs]

    def child_added(self, param: Parameter, data: tuple[RoiParameter, int]):
        if data[0].parent() is self.rois_setting:
            self.create_and_add(data[0])

    def create_and_add(self, param: RoiParameter):
        roi_meta = ROIMeta(param)
        self._ROIs.append(roi_meta)
        self.view_box.addItem(roi_meta.roi)
        roi_meta.roi.sigRegionChangeFinished.connect(lambda: self.roi_changed.emit())
        roi_meta.roi.sigRemoveRequested.connect(lambda: self.remove_ROI(roi_meta))
        roi_meta.roi.sigCopyRequested.connect(lambda: self.copy_ROI(roi_meta))
        self.new_ROI_signal.emit(param.index)
        self.roi_changed.emit()

    def value_changed(self, param: Parameter):
        if param.name() == 'color':
            self.emit_colors()

    def param_deleted(self, param: RoiParameter):
        roi_meta = find_objects_in_list_from_attr_name_val(
            self._ROIs, 'param', param)[0]
        self._ROIs.remove(roi_meta)
        self.view_box.removeItem(roi_meta.roi)
        self.remove_ROI_signal.emit(roi_meta.index)

    def menu_changed(self, param: RoiParameter, data: str):
        if data == 'Copy':
            roi_meta = self.get_roi_from_index(param.index)
            self.copy_ROI(roi_meta)
        elif data == 'Remove':
            roi_meta = self.get_roi_from_index(param.index)
            self.remove_ROI(roi_meta)

    def expand_roi_tree(self, roi):
        # Expand roi tree when roi gets double selected
        param = self.rois_setting.child(roi_format(roi.index))
        isExpanded = not param.opts['expanded']
        param.setOpts(expanded=isExpanded)

    def remove_ROI(self, roi_meta: ROIMeta):
        self.remove_roi_programmatically(roi_meta.index)

    def copy_ROI(self, roi_meta: ROIMeta):
        """Method to copy a ROI and add it to the parameter tree and to the viewer widget
        The method extracts the parameters of the copied ROI, create a new parameter, a new ROI and update it with the settings from the copied parameter
        Args:
            roi (ROI): the ROI to be copied
        """
        index = first_available_integer(self.get_ROI_indexes()) 

        #Copy parameter and edit name
        param_roi = roi_meta.param
        param_state = param_roi.saveState()  # Transforming parameter in dict
        param_state['name'] = roi_format(index)  # Changing name
        param_state['index'] = index
        param_state['title'] = roi_format(index)
        param = RoiParameter(param_roi.roi_dim, descriptor=param_roi.descriptor, index=index)
        param.restoreState(param_state)
        self.rois_setting.addChild(param)

    def update_use_channel(self, channels: List[str], index=None):
        """Function to update the selected channels. If no index is given, the channels are applied to all ROIs.

        Args:
            channels (List[str]): channels list from a viewer
            index (int, optional): ROI index. Defaults to None.
        """
        if index is not None:   
            param = self.rois_setting.child(roi_format(index), 'use_channel')
            param.setValue(dict(all_items=channels,
                                selected=channels))
        else:
            for ind in range(len(self)): 
                param = self.rois_setting.child(roi_format(ind), 'use_channel')
                param.setValue(dict(all_items=channels,
                        selected=channels))   

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
            {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': file}])

        for ind_det, det in enumerate(self.detector_modules):
            det_param = Parameter.create(name=f'det_{ind_det:03d}', type='group', children=[
                {'title': 'Det Name:', 'name': 'detname', 'type': 'str', 'value': det.title}])

            for ind_viewer, viewer in enumerate(det.ui.viewers):
                viewer_param = Parameter.create(
                    name=f'viewer_{ind_viewer:03d}', type='group',
                    children=[
                        {'title': 'Viewer:', 'name': 'viewername', 'type': 'str',
                         'value': det.ui.viewer_docks[ind_viewer].name()}])

                if hasattr(viewer, 'roi_manager'):
                    viewer_param.addChild(
                        {'title': 'ROI type:', 'name': 'roi_type', 'type': 'str',
                         'value': viewer.roi_manager.settings.child('ROIs').roi_dim})
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
    from pyqtgraph import PlotWidget, ViewBox

    im = ImageWidget()
    im = PlotWidget()
    prog = ROIViewerManager(im, ROIDim.ROI2D)
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout()
    widget.setLayout(layout)
    layout.addWidget(im)
    layout.addWidget(prog.settings_tree)
    widget.show()
    prog.add_roi_programmatically(ROI2D_TYPES[0])
    prog.add_roi_programmatically(ROI2D_TYPES[1])
    prog.add_roi_programmatically(ROI2D_TYPES[2])
    sys.exit(app.exec())