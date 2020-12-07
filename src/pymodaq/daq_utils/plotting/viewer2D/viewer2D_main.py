from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel, QCheckBox
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QRectF, QPointF
import sys
from collections import OrderedDict
from pymodaq.daq_utils.managers.roi_manager import ROIManager
import pyqtgraph as pg

from pymodaq.daq_utils.plotting.viewer2D.viewer2D_basic import ImageWidget
from pymodaq.daq_utils.plotting.plot_utils import AxisItem_Scaled
from pymodaq.daq_utils.plotting.graph_items import ImageItem, PlotCurveItem, TriangulationItem
from pymodaq.daq_utils.plotting.crosshair import Crosshair

import numpy as np
from easydict import EasyDict as edict
import copy
from pymodaq.daq_utils.gui_utils import DockArea

import pymodaq.daq_utils.daq_utils as utils
import datetime
from pymodaq.resources.QtDesigner_Ressources import QtDesigner_ressources_rc

from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

Gradients.update(OrderedDict([
    ('red', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (255, 0, 0, 255))], 'mode': 'rgb'}),
    ('green', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (0, 255, 0, 255))], 'mode': 'rgb'}),
    ('blue', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (0, 0, 255, 255))], 'mode': 'rgb'}), ]))


class Viewer2D(QObject):
    data_to_export_signal = pyqtSignal(
        OrderedDict)  # OrderedDict(name=self.DAQ_type,data0D=None,data1D=None,data2D=None)
    crosshair_dragged = pyqtSignal(float, float)  # signal used to pass crosshair position to other modules in
    # scaled axes units
    sig_double_clicked = pyqtSignal(float, float)
    ROI_select_signal = pyqtSignal(QRectF)
    ROI_changed = pyqtSignal()
    ROI_changed_finished = pyqtSignal()

    def __init__(self, parent=None, scaling_options=utils.ScalingOptions(scaled_xaxis=utils.ScaledAxis(),
                                                                         scaled_yaxis=utils.ScaledAxis())):
        super().__init__()
        # setting the gui

        self.title = 'viewer2D'
        if parent is None:
            parent = QtWidgets.QWidget()
        self.parent = parent

        self.max_size_integrated = 200
        self.scaling_options = copy.deepcopy(scaling_options)
        self.viewer_type = 'Data2D'  # by default
        self.title = ""

        self._x_axis = None
        self._y_axis = None
        self.x_axis_scaled = None
        self.y_axis_scaled = None

        self.raw_data = None
        self.image_widget = None
        self.isdata = edict(blue=False, green=False, red=False, spread=False)
        self.color_list = utils.plot_colors

        self.data_to_export = OrderedDict([])

        self.setupUI()

    def setupButtons(self, buttons_layout):
        self.ui.Show_histogram = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/Histogram.png")), '')
        self.ui.Show_histogram.setCheckable(True)
        buttons_layout.addWidget(self.ui.Show_histogram)

        self.ui.roiBtn = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/Region.png")), '')
        self.ui.roiBtn.setCheckable(True)
        buttons_layout.addWidget(self.ui.roiBtn)

        self.ui.isocurve_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/meshPlot.png")), '')
        self.ui.isocurve_pb.setCheckable(True)
        buttons_layout.addWidget(self.ui.isocurve_pb)

        self.ui.Ini_plot_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/Refresh.png")), '')
        buttons_layout.addWidget(self.ui.Ini_plot_pb)

        self.ui.aspect_ratio_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/Zoom_1_1.png")), '')
        self.ui.aspect_ratio_pb.setCheckable(True)
        buttons_layout.addWidget(self.ui.aspect_ratio_pb)

        self.ui.auto_levels_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/autoscale.png")), '')
        self.ui.auto_levels_pb.setCheckable(True)
        buttons_layout.addWidget(self.ui.auto_levels_pb)

        self.ui.crosshair_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/reset.png")), '')
        self.ui.crosshair_pb.setCheckable(True)
        buttons_layout.addWidget(self.ui.crosshair_pb)

        self.ui.ROIselect_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/Select_24.png")), '')
        self.ui.ROIselect_pb.setCheckable(True)
        buttons_layout.addWidget(self.ui.ROIselect_pb)

        self.ui.FlipUD_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/scale_vertically.png")), '')
        self.ui.FlipUD_pb.setCheckable(True)
        buttons_layout.addWidget(self.ui.FlipUD_pb)

        self.ui.FlipLR_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/scale_horizontally.png")), '')
        self.ui.FlipLR_pb.setCheckable(True)
        buttons_layout.addWidget(self.ui.FlipLR_pb)

        self.ui.rotate_pb = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/rotation2.png")), '')
        self.ui.rotate_pb.setCheckable(True)
        buttons_layout.addWidget(self.ui.rotate_pb)

        self.ui.x_label = QLabel('x:')
        self.ui.y_label = QLabel('y:')
        xywidget = QtWidgets.QWidget()
        xywidget.setLayout(QtWidgets.QVBoxLayout())

        buttons_layout.addWidget(xywidget)
        xywidget.layout().addWidget(self.ui.x_label)
        xywidget.layout().addWidget(self.ui.y_label)

        red = QtWidgets.QWidget()
        red.setLayout(QtWidgets.QVBoxLayout())
        self.ui.red_cb = QCheckBox('Red')
        self.ui.z_label_red = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/r_icon.png")), 'z_red')
        self.ui.z_label_red.setFlat(True)
        red.layout().addWidget(self.ui.red_cb)
        red.layout().addWidget(self.ui.z_label_red)
        buttons_layout.addWidget(red)

        green = QtWidgets.QWidget()
        green.setLayout(QtWidgets.QVBoxLayout())
        self.ui.green_cb = QCheckBox('Green')
        self.ui.z_label_green = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/g_icon.png")), 'z_green')
        self.ui.z_label_green.setFlat(True)
        green.layout().addWidget(self.ui.green_cb)
        green.layout().addWidget(self.ui.z_label_green)
        buttons_layout.addWidget(green)

        blue = QtWidgets.QWidget()
        blue.setLayout(QtWidgets.QVBoxLayout())
        self.ui.blue_cb = QCheckBox('Blue')
        self.ui.z_label_blue = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/b_icon.png")), 'z_blue')
        self.ui.z_label_blue.setFlat(True)
        blue.layout().addWidget(self.ui.blue_cb)
        blue.layout().addWidget(self.ui.z_label_blue)
        buttons_layout.addWidget(blue)

        spread = QtWidgets.QWidget()
        spread.setLayout(QtWidgets.QVBoxLayout())
        self.ui.spread_cb = QCheckBox('spread')
        self.ui.z_label_spread = QPushButton(QIcon(QPixmap(":/icons/Icon_Library/grey_icon.png")), 'z_spread')
        self.ui.z_label_spread.setFlat(True)
        spread.layout().addWidget(self.ui.spread_cb)
        spread.layout().addWidget(self.ui.z_label_spread)
        buttons_layout.addWidget(spread)

        buttons_layout.addStretch()

    def setupGraphs(self, graphs_layout):
        self.ui.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        graphs_layout.addWidget(self.ui.splitter)

        self.ui.widget_histo = QtWidgets.QWidget()
        graphs_layout.addWidget(self.ui.widget_histo)

        self.ui.splitter_VLeft = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.ui.splitter_VRight = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        self.ui.splitter.addWidget(self.ui.splitter_VLeft)
        self.ui.splitter.addWidget(self.ui.splitter_VRight)

        self.image_widget = ImageWidget()
        self.ui.graphicsView = self.image_widget
        self.ui.Lineout_H = pg.PlotWidget()
        self.ui.Lineout_V = pg.PlotWidget()
        self.ui.Lineout_integrated = pg.PlotWidget()

        self.ui.splitter_VLeft.addWidget(self.ui.graphicsView)
        self.ui.splitter_VLeft.addWidget(self.ui.Lineout_H)
        self.ui.splitter_VRight.addWidget(self.ui.Lineout_V)
        self.ui.splitter_VRight.addWidget(self.ui.Lineout_integrated)

        self.ui.plotitem = self.image_widget.plotitem  # for backward compatibility

        axis = self.ui.plotitem.getAxis('bottom')
        axis.setLabel(text='', units='Pxls')

        axisl = self.ui.plotitem.getAxis('left')
        axisl.setLabel(text='', units='Pxls')

        self.autolevels = False
        self.ui.auto_levels_pb.clicked.connect(self.set_autolevels)

        self.scaled_yaxis = AxisItem_Scaled('right')
        self.scaled_xaxis = AxisItem_Scaled('top')

        self.image_widget.view.sig_double_clicked.connect(self.double_clicked)
        self.image_widget.plotitem.layout.addItem(self.scaled_xaxis, *(1, 1))
        self.image_widget.plotitem.layout.addItem(self.scaled_yaxis, *(2, 2))
        self.scaled_xaxis.linkToView(self.image_widget.view)
        self.scaled_yaxis.linkToView(self.image_widget.view)
        self.set_scaling_axes(self.scaling_options)
        self.image_widget.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        self.ui.img_red = ImageItem()
        self.ui.img_green = ImageItem()
        self.ui.img_blue = ImageItem()
        self.ui.img_spread = TriangulationItem()

        # self.ui.img_red.sig_double_clicked.connect(self.double_clicked)
        self.ui.img_red.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
        self.ui.img_green.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
        self.ui.img_blue.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
        self.ui.img_red.setOpts(axisOrder='row-major')
        self.ui.img_green.setOpts(axisOrder='row-major')
        self.ui.img_blue.setOpts(axisOrder='row-major')

    def setupHisto(self, histo_layout):
        self.ui.widget_histo.setLayout(histo_layout)
        self.ui.histogram_red = pg.HistogramLUTWidget()
        self.ui.histogram_red.setImageItem(self.ui.img_red)
        self.ui.histogram_green = pg.HistogramLUTWidget()
        self.ui.histogram_green.setImageItem(self.ui.img_green)
        self.ui.histogram_blue = pg.HistogramLUTWidget()
        self.ui.histogram_blue.setImageItem(self.ui.img_blue)
        self.ui.histogram_spread = pg.HistogramLUTWidget()
        self.ui.histogram_spread.setImageItem(self.ui.img_spread)

        histo_layout.addWidget(self.ui.histogram_red)
        histo_layout.addWidget(self.ui.histogram_green)
        histo_layout.addWidget(self.ui.histogram_blue)
        histo_layout.addWidget(self.ui.histogram_spread)

        Ntick = 3
        colors_red = [(int(r), 0, 0) for r in pg.np.linspace(0, 255, Ntick)]
        colors_green = [(0, int(g), 0) for g in pg.np.linspace(0, 255, Ntick)]
        colors_blue = [(0, 0, int(b)) for b in pg.np.linspace(0, 255, Ntick)]
        colors_spread = [(int(b), int(b), int(b)) for b in pg.np.linspace(0, 255, Ntick)]

        cmap_red = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_red)
        cmap_green = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_green)
        cmap_blue = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_blue)
        cmap_spread = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_spread)

        self.ui.histogram_red.gradient.setColorMap(cmap_red)
        self.ui.histogram_green.gradient.setColorMap(cmap_green)
        self.ui.histogram_blue.gradient.setColorMap(cmap_blue)
        self.ui.histogram_spread.gradient.setColorMap(cmap_spread)
        self.ui.histogram_red.setVisible(False)
        self.ui.histogram_green.setVisible(False)
        self.ui.histogram_blue.setVisible(False)
        self.ui.histogram_spread.setVisible(False)
        self.ui.Show_histogram.clicked.connect(self.show_hide_histogram)

    def setupIsoCurve(self):
        # TODO provide isocurve for the spread points
        # # Isocurve drawing
        self.ui.iso = pg.IsocurveItem(level=0.8, pen='g', axisOrder='row-major')
        self.ui.iso.setParentItem(self.ui.img_red)
        self.ui.iso.setZValue(5)
        # # Draggable line for setting isocurve level
        self.ui.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        self.ui.histogram_red.vb.addItem(self.ui.isoLine)
        self.ui.histogram_red.vb.setMouseEnabled(y=False)  # makes user interaction a little easier
        self.ui.isoLine.setValue(0.8)
        self.ui.isoLine.setZValue(1000)  # bring iso line above contrast controls
        self.ui.isocurve_pb.clicked.connect(self.show_hide_iso)
        self.ui.isocurve_pb.setChecked(False)
        self.show_hide_iso()
        # build isocurves from smoothed data
        self.ui.isoLine.sigDragged.connect(self.updateIsocurve)

    def setupCrosshair(self):
        # #crosshair
        self.ui.crosshair = Crosshair(self.image_widget.plotitem)
        self.ui.crosshair_H_blue = PlotCurveItem(pen='b')
        self.ui.crosshair_H_green = PlotCurveItem(pen="g")
        self.ui.crosshair_H_red = PlotCurveItem(pen="r")
        self.ui.crosshair_H_spread = PlotCurveItem(pen=(128, 128, 128))
        self.ui.crosshair_V_blue = PlotCurveItem(pen="b")
        self.ui.crosshair_V_green = PlotCurveItem(pen="g")
        self.ui.crosshair_V_red = PlotCurveItem(pen="r")
        self.ui.crosshair_V_spread = PlotCurveItem(pen=(128, 128, 128))

        self.ui.Lineout_H.plotItem.addItem(self.ui.crosshair_H_blue)
        self.ui.Lineout_H.plotItem.addItem(self.ui.crosshair_H_red)
        self.ui.Lineout_H.plotItem.addItem(self.ui.crosshair_H_green)
        self.ui.Lineout_H.plotItem.addItem(self.ui.crosshair_H_spread)

        self.ui.Lineout_V.plotItem.addItem(self.ui.crosshair_V_blue)
        self.ui.Lineout_V.plotItem.addItem(self.ui.crosshair_V_red)
        self.ui.Lineout_V.plotItem.addItem(self.ui.crosshair_V_green)
        self.ui.Lineout_V.plotItem.addItem(self.ui.crosshair_V_spread)

        self.ui.crosshair.crosshair_dragged.connect(self.update_crosshair_data)
        self.ui.crosshair_pb.clicked.connect(self.crosshairClicked)
        self.crosshairClicked()

    def setupROI(self):
        # # ROI stuff
        self.ui.RoiCurve_H = OrderedDict()
        self.ui.RoiCurve_V = OrderedDict()
        self.ui.RoiCurve_integrated = OrderedDict()
        self.data_integrated_plot = OrderedDict()
        self.ui.ROIs = OrderedDict([])
        self.ui.roiBtn.clicked.connect(self.roi_clicked)

        self.roi_manager = ROIManager(self.image_widget, '2D')
        self.roi_manager.new_ROI_signal.connect(self.add_ROI)
        self.roi_manager.remove_ROI_signal.connect(self.remove_ROI)
        self.roi_manager.roi_settings_changed.connect(self.update_roi)
        self.ui.splitter.addWidget(self.roi_manager.roiwidget)
        self.roi_manager.roiwidget.setVisible(False)

    def setupUI(self):

        self.ui = QObject()

        vertical_layout = QtWidgets.QVBoxLayout()
        self.parent.setLayout(vertical_layout)

        buttons_widget = QtWidgets.QWidget()
        buttons_widget.setMaximumHeight(80)
        self.ui.buttons_layout = QtWidgets.QHBoxLayout()
        buttons_widget.setLayout(self.ui.buttons_layout)
        self.setupButtons(self.ui.buttons_layout)
        vertical_layout.addWidget(buttons_widget)

        graphs_widget = QtWidgets.QWidget()
        graphs_layout = QtWidgets.QHBoxLayout()
        graphs_widget.setLayout(graphs_layout)
        self.setupGraphs(graphs_layout)
        vertical_layout.addWidget(graphs_widget)

        # selection area checkbox
        self.ui.blue_cb.setVisible(True)
        self.ui.blue_cb.setChecked(True)
        self.ui.blue_cb.clicked.connect(self.update_selection_area_visibility)
        self.ui.green_cb.setVisible(True)
        self.ui.green_cb.setChecked(True)
        self.ui.green_cb.clicked.connect(self.update_selection_area_visibility)
        self.ui.red_cb.setVisible(True)
        self.ui.red_cb.clicked.connect(self.update_selection_area_visibility)
        self.ui.red_cb.setChecked(True)
        self.ui.spread_cb.setVisible(True)
        self.ui.spread_cb.clicked.connect(self.update_selection_area_visibility)
        self.ui.spread_cb.setChecked(True)

        self.image_widget.plotitem.addItem(self.ui.img_red)
        self.image_widget.plotitem.addItem(self.ui.img_green)
        self.image_widget.plotitem.addItem(self.ui.img_blue)
        self.image_widget.plotitem.addItem(self.ui.img_spread)
        self.ui.graphicsView.setCentralItem(self.image_widget.plotitem)

        self.ui.aspect_ratio_pb.clicked.connect(self.lock_aspect_ratio)
        self.ui.aspect_ratio_pb.setChecked(True)

        # histograms
        histo_layout = QtWidgets.QHBoxLayout()
        self.setupHisto(histo_layout)

        # ROI selects an area and export its bounds as a signal
        self.ui.ROIselect = pg.RectROI([0, 0], [10, 10], centered=True, sideScalers=True)
        self.image_widget.plotitem.addItem(self.ui.ROIselect)
        self.ui.ROIselect.setVisible(False)
        self.ui.ROIselect.sigRegionChangeFinished.connect(self.selected_region_changed)
        self.ui.ROIselect_pb.clicked.connect(self.show_ROI_select)

        self.setupIsoCurve()

        self.setupCrosshair()

        # flipping

        self.ui.FlipUD_pb.clicked.connect(self.update_image)
        self.ui.FlipLR_pb.clicked.connect(self.update_image)
        self.ui.rotate_pb.clicked.connect(self.update_image)

        self.setupROI()

        self.ui.Ini_plot_pb.clicked.connect(self.ini_plot)

        # #splitter

        self.ui.splitter_VLeft.splitterMoved[int, int].connect(self.move_right_splitter)
        self.ui.splitter_VRight.splitterMoved[int, int].connect(self.move_left_splitter)

    @pyqtSlot(str)
    def remove_ROI(self, roi_name):
        item = self.ui.RoiCurve_H.pop(roi_name)
        self.ui.Lineout_H.plotItem.removeItem(item)

        item = self.ui.RoiCurve_V.pop(roi_name)
        self.ui.Lineout_V.plotItem.removeItem(item)

        item = self.ui.RoiCurve_integrated.pop(roi_name)
        self.ui.Lineout_integrated.plotItem.removeItem(item)

        self.roi_changed()

    @pyqtSlot(int, str)
    def add_ROI(self, newindex, roi_type):
        item = self.roi_manager.ROIs['ROI_{:02d}'.format(newindex)]
        item.sigRegionChanged.connect(self.roi_changed)
        item_param = self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(newindex))
        color = item_param.child(('Color')).value()
        self.ui.RoiCurve_H["ROI_%02.0d" % newindex] = PlotCurveItem(pen=color)
        self.ui.Lineout_H.plotItem.addItem(self.ui.RoiCurve_H["ROI_%02.0d" % newindex])

        self.ui.RoiCurve_V["ROI_%02.0d" % newindex] = PlotCurveItem(pen=color)
        self.ui.Lineout_V.plotItem.addItem(self.ui.RoiCurve_V["ROI_%02.0d" % newindex])

        self.ui.RoiCurve_integrated["ROI_%02.0d" % newindex] = PlotCurveItem(pen=color)
        self.ui.Lineout_integrated.plotItem.addItem(self.ui.RoiCurve_integrated["ROI_%02.0d" % newindex])

        self.data_integrated_plot["ROI_%02.0d" % newindex] = np.zeros((2, 1))

        if self.isdata['red']:
            item_param.child('use_channel').setValue('red')
        elif self.isdata['green']:
            item_param.child('use_channel').setValue('green')
        elif self.isdata['blue']:
            item_param.child('use_channel').setValue('blue')
        elif self.isdata['spread']:
            item_param.child('use_channel').setValue('spread')

        self.roi_changed()

    def crosshairChanged(self, posx=None, posy=None):
        if self.raw_data is None:
            return
        data_red, data_blue, data_green = self.set_image_transform()
        if posx is None or posy is None:
            (posx, posy) = self.ui.crosshair.get_positions()

        if self.isdata["red"]:
            indx, indy = self.mapfromview('red', posx, posy)
            x_axis_scaled, y_axis_scaled = \
                self.scale_axis(np.linspace(0, self.ui.img_red.width() - 1, self.ui.img_red.width()),
                                np.linspace(0, self.ui.img_red.height() - 1, self.ui.img_red.height()))
            data_H_indexes = slice(None, None, 1)
            data_V_indexes = slice(None, None, 1)
            H_indexes = (utils.rint(indy), data_H_indexes)
            V_indexes = (data_V_indexes, utils.rint(indx))

            if self.isdata["blue"]:
                self.ui.crosshair_H_blue.setData(y=data_blue.__getitem__(H_indexes), x=x_axis_scaled)
            if self.isdata["green"]:
                self.ui.crosshair_H_green.setData(y=data_green.__getitem__(H_indexes), x=x_axis_scaled)
            if self.isdata["red"]:
                self.ui.crosshair_H_red.setData(y=data_red.__getitem__(H_indexes), x=x_axis_scaled)

            if self.isdata["blue"]:
                self.ui.crosshair_V_blue.setData(y=y_axis_scaled, x=data_blue.__getitem__(V_indexes))
            if self.isdata["green"]:
                self.ui.crosshair_V_green.setData(y=y_axis_scaled, x=data_green.__getitem__(V_indexes))
            if self.isdata["red"]:
                self.ui.crosshair_V_red.setData(y=y_axis_scaled, x=data_red.__getitem__(V_indexes))

        if self.isdata["spread"]:
            data_H_indexes = slice(None, None, 1)
            data_V_indexes = slice(None, None, 1)

            posx_adpative, posy_adpative = self.mapfromview('spread', posx, posy)
            points, data = self.ui.img_spread.get_points_at(axis='y', val=posy_adpative)
            x_sorted_indexes = np.argsort(points[:, 0])
            x = points[x_sorted_indexes, 0][data_H_indexes]
            xscaled, yscaled = self.scale_axis(x, x)
            self.ui.crosshair_H_spread.setData(x=xscaled,
                                               y=data[x_sorted_indexes][data_H_indexes])
            points, data = self.ui.img_spread.get_points_at(axis='x', val=posx_adpative)
            y_sorted_indexes = np.argsort(points[:, 1])
            y = points[y_sorted_indexes, 1][data_V_indexes]
            xscaled, yscaled = self.scale_axis(y, y)
            self.ui.crosshair_V_spread.setData(y=yscaled,
                                               x=data[y_sorted_indexes][data_V_indexes])

    def crosshairClicked(self):
        if self.ui.crosshair_pb.isChecked():
            self.ui.crosshair.setVisible(True)
            self.ui.x_label.setVisible(True)
            self.ui.y_label.setVisible(True)
            range = self.image_widget.view.viewRange()
            self.ui.crosshair.set_crosshair_position(np.mean(np.array(range[0])), np.mean(np.array(range[0])))

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
            if self.isdata["spread"]:
                self.ui.z_label_spread.setVisible(True)
                self.ui.crosshair_H_spread.setVisible(True)
                self.ui.crosshair_V_spread.setVisible(True)

            self.update_crosshair_data(*self.ui.crosshair.get_positions())
            # #self.crosshairChanged()
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
            self.ui.z_label_spread.setVisible(False)
            self.ui.crosshair_H_spread.setVisible(False)
            self.ui.crosshair_V_spread.setVisible(False)
        QtWidgets.QApplication.processEvents()
        self.show_lineouts()
        # self.show_lineouts()

    @pyqtSlot(float, float)
    def double_clicked(self, posx, posy):
        self.ui.crosshair.set_crosshair_position(posx, posy)
        self.update_crosshair_data(posx, posy)
        self.sig_double_clicked.emit(posx, posy)

    def ini_plot(self):
        for k in self.data_integrated_plot.keys():
            self.data_integrated_plot[k] = np.zeros((2, 1))

    def lock_aspect_ratio(self):
        if self.ui.aspect_ratio_pb.isChecked():
            self.image_widget.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        else:
            self.image_widget.plotitem.vb.setAspectLocked(lock=False)

    @pyqtSlot(int, int)
    def move_left_splitter(self, pos, index):
        self.ui.splitter_VLeft.blockSignals(True)
        self.ui.splitter_VLeft.moveSplitter(pos, index)
        self.ui.splitter_VLeft.blockSignals(False)

    @pyqtSlot(int, int)
    def move_right_splitter(self, pos, index):
        self.ui.splitter_VRight.blockSignals(True)
        self.ui.splitter_VRight.moveSplitter(pos, index)
        self.ui.splitter_VRight.blockSignals(False)

    def restore_state(self, data_tree):
        self.roi_settings.restoreState(data_tree)
        QtWidgets.QApplication.processEvents()

        for param in self.roi_settings.child(('ROIs')):
            index = param.name()
            self.ui.ROIs[index].sigRegionChangeFinished.disconnect()
            self.update_roi(index, 'angle', param.child(('angle')).value())
            # self.update_roi(index,'Color',param.child(('Color')).value())
            self.update_roi(index, 'x', param.child(*('position', 'x')).value())
            self.update_roi(index, 'y', param.child(*('position', 'y')).value())
            self.update_roi(index, 'dx', param.child(*('size', 'dx')).value())
            self.update_roi(index, 'dy', param.child(*('size', 'dy')).value())
            self.ui.ROIs[index].sigRegionChangeFinished.connect(self.ui.ROIs[index].emit_index_signal)

    def roi_changed(self):
        try:
            if self.raw_data is None:
                return
            axes = (0, 1)
            self.data_to_export['data0D'] = OrderedDict([])
            self.data_to_export['data1D'] = OrderedDict([])
            self.measure_data_dict = OrderedDict([])
            for indROI, key in enumerate(self.roi_manager.ROIs):

                color_source = self.roi_manager.settings.child('ROIs', key,
                                                               'use_channel').value()

                if color_source == "red":
                    data_flag = self.ui.red_cb.isChecked()
                    img_source = self.ui.img_red
                elif color_source == "green":
                    data_flag = self.ui.green_cb.isChecked()
                    img_source = self.ui.img_green
                elif color_source == "blue":
                    data_flag = self.ui.blue_cb.isChecked()
                    img_source = self.ui.img_blue
                elif color_source == 'spread':
                    data_flag = self.ui.spread_cb.isChecked()
                    img_source = self.ui.img_spread
                else:
                    data_flag = None

                if data_flag is None:
                    return

                if color_source == "red" or color_source == "green" or color_source == "blue":
                    data, coords = self.roi_manager.ROIs[key].getArrayRegion(
                        self.transform_image(self.raw_data[color_source]),
                        img_source, axes, returnMappedCoords=True)
                    if data is not None:
                        xvals = np.linspace(np.min(np.min(coords[1, :, :])), np.max(np.max(coords[1, :, :])),
                                            data.shape[1])
                        yvals = np.linspace(np.min(np.min(coords[0, :, :])), np.max(np.max(coords[0, :, :])),
                                            data.shape[0])

                else:
                    roi = self.roi_manager.ROIs[key]
                    xvals = []
                    yvals = []
                    data = []
                    for ind in range(self.raw_data['spread'].shape[0]):
                        # invoke the QPainterpath of the ROI (from the shape method)
                        if roi.shape().contains(QPointF(self.raw_data['spread'][ind, 0] - roi.pos().x(),
                                                        self.raw_data['spread'][ind, 1] - roi.pos().y())):
                            xvals.append(self.raw_data['spread'][ind, 0])
                            yvals.append(self.raw_data['spread'][ind, 1])
                            data.append(self.raw_data['spread'][ind, 2])
                    if len(data) == 0:
                        data = None
                    else:
                        data = np.array(data)
                        xvals = np.array(xvals)
                        yvals = np.array(yvals)

                if data is not None:
                    x_axis, y_axis = self.scale_axis(xvals, yvals)

                    if color_source == "spread":
                        ind_xaxis = np.argsort(x_axis)
                        ind_yaxis = np.argsort(y_axis)
                        data_H_axis = x_axis[ind_xaxis]
                        data_V_axis = y_axis[ind_yaxis]
                        data_H = data[ind_xaxis]
                        data_V = data[ind_yaxis]
                    else:
                        data_H_axis = x_axis
                        data_V_axis = y_axis
                        data_H = np.mean(data, axis=0)
                        data_V = np.mean(data, axis=1)

                    self.data_integrated_plot[key] = np.append(self.data_integrated_plot[key], np.array(
                        [[self.data_integrated_plot[key][0, -1]], [0]]) + np.array([[1], [np.sum(data)]]), axis=1)

                    if self.data_integrated_plot[key].shape[1] > self.max_size_integrated:
                        self.data_integrated_plot[key] = \
                            self.data_integrated_plot[key][:, self.data_integrated_plot[key].shape[1] - 200:]

                    self.ui.RoiCurve_H[key].setData(y=data_H, x=data_H_axis)
                    self.ui.RoiCurve_V[key].setData(y=data_V_axis, x=data_V)

                    self.ui.RoiCurve_integrated[key].setData(y=self.data_integrated_plot[key][1, :],
                                                             x=self.data_integrated_plot[key][0, :])

                    self.data_to_export['data2D'][self.title + '_{:s}'.format(key)] = \
                        utils.DataToExport(name=self.title, data=data, source='roi',
                                           x_axis=utils.Axis(data=x_axis,
                                                             units=self.scaling_options['scaled_xaxis']['units'],
                                                             label=self.scaling_options['scaled_xaxis']['label']),
                                           y_axis=utils.Axis(data=y_axis,
                                                             units=self.scaling_options['scaled_yaxis']['units'],
                                                             label=self.scaling_options['scaled_yaxis']['label']))

                    self.data_to_export['data1D'][self.title + '_Hlineout_{:s}'.format(key)] = \
                        utils.DataToExport(name=self.title, data=data_H, source='roi',
                                           x_axis=utils.Axis(data=data_H_axis,
                                                             units=self.scaling_options['scaled_xaxis']['units'],
                                                             label=self.scaling_options['scaled_xaxis']['label']))
                    self.data_to_export['data1D'][self.title + '_Vlineout_{:s}'.format(key)] = \
                        utils.DataToExport(name=self.title, data=data_V, source='roi',
                                           x_axis=utils.Axis(data=data_V_axis,
                                                             units=self.scaling_options['scaled_yaxis']['units'],
                                                             label=self.scaling_options['scaled_yaxis']['label']))

                    self.data_to_export['data0D'][self.title + '_Integrated_{:s}'.format(key)] = \
                        utils.DataToExport(name=self.title, data=np.sum(data), source='roi', )

                    self.measure_data_dict["Lineout {:s}:".format(key)] = np.sum(data)

            self.roi_manager.settings.child(('measurements')).setValue(self.measure_data_dict)

            self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
            self.data_to_export_signal.emit(self.data_to_export)
            self.ROI_changed.emit()
        except Exception as e:
            pass

    @pyqtSlot(list)
    def update_roi(self, changes):
        for param, change, param_value in changes:
            if change == 'value':
                if param.name() == 'Color':
                    key = param.parent().name()
                    self.ui.RoiCurve_H[key].setPen(param_value)
                    self.ui.RoiCurve_V[key].setPen(param_value)
                    self.ui.RoiCurve_integrated[key].setPen(param_value)

            elif change == 'childAdded':
                pass
            elif change == 'parent':
                key = param.name()
                self.ui.Lineout_H.removeItem(self.ui.RoiCurve_H.pop(key))
                self.ui.Lineout_V.removeItem(self.ui.RoiCurve_V.pop(key))
                self.ui.Lineout_integrated.removeItem(self.ui.RoiCurve_integrated.pop(key))

        self.roi_changed()

    def roi_clicked(self):
        roistate = self.ui.roiBtn.isChecked()

        self.roi_manager.roiwidget.setVisible(roistate)
        for k, roi in self.roi_manager.ROIs.items():
            roi.setVisible(roistate)
            self.ui.RoiCurve_H[k].setVisible(roistate)
            self.ui.RoiCurve_V[k].setVisible(roistate)
            self.ui.RoiCurve_integrated[k].setVisible(roistate)

        if self.ui.roiBtn.isChecked():
            self.roi_changed()

        self.show_lineouts()

        # if len(self.ui.ROIs) == 0 and roistate:
        #     self.roi_manager.settings.child(("ROIs")).addNew('RectROI')

    def scale_axis(self, xaxis_pxl, yaxis_pxl):
        return xaxis_pxl * self.scaling_options['scaled_xaxis']['scaling'] + self.scaling_options['scaled_xaxis'][
            'offset'], yaxis_pxl * self.scaling_options['scaled_yaxis']['scaling'] + \
            self.scaling_options['scaled_yaxis']['offset']

    def unscale_axis(self, xaxis, yaxis):
        return (xaxis - self.scaling_options['scaled_xaxis']['offset']) / self.scaling_options['scaled_xaxis'][
            'scaling'], (yaxis - self.scaling_options['scaled_yaxis']['offset']) / \
            self.scaling_options['scaled_yaxis']['scaling']

    def selected_region_changed(self):
        if self.ui.ROIselect_pb.isChecked():
            pos = self.ui.ROIselect.pos()
            size = self.ui.ROIselect.size()
            self.ROI_select_signal.emit(QRectF(pos[0], pos[1], size[0], size[1]))

    def set_autolevels(self):
        self.autolevels = self.ui.auto_levels_pb.isChecked()
        if not self.ui.auto_levels_pb.isChecked():
            self.ui.histogram_red.regionChanged()
            self.ui.histogram_green.regionChanged()
            self.ui.histogram_blue.regionChanged()

        self.ui.histogram_red.region.setVisible(not self.autolevels)
        self.ui.histogram_green.region.setVisible(not self.autolevels)
        self.ui.histogram_blue.region.setVisible(not self.autolevels)

    def set_scaling_axes(self, scaling_options=None):
        """
        metod used to update the scaling of the right and top axes in order to translate pixels to real coordinates
        scaling_options=dict(scaled_xaxis=dict(label="",units=None,offset=0,scaling=1),scaled_yaxis=dict(label="",units=None,offset=0,scaling=1))
        """
        if scaling_options is not None:
            self.scaling_options = copy.deepcopy(scaling_options)
        self.scaled_xaxis.scaling = self.scaling_options['scaled_xaxis']['scaling']
        self.scaled_xaxis.offset = self.scaling_options['scaled_xaxis']['offset']
        self.scaled_xaxis.setLabel(text=self.scaling_options['scaled_xaxis']['label'],
                                   units=self.scaling_options['scaled_xaxis']['units'])
        self.scaled_yaxis.scaling = self.scaling_options['scaled_yaxis']['scaling']
        self.scaled_yaxis.offset = self.scaling_options['scaled_yaxis']['offset']
        self.scaled_yaxis.setLabel(text=self.scaling_options['scaled_yaxis']['label'],
                                   units=self.scaling_options['scaled_yaxis']['units'])

        self.scaled_xaxis.linkedViewChanged(self.image_widget.view)
        self.scaled_yaxis.linkedViewChanged(self.image_widget.view)

    def transform_image(self, data):
        if data is not None:
            if len(data.shape) > 2:
                data = np.mean(data, axis=0)
            if self.ui.FlipUD_pb.isChecked():
                data = np.flipud(data)
            if self.ui.FlipLR_pb.isChecked():
                data = np.fliplr(data)
            if self.ui.rotate_pb.isChecked():
                data = np.flipud(np.transpose(data))
        if data is not None:
            return data.copy()
        else:
            return None

    def set_image_transform(self):
        # deactiviate fliping and rotation as non sense for points defined data
        status = self.isdata["red"] is False and self.isdata["blue"] is False
        status = status and self.isdata["green"] is False and self.isdata["spread"] is True
        status = not status

        self.ui.FlipUD_pb.setVisible(status)
        self.ui.FlipLR_pb.setVisible(status)
        self.ui.rotate_pb.setVisible(status)
        data_red, data_blue, data_green = None, None, None
        if self.isdata["red"]:
            data_red = self.transform_image(self.raw_data['red'])
        if self.isdata["blue"]:
            data_blue = self.transform_image(self.raw_data['blue'])
        if self.isdata["green"]:
            data_green = self.transform_image(self.raw_data['green'])
        return data_red, data_blue, data_green

    def set_visible_items(self):

        if self.ui.red_cb.isChecked() and self.isdata["red"] is False:  # turn it off if it was on but there is no data
            self.ui.red_cb.setChecked(False)
            self.ui.red_cb.parent().setVisible(False)

        elif self.isdata["red"]:
            self.ui.red_cb.setChecked(True)
            self.ui.red_cb.parent().setVisible(True)
        self.ui.img_red.setVisible(self.ui.red_cb.isChecked())
        if self.ui.Show_histogram.isChecked():
            self.ui.histogram_red.setVisible(self.ui.red_cb.isChecked())

        if self.ui.green_cb.isChecked() and self.isdata["green"] is False:
            # turn it off if it was on but there is no data
            self.ui.green_cb.setChecked(False)
            self.ui.green_cb.parent().setVisible(False)
        elif self.isdata["green"]:
            self.ui.green_cb.setChecked(True)
            self.ui.green_cb.parent().setVisible(True)
        self.ui.img_green.setVisible(self.ui.green_cb.isChecked())
        if self.ui.Show_histogram.isChecked():
            self.ui.histogram_green.setVisible(self.ui.green_cb.isChecked())

        if self.ui.blue_cb.isChecked() and self.isdata["blue"] is False:
            # turn it off if it was on but there is no data
            self.ui.blue_cb.setChecked(False)
            self.ui.blue_cb.parent().setVisible(False)
        elif self.isdata["blue"]:
            self.ui.blue_cb.setChecked(True)
            self.ui.blue_cb.parent().setVisible(True)
        self.ui.img_blue.setVisible(self.ui.blue_cb.isChecked())
        if self.ui.Show_histogram.isChecked():
            self.ui.histogram_blue.setVisible(self.ui.blue_cb.isChecked())

        if self.ui.spread_cb.isChecked() and self.isdata["spread"] is False:
            # turn it off if it was on but there is no data
            self.ui.spread_cb.setChecked(False)
            self.ui.spread_cb.parent().setVisible(False)
        elif self.isdata["spread"]:
            self.ui.spread_cb.setChecked(True)
            self.ui.spread_cb.parent().setVisible(True)
        self.ui.img_spread.setVisible(self.ui.spread_cb.isChecked())
        if self.ui.Show_histogram.isChecked():
            self.ui.histogram_spread.setVisible(self.ui.spread_cb.isChecked())

    def setImage(self, data_red=None, data_green=None, data_blue=None, data_spread=None):
        try:
            self.raw_data = dict(blue=data_blue, green=data_green, red=data_red, spread=data_spread)

            red_flag = data_red is not None
            self.isdata["red"] = red_flag
            green_flag = data_green is not None
            self.isdata["green"] = green_flag
            blue_flag = data_blue is not None
            self.isdata["blue"] = blue_flag
            spread_flag = data_spread is not None
            self.isdata["spread"] = spread_flag

            data_red, data_blue, data_green = self.set_image_transform()
            self.set_visible_items()

            self.data_to_export = OrderedDict(name=self.title, data0D=OrderedDict(), data1D=OrderedDict(),
                                              data2D=OrderedDict())

            if data_red is not None:  # if only one data only the red canal should be set otherwise this would fail
                self._x_axis = np.linspace(0, data_red.shape[1] - 1, data_red.shape[1])
                self._y_axis = np.linspace(0, data_red.shape[0] - 1, data_red.shape[0])
                self.x_axis_scaled, self.y_axis_scaled = self.scale_axis(self._x_axis, self._y_axis)

            ind = 0
            if red_flag:
                self.ui.img_red.setImage(data_red, autoLevels=self.autolevels)
                self.data_to_export['data2D']['CH{:03d}'.format(ind)] = \
                    utils.DataToExport(data=data_red, source='raw',
                                       x_axis=utils.Axis(data=self.x_axis_scaled,
                                                         units=self.scaling_options['scaled_xaxis']['units'],
                                                         label=self.scaling_options['scaled_xaxis']['label']),
                                       y_axis=utils.Axis(data=self.y_axis_scaled,
                                                         units=self.scaling_options['scaled_yaxis']['units'],
                                                         label=self.scaling_options['scaled_yaxis']['label']))
                ind += 1

            if green_flag:
                self.ui.img_green.setImage(data_green, autoLevels=self.autolevels)
                self.data_to_export['data2D']['CH{:03d}'.format(ind)] = \
                    utils.DataToExport(data=data_green, source='raw',
                                       x_axis=utils.Axis(data=self.x_axis_scaled,
                                                         units=self.scaling_options['scaled_xaxis']['units'],
                                                         label=self.scaling_options['scaled_xaxis']['label']),
                                       y_axis=utils.Axis(data=self.y_axis_scaled,
                                                         units=self.scaling_options['scaled_yaxis']['units'],
                                                         label=self.scaling_options['scaled_yaxis']['label']))
                ind += 1

            if blue_flag:
                self.ui.img_blue.setImage(data_blue, autoLevels=self.autolevels)
                self.data_to_export['data2D']['CH{:03d}'.format(ind)] = \
                    utils.DataToExport(data=data_blue, source='raw',
                                       x_axis=utils.Axis(data=self.x_axis_scaled,
                                                         units=self.scaling_options['scaled_xaxis']['units'],
                                                         label=self.scaling_options['scaled_xaxis']['label']),
                                       y_axis=utils.Axis(data=self.y_axis_scaled,
                                                         units=self.scaling_options['scaled_yaxis']['units'],
                                                         label=self.scaling_options['scaled_yaxis']['label']))
                ind += 1
            if spread_flag:
                self.ui.img_spread.setImage(self.raw_data['spread'], autoLevels=self.autolevels)
                self.data_to_export['data2D']['CH{:03d}'.format(ind)] = \
                    utils.DataToExport(data=data_spread[:, 2], source='raw',
                                       x_axis=utils.Axis(data=data_spread[:, 0],
                                                         units=self.scaling_options['scaled_xaxis']['units'],
                                                         label=self.scaling_options['scaled_xaxis']['label']),
                                       y_axis=utils.Axis(data=data_spread[:, 1],
                                                         units=self.scaling_options['scaled_yaxis']['units'],
                                                         label=self.scaling_options['scaled_yaxis']['label']))
                ind += 1

            if self.ui.roiBtn.isChecked():
                self.roi_changed()
            else:
                self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
                self.data_to_export_signal.emit(self.data_to_export)

            if self.ui.isocurve_pb.isChecked() and red_flag:
                self.ui.iso.setData(pg.gaussianFilter(data_red, (2, 2)))

            if self.ui.crosshair_pb.isChecked():
                self.crosshairChanged()

        except Exception as e:
            print(e)

    def setImageTemp(self, data_red=None, data_green=None, data_blue=None, data_spread=None):
        """
        to plot temporary data, for instance when all pixels are not yet populated...
        """

        self.raw_data = dict(blue=data_blue, green=data_green, red=data_red, spread=data_spread)
        red_flag = data_red is not None
        self.isdata["red"] = red_flag
        green_flag = data_green is not None
        self.isdata["green"] = green_flag
        blue_flag = data_blue is not None
        self.isdata["blue"] = blue_flag
        spread_flag = data_spread is not None
        self.isdata["spread"] = spread_flag

        data_red, data_blue, data_green = self.set_image_transform()
        self.set_visible_items()

        if data_red is not None:
            self.ui.img_red.setImage(data_red, autoLevels=self.autolevels)
        if data_green is not None:
            self.ui.img_green.setImage(data_green, autoLevels=self.autolevels)
        if data_blue is not None:
            self.ui.img_blue.setImage(data_blue, autoLevels=self.autolevels)
        if data_spread is not None:
            self.ui.img_spread.setImage(self.raw_data['spread'], autoLevels=self.autolevels)

    def mapfromview(self, graphitem, x, y):
        """
        get item coordinates from view coordinates
        Parameters
        ----------
        graphitem: (str or GraphItem) either 'red', 'blue', 'green' or 'spread' referring to their corresponding
            graphitem (self.ui.img_red)...
        x: (float) x oordinate in the view reference frame
        y: (float) y coordinate in the view refernece frame

        Returns
        -------
        x: (float) coordinate in the item reference frame
        y: (float) coordinate in the item reference frame
        """
        if isinstance(graphitem, str):
            if graphitem not in ('red', 'blue', 'green', 'spread'):
                return None
            graphitem = getattr(self.ui, f'img_{graphitem}')
        point = graphitem.mapFromView(QtCore.QPointF(x, y))
        return point.x(), point.y()

    def setObjectName(self, txt):
        self.parent.setObjectName(txt)

    def show_hide_histogram(self):
        if self.isdata["blue"] and self.ui.blue_cb.isChecked():
            self.ui.histogram_blue.setVisible(self.ui.Show_histogram.isChecked())
            self.ui.histogram_blue.setLevels(self.raw_data['blue'].min(), self.raw_data['blue'].max())
        if self.isdata["green"] and self.ui.green_cb.isChecked():
            self.ui.histogram_green.setVisible(self.ui.Show_histogram.isChecked())
            self.ui.histogram_green.setLevels(self.raw_data['green'].min(), self.raw_data['green'].max())
        if self.isdata["red"] and self.ui.red_cb.isChecked():
            self.ui.histogram_red.setVisible(self.ui.Show_histogram.isChecked())
            self.ui.histogram_red.setLevels(self.raw_data['red'].min(), self.raw_data['red'].max())
        if self.isdata["spread"] and self.ui.spread_cb.isChecked():
            self.ui.histogram_spread.setVisible(self.ui.Show_histogram.isChecked())
            self.ui.histogram_spread.setLevels(self.raw_data['spread'].min(), self.raw_data['spread'].max())
        QtWidgets.QApplication.processEvents()

    def show_hide_iso(self):
        if self.ui.isocurve_pb.isChecked():
            self.ui.iso.show()
            self.ui.isoLine.show()
            self.ui.Show_histogram.setChecked(True)
            self.show_hide_histogram()
            if self.ui.isocurve_pb.isChecked() and self.raw_data['red'] is not None:
                self.ui.iso.setData(pg.gaussianFilter(self.raw_data['red'], (2, 2)))
        else:
            self.ui.iso.hide()
            self.ui.isoLine.hide()

    def show_lineouts(self):
        state = self.ui.roiBtn.isChecked() or self.ui.crosshair_pb.isChecked()
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
        self.ui.splitter_VRight.splitterMoved[int, int].emit(0.6 * self.parent.height(), 1)
        self.ui.splitter.moveSplitter(0.6 * self.parent.width(), 1)
        self.ui.splitter_VLeft.moveSplitter(0.6 * self.parent.height(), 1)
        self.ui.splitter_VLeft.splitterMoved[int, int].emit(0.6 * self.parent.height(), 1)
        QtGui.QGuiApplication.processEvents()

    def show_ROI_select(self):
        self.ui.ROIselect.setVisible(self.ui.ROIselect_pb.isChecked())

    def update_image(self):
        self.setImageTemp(data_red=self.raw_data['red'], data_green=self.raw_data['green'],
                          data_blue=self.raw_data['blue'], data_spread=self.raw_data['spread'])

    # def update_image_flipud(self):
    #     self.ui.img_red.setOpts(flipud=self.ui.FlipUD_pb.isChecked())
    #     self.ui.img_green.setOpts(flipud=self.ui.FlipUD_pb.isChecked())
    #     self.ui.img_blue.setOpts(flipud=self.ui.FlipUD_pb.isChecked())
    #     self.ui.img_spread.setOpts(flipud=self.ui.FlipUD_pb.isChecked())
    #
    #     self.ui.crosshair_V_spread.setOpts(flipud=self.ui.FlipUD_pb.isChecked())
    #
    # def update_image_fliplr(self):
    #     self.ui.img_red.setOpts(fliplr=self.ui.FlipLR_pb.isChecked())
    #     self.ui.img_green.setOpts(fliplr=self.ui.FlipLR_pb.isChecked())
    #     self.ui.img_blue.setOpts(fliplr=self.ui.FlipLR_pb.isChecked())
    #     self.ui.img_spread.setOpts(fliplr=self.ui.FlipLR_pb.isChecked())
    #
    #     self.ui.crosshair_H_spread.setOpts(fliplr=self.ui.FlipLR_pb.isChecked())
    #
    # def update_image_rotate(self):
    #     self.ui.img_red.setOpts(rotate90=self.ui.rotate_pb.isChecked())
    #     self.ui.img_green.setOpts(rotate90=self.ui.rotate_pb.isChecked())
    #     self.ui.img_blue.setOpts(rotate90=self.ui.rotate_pb.isChecked())
    #     self.ui.img_spread.setOpts(rotate90=self.ui.rotate_pb.isChecked())
    #     self.ui.crosshair_V_spread.setOpts(flipudbis=self.ui.rotate_pb.isChecked())

    def update_selection_area_visibility(self):
        bluestate = self.ui.blue_cb.isChecked()
        self.ui.img_blue.setVisible(bluestate)
        # self.ui.histogram_blue.setVisible(bluestate)

        greenstate = self.ui.green_cb.isChecked()
        self.ui.img_green.setVisible(greenstate)
        # self.ui.histogram_green.setVisible(greenstate)

        redstate = self.ui.red_cb.isChecked()
        self.ui.img_red.setVisible(redstate)
        # self.ui.histogram_red.setVisible(redstate)

    def update_crosshair_data(self, posx, posy, name=""):
        try:
            (posx_scaled, posy_scaled) = self.scale_axis(posx, posy)
            self.crosshair_dragged.emit(posx_scaled, posy_scaled)

            # if self._x_axis is not None:
            #     x_axis_scaled, y_axis_scaled = self.scale_axis(self._x_axis, self._y_axis)
            #     indx = utils.find_index(self._x_axis, posx)[0][0]
            #     indy = utils.find_index(self._y_axis, posy)[0][0]
            # else: #case of spread data only
            #     indx, indy = (posx_scaled, posy_scaled)

            self.crosshairChanged(posx, posy)

            if self.isdata["blue"]:
                indx, indy = self.mapfromview('blue', posx, posy)
                z_blue = self.transform_image(self.raw_data["blue"])[utils.rint(indy), utils.rint(indx)]
                self.ui.z_label_blue.setText("{:.3e}".format(z_blue))
            if self.isdata["green"]:
                indx, indy = self.mapfromview('green', posx, posy)
                z_green = self.transform_image(self.raw_data["green"])[utils.rint(indy), utils.rint(indx)]
                self.ui.z_label_green.setText("{:.3e}".format(z_green))
            if self.isdata["red"]:
                indx, indy = self.mapfromview('red', posx, posy)
                z_red = self.transform_image(self.raw_data["red"])[utils.rint(indy), utils.rint(indx)]
                self.ui.z_label_red.setText("{:.3e}".format(z_red))
            if self.isdata["spread"]:
                z_spread = self.ui.img_spread.get_val_at(self.mapfromview('spread', posx, posy))
                self.ui.z_label_spread.setText("{:.3e}".format(z_spread))

            self.ui.x_label.setText("x={:.3e} ".format(posx_scaled))
            self.ui.y_label.setText("y={:.3e} ".format(posy_scaled))

        except Exception as e:
            print(e)

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
                xdata = x_axis['data']
            if 'label' in x_axis:
                label = x_axis['label']
            if 'units' in x_axis:
                units = x_axis['units']
        else:
            xdata = x_axis

        if len(xdata) > 1:
            x_scaling = xdata[1] - xdata[0]
            x_offset = np.min(xdata)
        else:
            x_scaling = 1.
            x_offset = 0.
        self.scaling_options['scaled_xaxis'].update(dict(offset=x_offset, scaling=x_scaling, label=label, units=units))
        self.set_scaling_axes(self.scaling_options)

    def set_axis_label(self, axis_settings=dict(orientation='bottom', label='x axis', units='pxls')):
        if axis_settings['orientation'] == 'bottom':
            axis = 'scaled_xaxis'
        else:
            axis = 'scaled_yaxis'
        self.scaling_options[axis].update(axis_settings)
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
                ydata = y_axis['data']
            if 'label' in y_axis:
                label = y_axis['label']
            if 'units' in y_axis:
                units = y_axis['units']
        else:
            ydata = y_axis

        if len(ydata) > 1:
            y_scaling = ydata[1] - ydata[0]
            y_offset = np.min(ydata)
        else:
            y_scaling = 1.
            y_offset = 0.
        self.scaling_options['scaled_yaxis'].update(dict(offset=y_offset, scaling=y_scaling, label=label, units=units))
        self.set_scaling_axes(self.scaling_options)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Form = DockArea()
    Form = QtWidgets.QWidget()

    Nx = 100
    Ny = 200
    data_random = pg.np.random.normal(size=(Ny, Nx))
    x = pg.np.linspace(0, Nx - 1, Nx)
    y = pg.np.linspace(0, Ny - 1, Ny)
    from pymodaq.daq_utils.daq_utils import gauss2D

    data_red = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 90)
    # data_red = pg.gaussianFilter(data_red, (2, 2))
    data_green = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 0)
    # data_green = pg.gaussianFilter(data_green, (2, 2))
    data_blue = data_random + 3 * gauss2D(x, 0.7 * Nx, Nx / 5, y, 0.2 * Ny, Ny / 5, 1)
    data_blue = pg.gaussianFilter(data_blue, (2, 2))

    prog = Viewer2D(Form)
    prog.set_scaling_axes(scaling_options=utils.ScalingOptions(
        scaled_xaxis=utils.ScaledAxis(label="eV", units=None, offset=100, scaling=0.1),
        scaled_yaxis=utils.ScaledAxis(label="time", units='s', offset=-20, scaling=2)))
    Form.show()
    # data = np.load('triangulation_data.npy')
    prog.setImage(data_red=data_red, data_blue=data_blue, )
    # prog.setImage(data_spread=data)
    app.processEvents()

    sys.exit(app.exec_())
