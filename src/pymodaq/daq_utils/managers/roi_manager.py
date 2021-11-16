import os
import sys

import pymodaq.daq_utils
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QObject, Slot, Signal, QPointF
from qtpy.QtGui import QIcon, QPixmap
from collections import OrderedDict

from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils.parameter import utils as putils
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree.parameterTypes.basetypes import GroupParameter
from pymodaq.daq_utils.parameter import pymodaq_ptypes
from pymodaq.daq_utils.managers.action_manager import QAction
from pyqtgraph import ROI as pgROI
from pyqtgraph import functions as fn
from pyqtgraph import LinearRegionItem as pgLinearROI
from pymodaq.daq_utils.daq_utils import plot_colors
from pymodaq.daq_utils.config import get_set_roi_path
from pymodaq.daq_utils.gui_utils import select_file
import numpy as np
from pathlib import Path


roi_path = get_set_roi_path()


class ROIBrushable(pgROI):
    def __init__(self, brush=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if brush is None:
            brush = QtGui.QBrush(QtGui.QColor(0, 0, 255, 50))
        self.setBrush(brush)

    def setBrush(self, *br, **kargs):
        """Set the brush that fills the region. Can have any arguments that are valid
        for :func:`mkBrush <pyqtgraph.mkBrush>`.
        """
        self.brush = fn.mkBrush(*br, **kargs)
        self.currentBrush = self.brush

    def paint(self, p, opt, widget):
        # p.save()
        # Note: don't use self.boundingRect here, because subclasses may need to redefine it.
        r = QtCore.QRectF(0, 0, self.state['size'][0], self.state['size'][1]).normalized()

        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)
        p.setBrush(self.currentBrush)
        p.translate(r.left(), r.top())
        p.scale(r.width(), r.height())
        p.drawRect(0, 0, 1, 1)
        # p.restore()


class LinearROI(pgLinearROI):
    index_signal = Signal(int)

    def __init__(self, index=0, pos=[0, 10], **kwargs):
        super().__init__(values=pos, **kwargs)
        self.index = index
        self.sigRegionChangeFinished.connect(self.emit_index_signal)

    def pos(self):
        return self.getRegion()

    def setPos(self, pos):
        self.setRegion(pos)

    def setPen(self, color):
        self.setBrush(color)

    def emit_index_signal(self):
        self.index_signal.emit(self.index)


class EllipseROI(pgROI):
    """
    Elliptical ROI subclass with one scale handle and one rotation handle.


    ============== =============================================================
    **Arguments**
    pos            (length-2 sequence) The position of the ROI's origin.
    size           (length-2 sequence) The size of the ROI's bounding rectangle.
    **args         All extra keyword arguments are passed to ROI()
    ============== =============================================================

    """
    index_signal = Signal(int)

    def __init__(self, index=0, pos=[0, 0], size=[10, 10], **kwargs):
        # QtGui.QGraphicsRectItem.__init__(self, 0, 0, size[0], size[1])
        super().__init__(pos=pos, size=size, **kwargs)
        self.addRotateHandle([1.0, 0.5], [0.5, 0.5])
        self.addScaleHandle([0.5 * 2. ** -0.5 + 0.5, 0.5 * 2. ** -0.5 + 0.5], [0.5, 0.5])
        self.index = index
        self.sigRegionChangeFinished.connect(self.emit_index_signal)

    def center(self):
        return QPointF(self.pos().x() + self.size().x() / 2, self.pos().y() + self.size().y() / 2)

    def emit_index_signal(self):
        self.index_signal.emit(self.index)

    def getArrayRegion(self, arr, img=None, axes=(0, 1), **kwds):
        """
        Return the result of ROI.getArrayRegion() masked by the elliptical shape
        of the ROI. Regions outside the ellipse are set to 0.
        """
        # Note: we could use the same method as used by PolyLineROI, but this
        # implementation produces a nicer mask.
        if kwds["returnMappedCoords"]:
            arr, coords = pgROI.getArrayRegion(self, arr, img, axes, **kwds)
        else:
            arr = pgROI.getArrayRegion(self, arr, img, axes, **kwds)
        if arr is None or arr.shape[axes[0]] == 0 or arr.shape[axes[1]] == 0:
            return arr
        w = arr.shape[axes[0]]
        h = arr.shape[axes[1]]
        # generate an ellipsoidal mask
        mask = np.fromfunction(
            lambda x, y: (((x + 0.5) / (w / 2.) - 1) ** 2 + ((y + 0.5) / (h / 2.) - 1) ** 2) ** 0.5 < 1, (w, h))

        # reshape to match array axes
        if axes[0] > axes[1]:
            mask = mask.T
        shape = [(n if i in axes else 1) for i, n in enumerate(arr.shape)]
        mask = mask.reshape(shape)
        if kwds["returnMappedCoords"]:
            return arr * mask, coords
        else:
            return arr * mask

    def height(self):
        return self.size().y()

    def paint(self, p, opt, widget):
        r = self.boundingRect()
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)

        p.scale(r.width(), r.height())  # workaround for GL bug
        r = QtCore.QRectF(r.x() / r.width(), r.y() / r.height(), 1, 1)

        p.drawEllipse(r)

    def shape(self):
        self.path = QtGui.QPainterPath()
        self.path.addEllipse(self.boundingRect())
        return self.path

    def width(self):
        return self.size().x()


