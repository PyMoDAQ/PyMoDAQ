from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QRectF, QRect, QPointF, QLocale
import sys
from collections import OrderedDict
import pyqtgraph as pg
from pyqtgraph.Point import Point
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
Gradients.update(OrderedDict([
            ('red', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (255, 0, 0, 255))], 'mode': 'rgb'}),
            ('green', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (0, 255, 0, 255))], 'mode': 'rgb'}),
            ('blue', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (0, 0, 255, 255))], 'mode': 'rgb'}),]))

#import pymodaq
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_gui import Ui_Form
from pymodaq.daq_utils.plotting.viewer2D.viewer2d_basic import ImageWidget, ImageItem, AxisItem_Scaled
from pymodaq.daq_utils.plotting.crosshair import Crosshair
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.custom_parameter_tree

import numpy as np
from easydict import EasyDict as edict
import pickle
import copy
import os
from pymodaq.daq_utils.daq_utils import DockArea

import  pymodaq.daq_utils.daq_utils as utils
import datetime


class EllipseROI(pg.ROI):
    """
    Elliptical ROI subclass with one scale handle and one rotation handle.
    
    
    ============== =============================================================
    **Arguments**
    pos            (length-2 sequence) The position of the ROI's origin.
    size           (length-2 sequence) The size of the ROI's bounding rectangle.
    \**args        All extra keyword arguments are passed to ROI()
    ============== =============================================================
    
    """
    index_signal=pyqtSignal(int)
    def __init__(self, index=0, **args):
        #QtGui.QGraphicsRectItem.__init__(self, 0, 0, size[0], size[1])
        pg.ROI.__init__(self, pos=[100,100], size=[100,100], **args)
        self.addRotateHandle([1.0, 0.5], [0.5, 0.5])
        self.addScaleHandle([0.5*2.**-0.5 + 0.5, 0.5*2.**-0.5 + 0.5], [0.5, 0.5])
        self.index=index
        self.sigRegionChangeFinished.connect(self.emit_index_signal)

    def center(self):
        return QPointF(self.pos().x()+self.size().x()/2,self.pos().y()+self.size().y()/2)

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
            arr,coords = pg.ROI.getArrayRegion(self, arr, img, axes, **kwds)
        else:
            arr = pg.ROI.getArrayRegion(self, arr, img, axes, **kwds)
        if arr is None or arr.shape[axes[0]] == 0 or arr.shape[axes[1]] == 0:
            return arr
        w = arr.shape[axes[0]]
        h = arr.shape[axes[1]]
        ## generate an ellipsoidal mask
        mask = np.fromfunction(lambda x,y: (((x+0.5)/(w/2.)-1)**2+ ((y+0.5)/(h/2.)-1)**2)**0.5 < 1, (w, h))

        # reshape to match array axes
        if axes[0] > axes[1]:
            mask = mask.T
        shape = [(n if i in axes else 1) for i,n in enumerate(arr.shape)]
        mask = mask.reshape(shape)
        if kwds["returnMappedCoords"]:
            return arr * mask,coords
        else:
            return arr * mask

    def height(self):
        return self.size().y()
        
    def paint(self, p, opt, widget):
        r = self.boundingRect()
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)

        p.scale(r.width(), r.height())## workaround for GL bug
        r = QtCore.QRectF(r.x()/r.width(), r.y()/r.height(), 1,1)

        p.drawEllipse(r)
    
    def shape(self):
        self.path = QtGui.QPainterPath()
        self.path.addEllipse(self.boundingRect())
        return self.path
    def width(self):
        return self.size().x()

class RectROI(pg.ROI):
    index_signal=pyqtSignal(int)
    def __init__(self, index=0):
        pg.ROI.__init__(self, pos=[100,100], size=[100,100]) #, scaleSnap=True, translateSnap=True)
        self.addScaleHandle([1, 1], [0, 0])
        self.addRotateHandle([0, 0], [0.5, 0.5])
        self.index=index
        self.sigRegionChangeFinished.connect(self.emit_index_signal)
    def center(self):
        return QPointF(self.pos().x()+self.size().x()/2,self.pos().y()+self.size().y()/2)
    def emit_index_signal(self):
        self.index_signal.emit(self.index)






