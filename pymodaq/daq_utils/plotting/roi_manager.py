import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QRectF, QRect, QPointF, QLocale
from collections import OrderedDict
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph import ROI as pgROI
from pyqtgraph import LinearRegionItem as pgLinearROI
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.daq_utils.daq_utils import select_file
import numpy as np
import copy

class LinearROI(pgLinearROI):
    index_signal = pyqtSignal(int)

    def __init__(self, index=0, pos=[0,10], **kwargs):
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
    \**args        All extra keyword arguments are passed to ROI()
    ============== =============================================================

    """
    index_signal = pyqtSignal(int)

    def __init__(self, index=0, pos=[0,0], size=[10,10], **kwargs):
        # QtGui.QGraphicsRectItem.__init__(self, 0, 0, size[0], size[1])
        super().__init__( pos=pos, size=size, **kwargs)
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
        ## generate an ellipsoidal mask
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

        p.scale(r.width(), r.height())  ## workaround for GL bug
        r = QtCore.QRectF(r.x() / r.width(), r.y() / r.height(), 1, 1)

        p.drawEllipse(r)

    def shape(self):
        self.path = QtGui.QPainterPath()
        self.path.addEllipse(self.boundingRect())
        return self.path

    def width(self):
        return self.size().x()


class RectROI(pgROI):
    index_signal = pyqtSignal(int)

    def __init__(self, index=0, pos=[0,0], size = [10,10]):
        super().__init__(pos=pos, size=size)  # , scaleSnap=True, translateSnap=True)
        self.addScaleHandle([1, 1], [0, 0])
        self.addRotateHandle([0, 0], [0.5, 0.5])
        self.index = index
        self.sigRegionChangeFinished.connect(self.emit_index_signal)

    def center(self):
        return QPointF(self.pos().x() + self.size().x() / 2, self.pos().y() + self.size().y() / 2)

    def emit_index_signal(self):
        self.index_signal.emit(self.index)


class ROIManager(QObject):
    ROI_changed = pyqtSignal()
    ROI_changed_finished = pyqtSignal()
    new_ROI_signal = pyqtSignal(int, str)
    remove_ROI_signal = pyqtSignal(str)
    roi_settings_changed = pyqtSignal(list)


    color_list = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (14, 207, 189), (207, 14, 166), (207, 204, 14)]

    def __init__(self, viewer_widget=None, ROI_type='1D'):
        super().__init__()
        self.ROI_type = ROI_type
        self.roiwidget = QtWidgets.QWidget()
        self.viewer_widget = viewer_widget #either a PlotWidget or a ImageWidget
        self.ROIs = OrderedDict([])
        self.setupUI()

    def setupUI(self):

        vlayout =QtWidgets.QVBoxLayout()
        self.roiwidget.setLayout(vlayout)

        horwidget = QtWidgets.QWidget()
        horlayout =QtWidgets.QHBoxLayout()
        horwidget.setLayout(horlayout)
        self.save_ROI_pb =QtWidgets.QPushButton('Save ROIs')
        self.load_ROI_pb =QtWidgets.QPushButton('Load ROIs')
        horlayout.addWidget(self.save_ROI_pb)
        horlayout.addWidget(self.load_ROI_pb)

        vlayout.addWidget(horwidget)

        self.roitree= ParameterTree()
        vlayout.addWidget(self.roitree)
        self.roiwidget.setMinimumWidth(300)
        self.roiwidget.setMaximumWidth(300)

        params = [{'title': 'Measurements:', 'name': 'measurements', 'type': 'table', 'value': OrderedDict([]), 'Ncol': 2, 'header': ["LO", "Value"]},
                ROIScalableGroup(roi_type=self.ROI_type, name="ROIs")]
        self.settings=Parameter.create(title='ROIs Settings', name='rois_settings', type='group', children=params)
        self.roitree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.roi_tree_changed)

        self.save_ROI_pb.clicked.connect(self.save_ROI)
        self.load_ROI_pb.clicked.connect(lambda: self.load_ROI(None))

    def roi_tree_changed(self,param,changes):

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':#new roi to create
                par=data[0]
                newindex = int(par.name()[-2:])

                if par.child(('type')).value() == '1D':
                    roi_type = ''
                    newroi = LinearROI(index=newindex, pos = [par.child('position', 'left').value(),
                                                      par.child('position', 'right').value()])
                    newroi.setZValue(-10)
                    newroi.setBrush(par.child(('Color')).value())
                    newroi.setOpacity(0.2)

                elif par.child(('type')).value() == '2D':
                    roi_type=par.child(('roi_type')).value()
                    if roi_type == 'RectROI':
                        newroi=RectROI(index=newindex, pos = [par.child('position', 'x').value(),
                                                      par.child('position', 'y').value()],
                                       size =[par.child('size', 'width').value(),
                                                      par.child('size', 'height').value()])
                    else:
                        newroi=EllipseROI(index=newindex, pos = [par.child('position', 'x').value(),
                                                      par.child('position', 'y').value()],
                                          size =[par.child('size', 'width').value(),
                                                      par.child('size', 'height').value()])
                    newroi.setPen(par.child(('Color')).value())

                newroi.sigRegionChanged.connect(self.ROI_changed.emit)
                newroi.sigRegionChangeFinished.connect(self.ROI_changed_finished.emit)
                newroi.index_signal[int].connect(self.update_roi_tree)
                try:
                    self.settings.sigTreeStateChanged.disconnect()
                except:
                    pass
                self.settings.sigTreeStateChanged.connect(self.roi_tree_changed)
                self.viewer_widget.plotItem.addItem(newroi)


                self.ROIs["ROI_%02.0d" % newindex] = newroi

                self.new_ROI_signal.emit(newindex, roi_type)

                # self.ui.RoiCurve_H["ROI_%02.0d" % newindex]=self.ui.Lineout_H.plot(pen=QtGui.QColor(*self.color_list[newindex]))
                # self.ui.RoiCurve_V["ROI_%02.0d" % newindex]=self.ui.Lineout_V.plot(pen=QtGui.QColor(*self.color_list[newindex]))
                # self.ui.RoiCurve_integrated["ROI_%02.0d" % newindex]=self.ui.Lineout_integrated.plot(pen=QtGui.QColor(*self.color_list[newindex]))
                # self.data_integrated_plot["ROI_%02.0d" % newindex]=np.zeros((2,1))
                # #self.data_to_export["%02.0d" % newindex]=None
                # self.roiChanged()

            elif change == 'value':
                if param.name() in custom_tree.iter_children(self.settings.child(('ROIs')),[]):
                    if param.name() == 'Color' or param.name() == 'angle' :
                        parent=param.parent().name()
                    else:
                        parent=param.parent().parent().name()
                    self.update_roi(parent,param)


            elif change == 'parent':
                if 'ROI' in param.name():
                    roi = self.ROIs.pop(param.name())
                    self.viewer_widget.plotItem.removeItem(roi)
                    self.remove_ROI_signal.emit(param.name())

            if param.name() != 'measurements':
                self.roi_settings_changed.emit([(param, 'value', param.value())])
        self.ROI_changed_finished.emit()

    def update_roi(self, roi_key, param):

        if param.name() == 'Color':
            self.ROIs[roi_key].setPen(param.value())
        elif param.name() == 'left' or param.name() == 'x':
            pos = self.ROIs[roi_key].pos()
            poss = [param.value(), pos[1]]
            poss.sort()
            self.ROIs[roi_key].setPos(poss)

        elif param.name() == 'right' or param.name() == 'y':
            pos = self.ROIs[roi_key].pos()
            poss = [pos[0], param.value()]
            poss.sort()
            self.ROIs[roi_key].setPos(poss)


        elif param.name() == 'angle':
            self.ROIs[roi_key].setAngle(param.value())
        elif param.name() == 'width':
            size = self.ROIs[roi_key].size()
            self.ROIs[roi_key].setSize((param.value(), size[1]))
        elif param.name() == 'height':
            size = self.ROIs[roi_key].size()
            self.ROIs[roi_key].setSize((size[0], param.value()))


    @pyqtSlot(int)
    def update_roi_tree(self,index):
        roi=self.ROIs['ROI_%02.0d'%index]
        par = self.settings.child(*('ROIs', 'ROI_%02.0d' % index))
        if isinstance(roi, LinearROI):
            pos = roi.getRegion()
        else:
            pos=roi.pos()
            size=roi.size()
            angle=roi.angle()

        try:
            self.settings.sigTreeStateChanged.disconnect()
        except:
            pass
        if isinstance(roi, LinearROI):
            par.child(*('position','left')).setValue(pos[0])
            par.child(*('position','right')).setValue(pos[1])
        if not isinstance(roi, LinearROI):
            par.child(*('position','x')).setValue(pos[0])
            par.child(*('position','y')).setValue(pos[1])
            par.child(*('size','width')).setValue(size[0])
            par.child(*('size','height')).setValue(size[1])
            par.child(('angle')).setValue(angle)

        self.settings.sigTreeStateChanged.connect(self.roi_tree_changed)


    def save_ROI(self):

        try:
            data=custom_tree.parameter_to_xml_string(self.settings.child(('ROIs')))
            path=select_file(ext='roi')

            if path != '':
                with open(path, 'wb') as f:
                    f.write(data)
        except Exception as e:
            print(e)

    def load_ROI(self, path = None):
        try:
            if path is None:
                path = select_file(save=False, ext='roi')
                if path != '':
                    for roi in self.ROIs.values():
                        index=roi.index
                        self.viewer_widget.plotitem.removeItem(roi)
                        #self.settings.sigTreeStateChanged.disconnect()
                        self.settings.child(*('ROIs', 'ROI_%02.0d' % index)).remove()
                        #self.settings.sigTreeStateChanged.connect(self.roi_tree_changed)
                    self.ROIs = OrderedDict([])


                    params = custom_tree.XML_file_to_parameter(path)
                    self.settings.child(('ROIs')).addChildren(params)

        except Exception as e:
            pass

class ROIScalableGroup(pTypes.GroupParameter):
    def __init__(self, roi_type = '1D', **opts):
        opts['type'] = 'group'
        opts['addText'] = "Add"
        self.roi_type = roi_type
        if roi_type is not '1D':
            opts['addList'] = ['RectROI', 'EllipseROI']
        self.color_list = ROIManager.color_list
        pTypes.GroupParameter.__init__(self, **opts)

    def addNew(self, typ=''):
        indexes = [int(par.name()[-2:]) for par in self.children()]
        if indexes == []:
            newindex = 0
        else:
            newindex = max(indexes) + 1
        child = {'name': 'ROI_{:02d}'.format(newindex), 'type': 'group', 'removable': True, 'renamable': False}

        children = [{'name': 'type', 'type': 'str', 'value': self.roi_type, 'readonly': True, 'visible': False},]
        if self.roi_type == '2D':
            children.extend([{'title': 'ROI Type', 'name': 'roi_type', 'type': 'str', 'value': typ, 'readonly': True},
                            {'title': 'Use channel', 'name': 'use_channel', 'type': 'list', 'values': ['red', 'green', 'blue']},])
        else:
            children.append({'title': 'Use channel', 'name': 'use_channel', 'type': 'list'})

        functions = ['Sum', 'Mean', 'half-life', 'expotime']
        children.append({'title': 'Math type:', 'name': 'math_function', 'type': 'list', 'values': functions,
                 'value': 'Sum', 'visible': self.roi_type == '1D'})
        children.extend([
            {'name': 'Color', 'type': 'color', 'value': self.color_list[newindex]},])
        if self.roi_type == '2D':
            children.extend([{'name': 'position', 'type': 'group', 'children': [
                {'name': 'x', 'type': 'float', 'value': 0, 'step': 1},
                {'name': 'y', 'type': 'float', 'value': 0, 'step': 1}
            ]},])
        else:
            children.extend([{'name': 'position', 'type': 'group', 'children': [
                {'name': 'left', 'type': 'float', 'value': 0, 'step': 1},
                {'name': 'right', 'type': 'float', 'value': 10, 'step': 1}
            ]},])
        if self.roi_type == '2D':
            children.extend([
                {'name': 'size', 'type': 'group', 'children': [
                    {'name': 'width', 'type': 'float', 'value': 10, 'step': 1},
                    {'name': 'height', 'type': 'float', 'value': 10, 'step': 1}
                ]},
                {'name': 'angle', 'type': 'float', 'value': 0, 'step': 1}])

        child['children'] = children

        self.addChild(child)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    from pymodaq.daq_utils.plotting.viewer2D.viewer2d_basic import ImageWidget
    from pyqtgraph import PlotWidget
    im = ImageWidget()
    im = PlotWidget()
    prog = ROIManager(im, '1D')
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout()
    widget.setLayout(layout)
    layout.addWidget(im)
    layout.addWidget(prog.roiwidget)
    widget.show()
    sys.exit(app.exec_())