class RectROI(pgROI):
    index_signal = Signal(int)

    def __init__(self, index=0, pos=[0, 0], size=[10, 10]):
        super().__init__(pos=pos, size=size)  # , scaleSnap=True, translateSnap=True)
        self.addScaleHandle([1, 1], [0, 0])
        self.addRotateHandle([0, 0], [0.5, 0.5])
        self.index = index
        self.sigRegionChangeFinished.connect(self.emit_index_signal)

    def center(self):
        return QPointF(self.pos().x() + self.size().x() / 2, self.pos().y() + self.size().y() / 2)

    def emit_index_signal(self):
        self.index_signal.emit(self.index)


ROI_NAME_PREFIX = 'ROI_'
ROI2D_TYPES = ['RectROI', 'EllipseROI']


class ROIScalableGroup(GroupParameter):
    def __init__(self, roi_type='1D', **opts):
        opts['type'] = 'group'
        opts['addText'] = "Add"
        self.roi_type = roi_type
        if roi_type != '1D':
            opts['addList'] = ROI2D_TYPES
        self.color_list = ROIManager.color_list
        super().__init__(**opts)

    def addNew(self, typ=''):
        name_prefix = ROI_NAME_PREFIX
        child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]
        if not child_indexes:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

        child = {'name': ROIManager.roi_format(newindex), 'type': 'group', 'removable': True, 'renamable': False}

        children = [{'name': 'type', 'type': 'str', 'value': self.roi_type, 'readonly': True, 'visible': False}, ]
        if self.roi_type == '2D':
            children.extend([{'title': 'ROI Type', 'name': 'roi_type', 'type': 'str', 'value': typ, 'readonly': True},
                             {'title': 'Use channel', 'name': 'use_channel', 'type': 'list',
                              'limits': ['red', 'green', 'blue', 'spread']}, ])
        else:
            children.append({'title': 'Use channel', 'name': 'use_channel', 'type': 'list'})

        functions = ['Sum', 'Mean', 'half-life', 'expotime']
        children.append({'title': 'Math type:', 'name': 'math_function', 'type': 'list', 'limits': functions,
                         'value': 'Sum', 'visible': self.roi_type == '1D'})
        children.extend([
            {'name': 'Color', 'type': 'color', 'value': list(np.roll(self.color_list, newindex)[0])}, ])
        if self.roi_type == '2D':
            children.extend([{'name': 'position', 'type': 'group', 'children': [
                {'name': 'x', 'type': 'float', 'value': 0, 'step': 1},
                {'name': 'y', 'type': 'float', 'value': 0, 'step': 1}
            ]}, ])
        else:
            children.extend([{'name': 'position', 'type': 'group', 'children': [
                {'name': 'left', 'type': 'float', 'value': 0, 'step': 1},
                {'name': 'right', 'type': 'float', 'value': 10, 'step': 1}
            ]}, ])
        if self.roi_type == '2D':
            children.extend([
                {'name': 'size', 'type': 'group', 'children': [
                    {'name': 'width', 'type': 'float', 'value': 10, 'step': 1},
                    {'name': 'height', 'type': 'float', 'value': 10, 'step': 1}
                ]},
                {'name': 'angle', 'type': 'float', 'value': 0, 'step': 1}])

        child['children'] = children

        self.addChild(child)