class Viewer2D(QtWidgets.QWidget):
    data_to_export_signal=pyqtSignal(OrderedDict) #OrderedDict(name=self.DAQ_type,data0D=None,data1D=None,data2D=None)
    crosshair_dragged=pyqtSignal(float, float) #signal used to pass crosshair position to other modules in scaled axes units
    sig_double_clicked=pyqtSignal(float, float)
    ROI_select_signal=pyqtSignal(QRectF)
    ROI_changed=pyqtSignal()
    ROI_changed_finished=pyqtSignal()

    def __init__(self,parent=None,scaling_options=dict(scaled_xaxis=dict(label="",units=None,offset=0,scaling=1),scaled_yaxis=dict(label="",units=None,offset=0,scaling=1))):
        super(Viewer2D,self).__init__()
        #setting the gui
        self.ui=Ui_Form()
        self.ui.ROIs_widget=self.setup_Roi_widget()


        if parent is None:
            parent=QtWidgets.QWidget()

        self.ui.setupUi(parent)#it's a widget here
        self.ui.horizontalLayout.addWidget(self.ui.ROIs_widget)
        self.ui.ROIs_widget.setVisible(False)

        self.max_size_integrated = 200
        self.scaling_options = copy.deepcopy(scaling_options)
        self.viewer_type='Data2D' #☺by default
        self.title=""
        self.parent=parent
        self.image = None
        self.isdata=edict(blue=False,green=False,red=False)
        self.color_list=[(255,0,0),(0,255,0),(0,0,255),(14,207,189),(207,14,166),(207,204,14)]

        self.image_widget = ImageWidget()
        self.ui.plotitem = self.image_widget.plotitem # for backward compatibility
        self.ui.splitter_VLeft.replaceWidget(0, self.ui.graphicsView)


        self.autolevels=False
        self.ui.auto_levels_pb.clicked.connect(self.set_autolevels)

        self.scaled_yaxis=AxisItem_Scaled('right')
        self.scaled_xaxis=AxisItem_Scaled('top')

        self.image_widget.view.sig_double_clicked.connect(self.double_clicked)
        self.image_widget.plotitem.layout.addItem(self.scaled_xaxis, *(1,1))
        self.image_widget.plotitem.layout.addItem(self.scaled_yaxis, *(2,2))
        self.scaled_xaxis.linkToView(self.image_widget.view)
        self.scaled_yaxis.linkToView(self.image_widget.view)
        self.set_scaling_axes(self.scaling_options)
        self.image_widget.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        self.ui.img_red = ImageItem()
        self.ui.img_green = ImageItem()
        self.ui.img_blue = ImageItem()
        #self.ui.img_red.sig_double_clicked.connect(self.double_clicked)
        self.ui.img_red.setCompositionMode( QtGui.QPainter.CompositionMode_Plus  )
        self.ui.img_green.setCompositionMode( QtGui.QPainter.CompositionMode_Plus  )
        self.ui.img_blue.setCompositionMode( QtGui.QPainter.CompositionMode_Plus  )
        self.ui.img_red.setOpts(axisOrder='row-major')
        self.ui.img_green.setOpts(axisOrder='row-major')
        self.ui.img_blue.setOpts(axisOrder='row-major')


        #selection area checkbox
        self.ui.blue_cb.setVisible(True)
        self.ui.blue_cb.setChecked(True)
        self.ui.blue_cb.clicked.connect(self.update_selection_area_visibility)
        self.ui.green_cb.setVisible(True)
        self.ui.green_cb.setChecked(True)
        self.ui.green_cb.clicked.connect(self.update_selection_area_visibility)
        self.ui.red_cb.setVisible(True)
        self.ui.red_cb.clicked.connect(self.update_selection_area_visibility)
        self.ui.red_cb.setChecked(True)

        self.image_widget.plotitem.addItem(self.ui.img_red)
        self.image_widget.plotitem.addItem(self.ui.img_green)
        self.image_widget.plotitem.addItem(self.ui.img_blue)
        self.ui.graphicsView.setCentralItem(self.image_widget.plotitem)

        ##self.ui.graphicsView.setCentralItem(self.image_widget.plotitem)
        #axis=pg.AxisItem('right',linkView=self.image_widget.view)
        #self.ui.graphicsView.addItem(axis)

        self.ui.aspect_ratio_pb.clicked.connect(self.lock_aspect_ratio)
        self.ui.aspect_ratio_pb.setChecked(True)

        #histograms
        histo_layout = QtWidgets.QHBoxLayout()
        self.ui.widget_histo.setLayout(histo_layout)
        self.ui.histogram_red=pg.HistogramLUTWidget()
        self.ui.histogram_red.setImageItem(self.ui.img_red)
        self.ui.histogram_green=pg.HistogramLUTWidget()
        self.ui.histogram_green.setImageItem(self.ui.img_green)
        self.ui.histogram_blue=pg.HistogramLUTWidget()
        self.ui.histogram_blue.setImageItem(self.ui.img_blue)
        histo_layout.addWidget(self.ui.histogram_red)
        histo_layout.addWidget(self.ui.histogram_green)
        histo_layout.addWidget(self.ui.histogram_blue)

        Ntick=3
        colors_red =[(int(r),0,0) for r in pg.np.linspace(0,255,Ntick)]
        colors_green=[(0,int(g),0) for g in pg.np.linspace(0,255,Ntick)]
        colors_blue=[(0,0,int(b)) for b in pg.np.linspace(0,255,Ntick)]
        cmap_red = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_red)
        cmap_green = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_green)
        cmap_blue = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_blue)
        self.ui.histogram_red.gradient.setColorMap(cmap_red)
        self.ui.histogram_green.gradient.setColorMap(cmap_green)
        self.ui.histogram_blue.gradient.setColorMap(cmap_blue)
        self.ui.histogram_red.setVisible(False)
        self.ui.histogram_green.setVisible(False)
        self.ui.histogram_blue.setVisible(False)
        self.ui.Show_histogram.clicked.connect(self.show_hide_histogram)


        #ROI selects an area and export its bounds as a signal
        self.ui.ROIselect=pg.RectROI([0,0],[10,10],centered=True,sideScalers=True)
        self.image_widget.plotitem.addItem(self.ui.ROIselect)
        self.ui.ROIselect.setVisible(False)
        self.ui.ROIselect.sigRegionChangeFinished.connect(self.selected_region_changed)
        self.ui.ROIselect_pb.clicked.connect(self.show_ROI_select)


        ## Isocurve drawing
        self.ui.iso = pg.IsocurveItem(level=0.8, pen='g',axisOrder='row-major')
        self.ui.iso.setParentItem(self.ui.img_red)
        self.ui.iso.setZValue(5)
        ## Draggable line for setting isocurve level
        self.ui.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        self.ui.histogram_red.vb.addItem(self.ui.isoLine)
        self.ui.histogram_red.vb.setMouseEnabled(y=False) # makes user interaction a little easier
        self.ui.isoLine.setValue(0.8)
        self.ui.isoLine.setZValue(1000) # bring iso line above contrast controls
        self.ui.isocurve_pb.clicked.connect(self.show_hide_iso)
        self.ui.isocurve_pb.setChecked(False)
        self.show_hide_iso()
        # build isocurves from smoothed data
        self.ui.isoLine.sigDragged.connect(self.updateIsocurve)

        ##crosshair
        self.ui.crosshair=Crosshair(self.image_widget.plotitem)
        self.ui.crosshair_H_blue = self.ui.Lineout_H.plot(pen="b")
        self.ui.crosshair_H_green = self.ui.Lineout_H.plot(pen="g")
        self.ui.crosshair_H_red = self.ui.Lineout_H.plot(pen="r")
        self.ui.crosshair_V_blue = self.ui.Lineout_V.plot(pen="b")
        self.ui.crosshair_V_green = self.ui.Lineout_V.plot(pen="g")
        self.ui.crosshair_V_red = self.ui.Lineout_V.plot(pen="r")


        self.ui.crosshair.crosshair_dragged.connect(self.update_crosshair_data)
        self.ui.crosshair_pb.clicked.connect(self.crosshairClicked)
        self.crosshairClicked()

        #flipping
        self.ui.FlipUD_pb.clicked.connect(self.update_image_flip)
        self.ui.FlipLR_pb.clicked.connect(self.update_image_flip)
        self.ui.rotate_pb.clicked.connect(self.update_image_flip)

        ## ROI stuff
        self.ui.RoiCurve_H=edict()
        self.ui.RoiCurve_V=edict()
        self.ui.RoiCurve_integrated=edict()
        self.data_integrated_plot= edict()
        self.ui.ROIs=OrderedDict([])
        self.ui.roiBtn.clicked.connect(self.roiClicked)

        self.data_to_export=OrderedDict(data0D=OrderedDict(),data1D=OrderedDict(),data2D=OrderedDict())

        self._x_axis=None
        self._y_axis=None
        self.x_axis_scaled=None
        self.y_axis_scaled=None

        self.ui.Ini_plot_pb.clicked.connect(self.ini_plot)


        params = [ROIScalableGroup(name="ROIs")]
        self.roi_settings=Parameter.create(title='ROIs Settings', name='roissettings', type='group', children=params)
        self.ui.ROI_Tree.setParameters(self.roi_settings, showTop=False)
        self.roi_settings.sigTreeStateChanged.connect(self.roi_tree_changed)

        self.ui.save_ROI_pb.clicked.connect(self.save_ROI)
        self.ui.load_ROI_pb.clicked.connect(self.load_ROI)

        #self.roiClicked() ## initialize roi plot to correct shape / visibility
        ##splitter
        try:
            self.ui.splitter_VLeft.splitterMoved[int,int].connect(self.move_right_splitter)
            self.ui.splitter_VRight.splitterMoved[int,int].connect(self.move_left_splitter)
        except:
            pass


    def add_ROI(self,roi_type='RectROI'):
        """
        Add a new ROI selector on the plot

        =======================      =========================================================
        **Arguments:**
        roi_type (str)               The type of ROI to instantiate: either 'RectROI' (default) or 'EllipseROI'
        """

        self.roi_settings.child(("ROIs")).addNew(roi_type)


    def crosshairChanged(self,indx=None,indy=None):
        if self.image is None or self._x_axis is None or self._y_axis is None:
            return

        image = self.image
        if indx is None or indy is None:
            (posx,posy)=self.ui.crosshair.get_positions()
            indx=utils.find_index(self._x_axis,posx)[0][0]
            indy=utils.find_index(self._y_axis,posy)[0][0]
        try:

            if self.isdata["blue"]:
                self.ui.crosshair_H_blue.setData(y=image["blue"][indy,:], x=self.x_axis_scaled)
            if self.isdata["green"]:
                self.ui.crosshair_H_green.setData(y=image["green"][indy,:], x=self.x_axis_scaled)
            if self.isdata["red"]:
                self.ui.crosshair_H_red.setData(y=image["red"][indy,:], x=self.x_axis_scaled)

            if self.isdata["blue"]:
                self.ui.crosshair_V_blue.setData(y=self.y_axis_scaled, x=image["blue"][:,indx])
            if self.isdata["green"]:
                self.ui.crosshair_V_green.setData(y=self.y_axis_scaled, x=image["green"][:,indx])
            if self.isdata["red"]:
                self.ui.crosshair_V_red.setData(y=self.y_axis_scaled, x=image["red"][:,indx])

        except Exception as e:
            raise e

    def crosshairClicked(self):
        if self.ui.crosshair_pb.isChecked():
            self.ui.crosshair.setVisible(True)
            self.ui.x_label.setVisible(True)
            self.ui.y_label.setVisible(True)
            range=self.image_widget.view.viewRange()
            self.ui.crosshair.set_crosshair_position(np.mean(np.array(range[0])),np.mean(np.array(range[0])))

            if self.isdata["blue"]:
                self.ui.z_label_blue.setVisible(True)
                self.ui.crosshair_H_blue.setVisible(True)
                self.ui.crosshair_V_blue.setVisible(True)
            if self.isdata["green"]:
                self.ui.z_label_green.setVisible(True)
                self.ui.crosshair_H_green.setVisible(True)
                self.ui.crosshair_V_green.setVisible(True)
            if self.isdata["red"]:
                self.ui.z_label_red.setVisible(True)
                self.ui.crosshair_H_red.setVisible(True)
                self.ui.crosshair_V_red.setVisible(True)
            self.update_crosshair_data(*self.ui.crosshair.get_positions())
            ##self.crosshairChanged()
        else:
            self.ui.crosshair.setVisible(False)
            self.ui.x_label.setVisible(False)
            self.ui.y_label.setVisible(False)

            self.ui.z_label_blue.setVisible(False)
            self.ui.z_label_green.setVisible(False)
            self.ui.z_label_red.setVisible(False)
            self.ui.crosshair_H_blue.setVisible(False)
            self.ui.crosshair_H_green.setVisible(False)
            self.ui.crosshair_H_red.setVisible(False)
            self.ui.crosshair_V_blue.setVisible(False)
            self.ui.crosshair_V_green.setVisible(False)
            self.ui.crosshair_V_red.setVisible(False)
        QtWidgets.QApplication.processEvents()
        self.show_lineouts()
        #self.show_lineouts()

    @pyqtSlot(float,float)
    def double_clicked(self,posx,posy):
        self.ui.crosshair.set_crosshair_position(posx,posy)
        self.update_crosshair_data(posx,posy)
        self.sig_double_clicked.emit(posx,posy)

    def ini_plot(self):
        for k in self.data_integrated_plot.keys():
            self.data_integrated_plot[k]=np.zeros((2,1))

    def load_ROI(self, path = None):
        try:
            for roi in self.ui.ROIs.values():
                index=roi.index
                self.image_widget.plotitem.removeItem(roi)
                self.roi_settings.sigTreeStateChanged.disconnect()
                self.roi_settings.child(*('ROIs','ROI_%02.0d'%index)).remove()
                self.roi_settings.sigTreeStateChanged.connect(self.roi_tree_changed)
                self.ui.ROIs.pop('ROI_%02.0d'%index)

            if path is None:
                path=self.select_file(save=False)
            with open(path, 'rb') as f:
                data_tree = pickle.load(f)
                self.restore_state(data_tree)

        except Exception as e:
            pass

    def lock_aspect_ratio(self):
        if self.ui.aspect_ratio_pb.isChecked():
            self.image_widget.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        else:
            self.image_widget.plotitem.vb.setAspectLocked(lock=False)

    @pyqtSlot(int, int)
    def move_left_splitter(self,pos,index):
        self.ui.splitter_VLeft.blockSignals(True)
        self.ui.splitter_VLeft.moveSplitter(pos,index)
        self.ui.splitter_VLeft.blockSignals(False)

    @pyqtSlot(int, int)
    def move_right_splitter(self,pos,index):
        self.ui.splitter_VRight.blockSignals(True)
        self.ui.splitter_VRight.moveSplitter(pos,index)
        self.ui.splitter_VRight.blockSignals(False)

    def restore_state(self,data_tree):
        self.roi_settings.restoreState(data_tree)
        QtWidgets.QApplication.processEvents()

        for param in self.roi_settings.child(('ROIs')):
            index=param.name()
            self.ui.ROIs[index].sigRegionChangeFinished.disconnect()
            self.update_roi(index,'angle',param.child(('angle')).value())
            #self.update_roi(index,'Color',param.child(('Color')).value())
            self.update_roi(index,'x',param.child(*('position','x')).value())
            self.update_roi(index,'y',param.child(*('position','y')).value())
            self.update_roi(index,'dx',param.child(*('size','dx')).value())
            self.update_roi(index,'dy',param.child(*('size','dy')).value())
            self.ui.ROIs[index].sigRegionChangeFinished.connect(self.ui.ROIs[index].emit_index_signal)


    def roiChanged(self):
        #self.data_to_export=edict(data0D=OrderedDict(),data1D=OrderedDict(),data2D=OrderedDict())
        try:
            if self.image is None:
                return
            axes = (0, 1)
            image = self.image
            color=self.ui.choose_trace_ROI_cb.currentText()
            if color=="red":
                data_flag=self.ui.red_cb.isChecked()
                img_source=self.ui.img_red
            elif color=="green":
                data_flag=self.ui.green_cb.isChecked()
                img_source=self.ui.img_green
            elif color=="blue":
                data_flag=self.ui.blue_cb.isChecked()
                img_source=self.ui.img_blue
            else: data_flag=None

            if data_flag is None:
                return

            self.data_to_export['data0D']=OrderedDict([])
            self.data_to_export['data1D']=OrderedDict([])

            for k in self.ui.ROIs.keys():
                data, coords = self.ui.ROIs[k].getArrayRegion(image[color], img_source, axes, returnMappedCoords=True)

                if data is not None:
                    xvals=np.linspace(np.min(np.min(coords[1,:,:])),np.max(np.max(coords[1,:,:])),data.shape[1])
                    yvals=np.linspace(np.min(np.min(coords[0,:,:])),np.max(np.max(coords[0,:,:])),data.shape[0])
                    x_axis,y_axis=self.scale_axis(xvals,yvals)

                    self.data_integrated_plot[k]=np.append(self.data_integrated_plot[k],np.array([[self.data_integrated_plot[k][0,-1]],[0]])+np.array([[1],[np.sum(data)]]),axis=1)
                    if self.data_integrated_plot[k].shape[1] > self.max_size_integrated:
                        self.data_integrated_plot[k] = self.data_integrated_plot[k][:,self.data_integrated_plot[k].shape[1]-200:]
                    self.ui.RoiCurve_H[k].setData(y=np.mean(data,axis=0), x=xvals)
                    self.ui.RoiCurve_V[k].setData(y=yvals, x=np.mean(data,axis=1))
                    self.ui.RoiCurve_integrated[k].setData(y=self.data_integrated_plot[k][1,:], x=self.data_integrated_plot[k][0,:])
                    self.data_to_export['data2D'][self.title+'_{:s}'.format(k)]=OrderedDict(data=data,
                        x_axis=dict(data=x_axis, units=self.scaling_options['scaled_xaxis']['units'], label=self.scaling_options['scaled_xaxis']['label']),
                        y_axis=dict(data=y_axis, units=self.scaling_options['scaled_yaxis']['units'], label=self.scaling_options['scaled_yaxis']['label']))

                    self.data_to_export['data1D'][self.title+'_Hlineout_{:s}'.format(k)]=OrderedDict(data=np.mean(data,axis=0),
                        x_axis=dict(data=x_axis, units=self.scaling_options['scaled_xaxis']['units'], label=self.scaling_options['scaled_xaxis']['label']))
                    self.data_to_export['data1D'][self.title+'_Vlineout_{:s}'.format(k)]=OrderedDict(data=np.mean(data,axis=1),
                        x_axis=dict(data=y_axis, units=self.scaling_options['scaled_yaxis']['units'], label=self.scaling_options['scaled_yaxis']['label']))
                    self.data_to_export['data0D'][self.title+'_Integrated_{:s}'.format(k)]=OrderedDict(data=np.sum(data))
            self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
            self.data_to_export_signal.emit(self.data_to_export)
            self.ROI_changed.emit()
        except Exception as e:
            pass

    def roiClicked(self):
        roistate=self.ui.roiBtn.isChecked()

        self.ui.ROIs_widget.setVisible(roistate)
        for k,roi in self.ui.ROIs.items():
            roi.setVisible(roistate)
            self.ui.RoiCurve_H[k].setVisible(roistate)
            self.ui.RoiCurve_V[k].setVisible(roistate)
            self.ui.RoiCurve_integrated[k].setVisible(roistate)

        if self.ui.roiBtn.isChecked():
            self.roiChanged()

        self.show_lineouts()

        if len(self.ui.ROIs)==0 and roistate:
            self.roi_settings.child(("ROIs")).addNew('RectROI')

    def roi_tree_changed(self,param,changes):

        for param, change, data in changes:
            path = self.roi_settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':#new roi to create
                param_name=data[0].name()
                roi_type=data[0].children()[0].value()
                color=data[0].child(('Color')).value().rgba()
                pos=[data[0].child(('position')).child('x').value(),data[0].child(('position')).child('y').value()]
                size=[data[0].child(('size')).child('dx').value(),data[0].child(('size')).child('dy').value()]
                angle=data[0].child(('angle')).value()

                par=self.roi_settings.child((childName)).child((param_name))

                newindex=int(param_name[-2:])

                if roi_type == 'RectROI':
                    newroi=RectROI(index=newindex)
                else:
                    newroi=EllipseROI(index=newindex)
                newroi.sigRegionChanged.connect(self.roiChanged)
                newroi.sigRegionChangeFinished.connect(self.ROI_changed_finished.emit)
                newroi.setPen(self.color_list[newindex])
                newroi.index_signal[int].connect(self.update_roi_tree)
                try:
                    self.roi_settings.sigTreeStateChanged.disconnect()
                except:
                    pass
                par.child(('Color')).setValue(QtGui.QColor(*self.color_list[newindex]))
                self.roi_settings.sigTreeStateChanged.connect(self.roi_tree_changed)
                self.image_widget.plotitem.addItem(newroi)

                newroi.pos

                self.ui.ROIs["ROI_%02.0d" % newindex]=newroi
                self.ui.RoiCurve_H["ROI_%02.0d" % newindex]=self.ui.Lineout_H.plot(pen=QtGui.QColor(*self.color_list[newindex]))
                self.ui.RoiCurve_V["ROI_%02.0d" % newindex]=self.ui.Lineout_V.plot(pen=QtGui.QColor(*self.color_list[newindex]))
                self.ui.RoiCurve_integrated["ROI_%02.0d" % newindex]=self.ui.Lineout_integrated.plot(pen=QtGui.QColor(*self.color_list[newindex]))
                self.data_integrated_plot["ROI_%02.0d" % newindex]=np.zeros((2,1))
                #self.data_to_export["%02.0d" % newindex]=None
                self.roiChanged()

            elif change == 'value':

                if param.name() == 'Color' or param.name() == 'angle' :
                    parent=param.parent().name()
                else:
                    parent=param.parent().parent().name()
                self.update_roi(parent,param.name(),param.value())



            elif change == 'parent':
                self.image_widget.plotitem.removeItem(self.ui.ROIs[param.name()])
                self.ui.ROIs.pop(param.name())
                self.ui.Lineout_H.removeItem(self.ui.RoiCurve_H[param.name()])
                self.ui.RoiCurve_H.pop(param.name())
                self.ui.Lineout_V.removeItem(self.ui.RoiCurve_V[param.name()])
                self.ui.RoiCurve_V.pop(param.name())
                self.ui.Lineout_integrated.removeItem(self.ui.RoiCurve_integrated[param.name()])
                self.ui.RoiCurve_integrated.pop(param.name())

    def save_ROI(self):

        try:
            data=self.roi_settings.saveState()
            path=self.select_file()
            if path is not None:
                with open(path, 'wb') as f:
                    pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            pass


    def scale_axis(self,xaxis,yaxis):
        return xaxis*self.scaling_options['scaled_xaxis']['scaling']+self.scaling_options['scaled_xaxis']['offset'],\
               yaxis*self.scaling_options['scaled_yaxis']['scaling']+self.scaling_options['scaled_yaxis']['offset']

    def select_file(self,start_path=None,save=True):
        try:
            if save:
                fname = QtWidgets.QFileDialog.getSaveFileName(None, 'Enter a .roi2D file name',start_path,"roi2D file (*.roi2D)")
            else:
                fname=QtWidgets.QFileDialog.getOpenFileName(None, 'Select a .roi2D file name',start_path,"roi2D file (*.roi2D)")
            fname=fname[0]
            if not( not(fname)): #execute if the user didn't cancel the file selection
                (head,filename)=os.path.split(fname)
                (filename,ext)=os.path.splitext(fname)
                fname=os.path.join(head,filename+".roi2D")
            return fname

        except Exception as e:
            pass



    def selected_region_changed(self):
        if self.ui.ROIselect_pb.isChecked():
            pos=self.ui.ROIselect.pos()
            size=self.ui.ROIselect.size()
            self.ROI_select_signal.emit(QRectF(pos[0],pos[1],size[0],size[1]))


    def set_autolevels(self):
        self.autolevels=self.ui.auto_levels_pb.isChecked()
        if not self.ui.auto_levels_pb.isChecked():
            self.ui.histogram_red.regionChanged()
            self.ui.histogram_green.regionChanged()
            self.ui.histogram_blue.regionChanged()

        self.ui.histogram_red.region.setVisible(not self.autolevels)
        self.ui.histogram_green.region.setVisible(not self.autolevels)
        self.ui.histogram_blue.region.setVisible(not self.autolevels)

    def set_scaling_axes(self,scaling_options=None):
        """
        metod used to update the scaling of the right and top axes in order to translate pixels to real coordinates
        scaling_options=dict(scaled_xaxis=dict(label="",units=None,offset=0,scaling=1),scaled_yaxis=dict(label="",units=None,offset=0,scaling=1))
        """
        if scaling_options is not None:
            self.scaling_options=copy.deepcopy(scaling_options)
        self.scaled_xaxis.scaling=self.scaling_options['scaled_xaxis']['scaling']
        self.scaled_xaxis.offset=self.scaling_options['scaled_xaxis']['offset']
        self.scaled_xaxis.setLabel(text=self.scaling_options['scaled_xaxis']['label'],units=self.scaling_options['scaled_xaxis']['units'])
        self.scaled_yaxis.scaling=self.scaling_options['scaled_yaxis']['scaling']
        self.scaled_yaxis.offset=self.scaling_options['scaled_yaxis']['offset']
        self.scaled_yaxis.setLabel(text=self.scaling_options['scaled_yaxis']['label'],units=self.scaling_options['scaled_yaxis']['units'])

        self.scaled_xaxis.linkedViewChanged(self.image_widget.view)
        self.scaled_yaxis.linkedViewChanged(self.image_widget.view)

    def setImage(self,data_red=None,data_green=None,data_blue=None):
        try:
            if data_red is not None:
                if len(data_red.shape)>2:
                    data_red=np.mean(data_red,axis=0)
                if self.ui.FlipUD_pb.isChecked():
                    data_red=np.flipud(data_red)
                if self.ui.FlipLR_pb.isChecked():
                    data_red=np.fliplr(data_red)
                if self.ui.rotate_pb.isChecked():
                    data_red = np.transpose(data_red)

            if data_green is not None:
                if len(data_green.shape)>2:
                    data_green=np.mean(data_green,axis=0)
                if self.ui.FlipUD_pb.isChecked():
                    data_green=np.flipud(data_green)
                if self.ui.FlipLR_pb.isChecked():
                    data_green=np.fliplr(data_green)
                if self.ui.rotate_pb.isChecked():
                    data_green = np.transpose(data_green)

            if data_blue is not None:
                if len(data_blue.shape)>2:
                    data_blue=np.mean(data_blue,axis=0)
                if self.ui.FlipUD_pb.isChecked():
                    data_blue=np.flipud(data_blue)
                if self.ui.FlipLR_pb.isChecked():
                    data_blue=np.fliplr(data_blue)
                if self.ui.rotate_pb.isChecked():
                    data_blue = np.transpose(data_blue)

            red_flag= data_red is not None
            self.isdata["red"]=red_flag
            green_flag= data_green is not None
            self.isdata["green"]=green_flag
            blue_flag= data_blue is not None
            self.isdata["blue"]=blue_flag

            self.data_to_export=OrderedDict(name=self.title,data0D=OrderedDict(),data1D=OrderedDict(),data2D=OrderedDict())
            self.image=edict(blue=data_blue,green=data_green,red=data_red)
            if red_flag:
                bounds=QRectF(0,0,data_red.shape[1],data_red.shape[0])
            elif green_flag:
                bounds=QRectF(0,0,data_green.shape[1],data_green.shape[0])
            elif blue_flag:
                bounds=QRectF(0,0,data_blue.shape[1],data_blue.shape[0])
            self.ui.ROIselect.maxBounds=bounds

            self.ui.img_red.setImage(data_red,autoLevels = self.autolevels)
            self.ui.img_green.setImage(data_green,autoLevels = self.autolevels)
            self.ui.img_blue.setImage(data_blue,autoLevels = self.autolevels)

            if self.ui.red_cb.isChecked() and red_flag==False: #turn it off if it was on but there is no data
                self.ui.red_cb.setChecked(False)
            elif red_flag:
                self.ui.red_cb.setChecked(True)

            #self.ui.red_cb.setChecked(red_flag)
            #self.ui.red_cb.setVisible(red_flag)
            self.ui.img_red.setVisible(self.ui.red_cb.isChecked())
            if self.ui.Show_histogram.isChecked():
                self.ui.histogram_red.setVisible(self.ui.red_cb.isChecked())


            if self.ui.green_cb.isChecked() and green_flag==False: #turn it off if it was on but there is no data
                self.ui.green_cb.setChecked(False)
            elif green_flag:
                self.ui.green_cb.setChecked(True)
            #self.ui.green_cb.setVisible(green_flag)
            #self.ui.green_cb.setChecked(green_flag)
            self.ui.img_green.setVisible(self.ui.green_cb.isChecked())
            if self.ui.Show_histogram.isChecked():
                self.ui.histogram_green.setVisible(self.ui.green_cb.isChecked())


            if self.ui.blue_cb.isChecked() and blue_flag==False: #turn it off if it was on but there is no data
                self.ui.blue_cb.setChecked(False)
            elif blue_flag:
                self.ui.blue_cb.setChecked(True)
            #self.ui.blue_cb.setVisible(blue_flag)
            #self.ui.blue_cb.setChecked(blue_flag)
            self.ui.img_blue.setVisible(self.ui.blue_cb.isChecked())
            if self.ui.Show_histogram.isChecked():
                self.ui.histogram_blue.setVisible(self.ui.blue_cb.isChecked())

            self._x_axis=np.linspace(0,data_red.shape[1]-1,data_red.shape[1])
            self._y_axis=np.linspace(0,data_red.shape[0]-1,data_red.shape[0])
            self.x_axis_scaled,self.y_axis_scaled=self.scale_axis(self._x_axis,self._y_axis)

            ind = 0
            if red_flag:
                self.data_to_export['data2D']['CH{:03d}'.format(ind)]=OrderedDict(data=data_red,
                        x_axis=dict(data=self.x_axis_scaled, units=self.scaling_options['scaled_xaxis']['units'], label=self.scaling_options['scaled_xaxis']['label']),
                        y_axis=dict(data=self.y_axis_scaled, units=self.scaling_options['scaled_yaxis']['units'], label=self.scaling_options['scaled_yaxis']['label']))
                ind +=1

            if green_flag:
                self.data_to_export['data2D']['CH{:03d}'.format(ind)]=OrderedDict(data=data_green,
                        x_axis=dict(data=self.x_axis_scaled, units=self.scaling_options['scaled_xaxis']['units'], label=self.scaling_options['scaled_xaxis']['label']),
                        y_axis=dict(data=self.y_axis_scaled, units=self.scaling_options['scaled_yaxis']['units'], label=self.scaling_options['scaled_yaxis']['label']))
                ind += 1

            if blue_flag:
                self.data_to_export['data2D']['CH{:03d}'.format(ind)]=OrderedDict(data=data_blue,
                        x_axis=dict(data=self.x_axis_scaled, units=self.scaling_options['scaled_xaxis']['units'], label=self.scaling_options['scaled_xaxis']['label']),
                        y_axis=dict(data=self.y_axis_scaled, units=self.scaling_options['scaled_yaxis']['units'], label=self.scaling_options['scaled_yaxis']['label']))
                ind += 1

            if self.ui.roiBtn.isChecked():
                self.roiChanged()
            else:
                self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
                self.data_to_export_signal.emit(self.data_to_export)

            if self.ui.isocurve_pb.isChecked() and red_flag:
                self.ui.iso.setData(pg.gaussianFilter(data_red, (2, 2)))

            if self.ui.crosshair_pb.isChecked():
                self.crosshairChanged()

        except Exception as e:
            print(e)

    def setImageTemp(self,data_red=None,data_green=None,data_blue=None):
        """
        to plot temporary data, for instance when all pixels are not yet populated...
        """

        if data_red is not None:
            if len(data_red.shape)>2:
                data_red=np.mean(data_red,axis=0)
            if self.ui.FlipUD_pb.isChecked():
                data_red=np.flipud(data_red)
            if self.ui.FlipLR_pb.isChecked():
                data_red=np.fliplr(data_red)
            if self.ui.rotate_pb.isChecked():
                data_red=np.transpose(data_red)
        if data_green is not None:
            if len(data_green.shape)>2:
                data_green=np.mean(data_green,axis=0)
            if self.ui.FlipUD_pb.isChecked():
                data_green=np.flipud(data_green)
            if self.ui.FlipLR_pb.isChecked():
                data_green=np.fliplr(data_green)
            if self.ui.rotate_pb.isChecked():
                data_green = np.transpose(data_green)
        if data_blue is not None:
            if len(data_blue.shape)>2:
                data_blue=np.mean(data_blue,axis=0)
            if self.ui.FlipUD_pb.isChecked():
                data_blue=np.flipud(data_blue)
            if self.ui.FlipLR_pb.isChecked():
                data_blue=np.fliplr(data_blue)
            if self.ui.rotate_pb.isChecked():
                data_blue = np.transpose(data_blue)


        if data_red is not None:
            self.ui.img_red.setImage(data_red,autoLevels = self.autolevels)
        if data_green is not None:
            self.ui.img_green.setImage(data_green,autoLevels = self.autolevels)
        if data_blue is not None:
            self.ui.img_blue.setImage(data_blue,autoLevels = self.autolevels)

    def setObjectName(self,txt):
        self.parent.setObjectName(txt)

    def setup_Roi_widget(self):
        widgetROIS=QtWidgets.QWidget()
        self.ui.verticalLayout_settings=QtWidgets.QVBoxLayout()
        horlayout0=QtWidgets.QHBoxLayout()
        self.ui.label=QtWidgets.QLabel('Use image:')
        self.ui.choose_trace_ROI_cb=QtWidgets.QComboBox()
        self.ui.choose_trace_ROI_cb.addItems(['red','green','blue'])
        horlayout0.addWidget(self.ui.label)
        horlayout0.addWidget(self.ui.choose_trace_ROI_cb)

        horlayout=QtWidgets.QHBoxLayout()
        self.ui.save_ROI_pb=QtWidgets.QPushButton('Save ROIs')
        self.ui.load_ROI_pb=QtWidgets.QPushButton('Load ROIs')
        horlayout.addWidget(self.ui.save_ROI_pb)
        horlayout.addWidget(self.ui.load_ROI_pb)
        self.ui.verticalLayout_settings.addLayout(horlayout0)
        self.ui.verticalLayout_settings.addLayout(horlayout)


        self.ui.ROI_Tree= ParameterTree()
        self.ui.verticalLayout_settings.addWidget(self.ui.ROI_Tree)
        widgetROIS.setLayout(self.ui.verticalLayout_settings)
        widgetROIS.setMaximumWidth(300)
        return widgetROIS



    def show_hide_histogram(self):
        if self.isdata["blue"] and self.ui.blue_cb.isChecked():
            self.ui.histogram_blue.setVisible(self.ui.Show_histogram.isChecked())
            self.ui.histogram_blue.setLevels(self.image.blue.min(), self.image.blue.max())
        if self.isdata["green"] and self.ui.green_cb.isChecked():
            self.ui.histogram_green.setVisible(self.ui.Show_histogram.isChecked())
            self.ui.histogram_green.setLevels(self.image.green.min(), self.image.green.max())
        if self.isdata["red"] and self.ui.red_cb.isChecked():
            self.ui.histogram_red.setVisible(self.ui.Show_histogram.isChecked())
            self.ui.histogram_red.setLevels(self.image.red.min(), self.image.red.max())

        QtWidgets.QApplication.processEvents()

    def show_hide_iso(self):
        if self.ui.isocurve_pb.isChecked():
            self.ui.iso.show()
            self.ui.isoLine.show()
            self.ui.Show_histogram.setChecked(True)
            self.show_hide_histogram()
            if self.ui.isocurve_pb.isChecked() and self.image.red is not None:
                self.ui.iso.setData(pg.gaussianFilter(self.image.red, (2, 2)))
        else:
            self.ui.iso.hide()
            self.ui.isoLine.hide()


    def show_lineouts(self):
        state=self.ui.roiBtn.isChecked() or self.ui.crosshair_pb.isChecked()
        if state:
            showLineout_H = True
            showLineout_V = True
            showroiintegrated = True
            self.ui.Lineout_H.setMouseEnabled(True, True)
            self.ui.Lineout_V.setMouseEnabled(True, True)
            self.ui.Lineout_integrated.setMouseEnabled(True, True)
            self.ui.Lineout_H.showAxis('left')
            self.ui.Lineout_V.showAxis('left')
            self.ui.Lineout_integrated.showAxis('left')

        else:
            showLineout_H = False
            showLineout_V = False
            showroiintegrated = False

            self.ui.Lineout_H.setMouseEnabled(False, False)
            self.ui.Lineout_V.setMouseEnabled(False, False)
            self.ui.Lineout_integrated.setMouseEnabled(False, False)
            self.ui.Lineout_H.hideAxis('left')
            self.ui.Lineout_V.hideAxis('left')
            self.ui.Lineout_integrated.hideAxis('left')

        self.ui.Lineout_H.setVisible(showLineout_H)
        self.ui.Lineout_V.setVisible(showLineout_V)
        self.ui.Lineout_integrated.setVisible(showroiintegrated)

        self.ui.Lineout_H.update()
        self.ui.Lineout_V.update()
        self.ui.Lineout_integrated.update()

        QtGui.QGuiApplication.processEvents()
        self.ui.splitter_VRight.splitterMoved[int,int].emit(0.6*self.parent.height(),1)
        self.ui.splitter.moveSplitter(0.6*self.parent.width(),1)
        self.ui.splitter_VLeft.moveSplitter(0.6*self.parent.height(),1)
        self.ui.splitter_VLeft.splitterMoved[int,int].emit(0.6*self.parent.height(),1)
        QtGui.QGuiApplication.processEvents()


    def show_ROI_select(self):
        self.ui.ROIselect.setVisible(self.ui.ROIselect_pb.isChecked())


    def update_image_flip(self):
        self.setImageTemp(self.ui.img_red.image,self.ui.img_green.image,self.ui.img_blue.image)

    def update_roi(self,index_roi,param_name,param_value):

        if param_name == 'Color':
            self.ui.ROIs[index_roi].setPen(param_value)
            self.ui.RoiCurve_H[index_roi].setPen(param_value)
            self.ui.RoiCurve_V[index_roi].setPen(param_value)
            self.ui.RoiCurve_integrated[index_roi].setPen(param_value)
        elif param_name == 'x':
            pos=self.ui.ROIs[index_roi].pos()
            self.ui.ROIs[index_roi].setPos((param_value,pos[1]))
        elif param_name == 'y':
            pos=self.ui.ROIs[index_roi].pos()
            self.ui.ROIs[index_roi].setPos((pos[0],param_value))
        elif param_name == 'angle':
            self.ui.ROIs[index_roi].setAngle(param_value)
        elif param_name == 'dx':
            size=self.ui.ROIs[index_roi].size()
            self.ui.ROIs[index_roi].setSize((param_value,size[1]))
        elif param_name == 'dy':
            size=self.ui.ROIs[index_roi].size()
            self.ui.ROIs[index_roi].setSize((size[0],param_value))

    @pyqtSlot(int)
    def update_roi_tree(self,index):
        roi=self.ui.ROIs['ROI_%02.0d'%index]
        pos=roi.pos()
        size=roi.size()
        angle=roi.angle()
        par=self.roi_settings.child(*('ROIs','ROI_%02.0d'%index))
        try:
            self.roi_settings.sigTreeStateChanged.disconnect()
        except:
            pass
        par.child(*('position','x')).setValue(pos[0])
        par.child(*('position','y')).setValue(pos[1])
        par.child(*('size','dx')).setValue(size[0])
        par.child(*('size','dy')).setValue(size[1])
        par.child(('angle')).setValue(angle)

        self.roi_settings.sigTreeStateChanged.connect(self.roi_tree_changed)




    def update_selection_area_visibility(self):
        bluestate=self.ui.blue_cb.isChecked()
        self.ui.img_blue.setVisible(bluestate)
        #self.ui.histogram_blue.setVisible(bluestate)

        greenstate=self.ui.green_cb.isChecked()
        self.ui.img_green.setVisible(greenstate)
        #self.ui.histogram_green.setVisible(greenstate)

        redstate=self.ui.red_cb.isChecked()
        self.ui.img_red.setVisible(redstate)
        #self.ui.histogram_red.setVisible(redstate)

    def update_crosshair_data(self,posx,posy,name=""):
        try:
            (posx_scaled,posy_scaled)=self.scale_axis(posx,posy)
            self.crosshair_dragged.emit(posx_scaled,posy_scaled)
            x_axis_scaled,y_axis_scaled=self.scale_axis(self._x_axis,self._y_axis)
            indx=utils.find_index(self._x_axis,posx)[0][0]
            indy=utils.find_index(self._y_axis,posy)[0][0]

            self.crosshairChanged(indx,indy)

            if self.isdata["blue"]:
                z_blue=self.image["blue"][indy,indx]
                self.ui.z_label_blue.setText("{:.6e}".format(z_blue))
            if self.isdata["green"]:
                z_green=self.image["green"][indy,indx]
                self.ui.z_label_green.setText("{:.6e}".format(z_green))
            if self.isdata["red"]:
                z_red=self.image["red"][indy,indx]
                self.ui.z_label_red.setText("{:.6e}".format(z_red))


            self.ui.x_label.setText("x={:.6e} ".format(posx_scaled))
            self.ui.y_label.setText("y={:.6e} ".format(posy_scaled))

        except Exception as e:
            pass

    def updateIsocurve(self):
        self.ui.iso.setLevel(self.ui.isoLine.value())


    @property
    def x_axis(self):
        return self.x_axis_scaled

    @x_axis.setter
    def x_axis(self, x_axis):
        label = ''
        units = ''
        if isinstance(x_axis, dict):
            if 'data' in x_axis:
                xdata=x_axis['data']
            if 'label' in x_axis:
                label=x_axis['label']
            if 'units' in x_axis:
                units= x_axis['units']
        else:
            xdata=x_axis

        x_offset = np.min(xdata)
        x_scaling = xdata[1] - xdata[0]
        self.scaling_options['scaled_xaxis'].update(dict(offset=x_offset, scaling=x_scaling, label=label, units=units))
        self.set_scaling_axes(self.scaling_options)

    @property
    def y_axis(self):
        return self.y_axis_scaled

    @y_axis.setter
    def y_axis(self, y_axis):
        label = ''
        units = ''
        if isinstance(y_axis, dict):
            if 'data' in y_axis:
                ydata=y_axis['data']
            if 'label' in y_axis:
                label=y_axis['label']
            if 'units' in y_axis:
                units= y_axis['units']
        else:
            ydata=y_axis
        y_offset = np.min(ydata)
        y_scaling = ydata[1] - ydata[0]
        self.scaling_options['scaled_yaxis'].update(dict(offset=y_offset, scaling=y_scaling, label=label, units=units))
        self.set_scaling_axes(self.scaling_options)


class ROIScalableGroup(pTypes.GroupParameter):
    def __init__(self, **opts):
        opts['type'] = 'group'
        opts['addText'] = "Add"
        opts['addList'] = ['RectROI', 'EllipseROI']
        pTypes.GroupParameter.__init__(self, **opts)
    
    def addNew(self, typ):
        indexes=[int(par.name()[-2:]) for par in self.children()]
        if indexes==[]:
            newindex=0
        else:
            newindex=max(indexes)+1
        child={'name': 'ROI_%02.0d' % newindex, 'type': 'group', 'children': [
                {'name': 'Type', 'type': 'str', 'value': typ, 'readonly': True},
                {'name': 'Color', 'type': 'color', 'value': "FF0"},
                {'name': 'position', 'type': 'group', 'children': [
                        {'name': 'x', 'type': 'float', 'value': 0, 'step':1},
                        {'name': 'y', 'type': 'float', 'value': 0, 'step':1}
                ]},
                {'name': 'size', 'type': 'group', 'children': [
                        {'name': 'dx', 'type': 'float', 'value': 10, 'step':1},
                        {'name': 'dy', 'type': 'float', 'value': 10, 'step':1}
                ]},
                {'name': 'angle', 'type': 'float', 'value': 0, 'step': 1}
                
                ],'removable':True, 'renamable':False
               }

        self.addChild(child)