class ROIManager(QObject):
    ROI_changed = Signal()
    ROI_changed_finished = Signal()

    new_ROI_signal = Signal(int, str)
    remove_ROI_signal = Signal(str)
    roi_value_changed = Signal(str, tuple)

    roi_update_children = Signal(list)

    color_list = np.array(plot_colors)

    def __init__(self, viewer_widget=None, ROI_type='1D'):
        super().__init__()
        self.ROI_type = ROI_type
        self.roiwidget = QtWidgets.QWidget()
        self.viewer_widget = viewer_widget  # either a PlotWidget or a ImageWidget
        self._ROIs = OrderedDict([])
        self.setupUI()

    @staticmethod
    def roi_format(index):
        return f'{ROI_NAME_PREFIX}{index:02d}'

    @property
    def ROIs(self):
        return self._ROIs

    def get_roi_from_index(self, index: int):
        return self.ROIs[self.roi_format(index)]

    def _set_roi_from_index(self, index: int, roi):
        self.ROIs[self.roi_format(index)] = roi

    def get_roi(self, roi_key):
        if roi_key in self.ROIs:
            return self.ROIs[roi_key]
        else:
            raise KeyError(f'{roi_key} is not a valid ROI identifier for {self.ROIs}')

    def add_roi_programmatically(self, roitype=ROI2D_TYPES[0]):
        self.settings.child('ROIs').addNew(roitype)

    def remove_roi_programmatically(self, index: int):
        self.settings.child('ROIs').removeChild(self.settings.child('ROIs', self.roi_format(index)))

    def setupUI(self):

        vlayout = QtWidgets.QVBoxLayout()
        self.roiwidget.setLayout(vlayout)

        self.toolbar = QtWidgets.QToolBar()
        vlayout.addWidget(self.toolbar)

        self.save_ROI_pb = QAction(QIcon(QPixmap(":/icons/Icon_Library/save_ROI.png")), 'Save ROIs')
        self.load_ROI_pb = QAction(QIcon(QPixmap(":/icons/Icon_Library/load_ROI.png")), 'Load ROIs')
        self.clear_ROI_pb = QAction(QIcon(QPixmap(":/icons/Icon_Library/clear_ROI.png")), 'Clear ROIs')
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

        self.save_ROI_pb.triggered.connect(self.save_ROI)
        self.load_ROI_pb.triggered.connect(lambda: self.load_ROI(None))
        self.clear_ROI_pb.triggered.connect(self.clear_ROI)

    def roi_tree_changed(self, param, changes):

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':  # new roi to create
                par = data[0]
                newindex = int(par.name()[-2:])

                if par.child(('type')).value() == '1D':
                    roi_type = ''

                    pos = self.viewer_widget.plotItem.vb.viewRange()[0]
                    newroi = LinearROI(index=newindex, pos=pos)
                    newroi.setZValue(-10)
                    newroi.setBrush(par.child(('Color')).value())
                    newroi.setOpacity(0.2)

                elif par.child(('type')).value() == '2D':
                    roi_type = par.child(('roi_type')).value()
                    xrange = self.viewer_widget.plotItem.vb.viewRange()[0]
                    yrange = self.viewer_widget.plotItem.vb.viewRange()[1]
                    width = np.max(((xrange[1] - xrange[0]) / 10, 2))
                    height = np.max(((yrange[1] - yrange[0]) / 10, 2))
                    pos = [int(np.mean(xrange) - width / 2), int(np.mean(yrange) - width / 2)]

                    if roi_type == 'RectROI':
                        newroi = RectROI(index=newindex, pos=pos,
                                         size=[width, height])
                    else:
                        newroi = EllipseROI(index=newindex, pos=pos,
                                            size=[width, height])
                    newroi.setPen(par.child(('Color')).value())

                newroi.sigRegionChanged.connect(lambda: self.ROI_changed.emit())
                newroi.sigRegionChangeFinished.connect(lambda: self.ROI_changed_finished.emit())
                newroi.index_signal[int].connect(self.update_roi_tree)
                try:
                    self.settings.sigTreeStateChanged.disconnect()
                except Exception:
                    pass
                self.settings.sigTreeStateChanged.connect(self.roi_tree_changed)
                self.viewer_widget.plotItem.addItem(newroi)

                self._set_roi_from_index(newindex, newroi)

                self.new_ROI_signal.emit(newindex, roi_type)
                self.update_roi_tree(newindex)

            elif change == 'value':
                if param.name() in putils.iter_children(self.settings.child(('ROIs')), []):
                    parent_name = putils.get_param_path(param)[putils.get_param_path(param).index('ROIs')+1]
                    self.update_roi(parent_name, param)
                    self.roi_value_changed.emit(parent_name, (param, param.value()))

            elif change == 'parent':
                if 'ROI' in param.name():
                    roi = self._ROIs.pop(param.name())
                    self.viewer_widget.plotItem.removeItem(roi)
                    self.remove_ROI_signal.emit(param.name())

        self.ROI_changed_finished.emit()

    def update_roi(self, roi_key, param):
        self._ROIs[roi_key].index_signal[int].disconnect()
        if param.name() == 'Color':
            self._ROIs[roi_key].setPen(param.value())
        elif param.name() == 'left' or param.name() == 'x':
            pos = self._ROIs[roi_key].pos()
            poss = [param.value(), pos[1]]
            if self.settings.child('ROIs', roi_key, 'type').value() == '1D':
                poss.sort()
            self._ROIs[roi_key].setPos(poss)

        elif param.name() == 'right' or param.name() == 'y':
            pos = self._ROIs[roi_key].pos()
            poss = [pos[0], param.value()]
            if self.settings.child('ROIs', roi_key, 'type').value() == '1D':
                poss.sort()
            self._ROIs[roi_key].setPos(poss)

        elif param.name() == 'angle':
            self._ROIs[roi_key].setAngle(param.value())
        elif param.name() == 'width':
            size = self._ROIs[roi_key].size()
            self._ROIs[roi_key].setSize((param.value(), size[1]))
        elif param.name() == 'height':
            size = self._ROIs[roi_key].size()
            self._ROIs[roi_key].setSize((size[0], param.value()))
        self._ROIs[roi_key].index_signal[int].connect(self.update_roi_tree)

    @Slot(int)
    def update_roi_tree(self, index):
        roi = self.get_roi_from_index(index)
        par = self.settings.child(*('ROIs', self.roi_format(index)))
        if isinstance(roi, LinearROI):
            pos = roi.getRegion()
        else:
            pos = roi.pos()
            size = roi.size()
            angle = roi.angle()

        try:
            self.settings.sigTreeStateChanged.disconnect()
        except Exception:
            pass
        if isinstance(roi, LinearROI):
            par.child(*('position', 'left')).setValue(pos[0])
            par.child(*('position', 'right')).setValue(pos[1])
        if not isinstance(roi, LinearROI):
            par.child(*('position', 'x')).setValue(pos[0])
            par.child(*('position', 'y')).setValue(pos[1])
            par.child(*('size', 'width')).setValue(size[0])
            par.child(*('size', 'height')).setValue(size[1])
            par.child('angle').setValue(angle)

        self.settings.sigTreeStateChanged.connect(self.roi_tree_changed)

    def save_ROI(self):

        try:
            data = ioxml.parameter_to_xml_string(self.settings.child(('ROIs')))
            path = select_file(start_path=Path.home(), ext='xml')

            if path != '':
                with open(path, 'wb') as f:
                    f.write(data)
        except Exception as e:
            print(e)

    def clear_ROI(self):
        indexes = [roi.index for roi in self._ROIs.values()]
        for index in indexes:
            self.settings.child(*('ROIs', self.roi_format(index))).remove()
            # self.settings.sigTreeStateChanged.connect(self.roi_tree_changed)

    def load_ROI(self, path=None, params=None):
        try:
            if params is None:
                if path is None:
                    path = select_file(start_path=Path.home(), save=False, ext='xml')
                    if path != '':
                        params = Parameter.create(title='Settings', name='settings', type='group',
                                                  children=ioxml.XML_file_to_parameter(path))

            if params is not None:
                self.clear_ROI()
                QtWidgets.QApplication.processEvents()

                for param in params:
                    if 'roi_type' in putils.iter_children(param, []):
                        self.settings.child(('ROIs')).addNew(param.child(('roi_type')).value())
                    else:
                        self.settings.child(('ROIs')).addNew()
                # self.settings.child(('ROIs')).addChildren(params)
                QtWidgets.QApplication.processEvents()

                # settings = Parameter.create(title='Settings', name='settings', type='group')
                #
                # for param in params:
                #     settings.addChildren(custom_tree.XML_string_to_parameter(custom_tree.parameter_to_xml_string(param)))

                self.set_roi(self.settings.child(('ROIs')).children(), params)

        except Exception as e:
            pass

    def set_roi(self, roi_params, roi_params_new):
        for child, new_child in zip(roi_params, roi_params_new):
            if 'group' not in child.opts['type']:
                child.setValue(new_child.value())
            else:
                self.set_roi(child.children(), new_child.children())



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    from pymodaq.daq_utils.plotting.data_viewers.viewer2D_basic import ImageWidget
    from pyqtgraph import PlotWidget

    im = ImageWidget()
    im = PlotWidget()
    prog = ROIManager(im, '2D')
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout()
    widget.setLayout(layout)
    layout.addWidget(im)
    layout.addWidget(prog.roiwidget)
    widget.show()
    prog.add_roi_programmatically(ROI2D_TYPES[0])
    prog.add_roi_programmatically(ROI2D_TYPES[1])
    sys.exit(app.exec_())