if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Form=DockArea()
    Form=QtWidgets.QWidget()
    
    prog = Viewer2D(Form);
    prog.set_scaling_axes(scaling_options=dict(scaled_xaxis=dict(label="eV",units=None,offset=20,scaling=2),scaled_yaxis=dict(label="time",units='s',offset=-10,scaling=0.1)))
    Nx=100;
    Ny=200
    data_random = pg.np.random.normal(size=(Ny, Nx))
    x=pg.np.linspace(0,Nx-1,Nx)
    y=pg.np.linspace(0,Ny-1,Ny)
    from pymodaq.daq_utils.daq_utils import  gauss2D
    data_red=data_random+3*gauss2D(x,0.2*Nx,Nx/5,y,0.3*Ny,Ny/5,1)
    data_red = pg.gaussianFilter(data_red, (2, 2))
    data_green=data_random+3*gauss2D(x,0.6*Nx,Nx/5,y,0.6*Ny,Ny/5,1)
    data_green = pg.gaussianFilter(data_green, (2, 2))
    data_blue=data_random+3*gauss2D(x,0.7*Nx,Nx/5,y,0.2*Ny,Ny/5,1)
    data_blue = pg.gaussianFilter(data_blue, (2, 2))
    
    prog.setImage(data_blue=data_blue,data_green=None,data_red=data_red)
    
    prog.add_ROI('ElipseROI')
    
    #prog.ui.imag_blue.set

    #prog.ui.img_blue.setScale(2)
    #import hyperspy.api as hs

    #filename='C:\\Users\\Weber\\Downloads\\CBEDs pour seb\\CBED position 3 laser 200mW 4s bin 1 exposure time 1.2 m STEM 3.dm4'
    #cbed1=hs.load(filename)
    #prog.setImage(cbed1.data)

    
    Form.show()
    sys.exit(app.exec_())