class ROISaver:
    def __init__(self, msgbox=False, det_modules=[]):

        self.roi_presets = None
        self.detector_modules = det_modules

        if msgbox:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Overshoot Manager?")
            msgBox.setInformativeText("What do you want to do?")
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.Cancel)
            modify_button = msgBox.addButton('Modify', QtWidgets.QMessageBox.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
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

        children = pymodaq.daq_utils.parameter.ioxml.XML_file_to_parameter(filename)
        self.roi_presets = Parameter.create(title='roi', name='rois', type='group', children=children)

        det_children = [child for child in self.roi_presets.children() if 'det' in child.opts['name']]
        det_names = [child.child(('detname')).value() for child in self.roi_presets.children() if
                     'det' in child.opts['name']]
        det_module_names = [det.title for det in self.detector_modules]
        for ind_det, det_roi in enumerate(det_children):
            det_module = self.detector_modules[det_module_names.index(det_names[ind_det])]
            viewer_children = [child for child in det_roi.children() if 'viewer' in child.opts['name']]
            for ind_viewer, viewer in enumerate(det_module.ui.viewers):
                rois_params = [child for child in viewer_children[ind_viewer].children() if 'ROI' in child.opts['name']]
                if hasattr(viewer, 'roi_manager'):
                    # if hasattr(viewer.ui, 'roiBtn'):
                    #     viewer.ui.roiBtn.click()
                    # elif hasattr(viewer.ui, 'Do_math_pb'):
                    #     viewer.ui.Do_math_pb.click()

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
                viewer_param = Parameter.create(name=f'viewer_{ind_viewer:03d}', type='group', children=[
                    {'title': 'Viewer:', 'name': 'viewername', 'type': 'str',
                     'value': det.ui.viewer_docks[ind_viewer].name()}, ])

                if hasattr(viewer, 'roi_manager'):
                    viewer_param.addChild({'title': 'ROI type:', 'name': 'roi_type', 'type': 'str',
                                           'value': viewer.roi_manager.settings.child(('ROIs')).roi_type})
                    viewer_param.addChildren(viewer.roi_manager.settings.child(('ROIs')).children())
                det_param.addChild(viewer_param)
            self.roi_presets.addChild(det_param)

        pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_file(self.roi_presets, os.path.join(roi_path, file))
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

        if res == dialog.Accepted:
            # save managers parameters in a xml file
            # start = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
            # start = os.path.join("..",'daq_scan')
            pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_file(self.roi_presets, os.path.join(roi_path,
                                                                                                   self.roi_presets.child(
                                                                                                       (
                                                                                                           'filename')).value()))