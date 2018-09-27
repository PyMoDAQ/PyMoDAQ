from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, Qt, QLocale
from PyQt5.QtGui import QImage, QPixmap, QIcon
from collections import OrderedDict
import sys
from PyMoDAQ.DAQ_Navigation_Visu.GUI.DAQ_Navigation_Visu_GUI import Ui_MainWindow
from PyMoDAQ.DAQ_Utils.plotting.trace1D_selection import Trace1D_selection
import python_lib as mylib
from PyMoDAQ.DAQ_Utils.plotting.image_view_multicolor import Image_View_Multicolor
from nptdms import TdmsFile
from python_lib.utils.file_management import TdmsWriter_custom
#import DAQ_Navigation_Visu_Support as DAQ_Support
import os
import pyqtgraph as pg
import numpy as np
import re
from scipy.optimize import curve_fit
from matplotlib.figure import Figure , SubplotParams
import matplotlib.cm as cm
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar) 
#import pickle
import QtDesigner_ressources_rc
from PyMoDAQ.DAQ_Utils.DAQ_enums import Measurement_type


class DAQ_Navigation_Visu(Ui_MainWindow,QObject):
    start_process=pyqtSignal()
    def __init__(self, MainWindow):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_Navigation_Visu,self).__init__()
        #load GUI interface
        self.ui=Ui_MainWindow()
        self.ui.setupUi(MainWindow)
        #self.setupUi(MainWindow)
        self.ui.MainWindow=MainWindow
        self.wait_time=2000 #time in ms for the status bar to show information

        #add a label and a progressbar to the status bar
        self.ui.status_label=QtWidgets.QLabel(MainWindow)
        self.ui.status_progressbar=QProgressBar(MainWindow)
        self.ui.statusbar.addWidget(self.ui.status_label)
        self.ui.statusbar.addWidget(self.ui.status_progressbar,1)
        self.ui.status_label.setVisible(False)
        self.ui.status_progressbar.setVisible(False)
        self.ui.status_progressbar.setMinimum(0)
        self.ui.status_progressbar.setMaximum(100)
        form=QtWidgets.QWidget()
        self.ui.Data2D_graph=Image_View_Multicolor(form)
        
        self.start_path=None

        self.ui.verticalLayout_4.addWidget(form)
        #set initial parameters
        self.parameters=DAQ_Navigation_Visu_struct()
        self.data_struct=DAQ_Navigation_Visu_Data()
        self.data_process=DAQ_Navigation_Visu_process()
        

        self.ui.colors_combo.addItem(QIcon(QtGui.QPixmap(":/Labview_icons/Icon_Library/b_icon.png")),'B')
        self.ui.colors_combo.addItem(QIcon(QtGui.QPixmap(":/Labview_icons/Icon_Library/bg_icon.png")),'BG')
        self.ui.colors_combo.addItem(QIcon(QtGui.QPixmap(":/Labview_icons/Icon_Library/rgb_icon.png")),'RGB')

        self.measurement_types=Measurement_type.names(Measurement_type)
        self.ui.measure_type_combo.clear()
        self.ui.measure_type_combo.addItems(self.measurement_types)
        
              
        self.ui.table_properties.setColumnCount(2)
        self.ui.table_properties.setHorizontalHeaderLabels(["property name","Property value"])
        self.ui.table_properties.horizontalHeader().setSectionResizeMode(self.ui.table_properties.horizontalHeader().ResizeToContents)

        self.ui.plot_1D=self.ui.Data1D_graph.plotItem
        self.ui.plot_1D.enableAutoRange('xy', True)

        #self.ui.reshape_types.clear()
        #self.ui.reshape_types.addItems(self.data_struct.reshape_types)
        #self.ui.reshape_types.setCurrentIndex(3)
        #self.ui.reshape_types.setEnabled(False)

        #MainWindow.setMinimumWidth(1200)
        self.ui.selected_region_red=pg.LinearRegionItem([400,450])
        self.ui.selected_region_red.setZValue(-10)
        self.ui.selected_region_red.setBrush('r')
        self.ui.selected_region_red.setOpacity(0.2)
        self.ui.selected_region_red.setVisible(False)

        self.ui.selected_region_green=pg.LinearRegionItem([500,550])
        self.ui.selected_region_green.setZValue(-10)
        self.ui.selected_region_green.setBrush('g')
        self.ui.selected_region_green.setOpacity(0.2)
        self.ui.selected_region_red.setVisible(False)

        self.ui.selected_region_blue=pg.LinearRegionItem([600,650])
        self.ui.selected_region_blue.setZValue(-10)
        self.ui.selected_region_blue.setBrush('b')
        self.ui.selected_region_blue.setOpacity(0.2)


        self.ui.Data1D_graph.addItem(self.ui.selected_region_red)
        self.ui.Data1D_graph.addItem(self.ui.selected_region_green)
        self.ui.Data1D_graph.addItem(self.ui.selected_region_blue)

        self.ui.splitter_7.setSizes([400, 10])
        self.ui.splitter_4.setSizes([300, 300])
        self.ui.splitter_5.setSizes([400, 200])

        self.ui.curve_1D=self.ui.plot_1D.plot(pen='w')
        self.ui.curve_1D_fit=self.ui.plot_1D.plot(pen='y')
        self.ui.curve_1D_despiked=self.ui.plot_1D.plot(pen='r')

        #
        self.ui.cmap_combo.addItems(list(cm.cmap_d.keys()))
        #cmaps=list(cm.cmap_d.keys())
        #cmaps.sort(key=str.lower)
        #for map_name in cmaps:
        #    icon=QIcon(self.map_to_pixmap(cm.cmap_d[map_name]))
        #    self.ui.cmap_combo.addItem(icon,map_name)


        Form = QtWidgets.QWidget()
        self.ui.converter = mylib.Units_converter(Form)
        self.ui.toolBox.addItem(Form,"Units converter")

        #☻self.ui.MainWindow.tabifyDockWidget(self.ui.dockWidget_plotting,self.ui.dockWidget_Main)
        self.ui.figure = Figure()
        
        self.ui.canvas = FigureCanvas(self.ui.figure)
        self.ui.toolbar = NavigationToolbar(self.ui.canvas,self.ui.tabWidget_2, coordinates=True)
        self.ui.plotting_layout.addWidget(self.ui.toolbar)
        self.ui.plotting_layout.addWidget(self.ui.canvas)
        self.ui.canvas.draw()


        #process the menu actions
        
        self.ui.actionLabspec.triggered.connect(lambda: self.update_status("Loading Labspec files"))
        self.ui.actionLabspec.triggered.connect(lambda: self.LoadCartographyLabspec_fun(new_tdms=True))
        self.ui.actionLabspec_add.triggered.connect(lambda: self.update_status("Loading Labspec files"))
        self.ui.actionLabspec_add.triggered.connect(lambda: self.LoadCartographyLabspec_fun(new_tdms=False))
        
        self.ui.actionLabspec_Dual_Mode.triggered.connect(lambda: self.update_status("Loading Labspec files"))
        self.ui.actionLabspec_Dual_Mode.triggered.connect(lambda: self.LoadCartographyLabspec_fun(new_tdms=True,dual=True))
        self.ui.actionLabspec_Dual_Mode_add.triggered.connect(lambda: self.update_status("Loading Labspec files"))
        self.ui.actionLabspec_Dual_Mode_add.triggered.connect(lambda: self.LoadCartographyLabspec_fun(new_tdms=False,dual=True))
        
        self.ui.actionAFM.triggered.connect(lambda: self.update_status("Loading AFM files"))
        self.ui.actionAFM.triggered.connect(lambda: self.LoadCartographyAFM_fun(new_tdms=True))
        self.ui.actionAFM_add.triggered.connect(lambda: self.update_status("Loading AFM files"))
        self.ui.actionAFM_add.triggered.connect(lambda: self.LoadCartographyAFM_fun(new_tdms=False))
        
        self.ui.actionLabview.triggered.connect(lambda: self.update_status("Loading Labview scan files"))
        self.ui.actionLabview.triggered.connect(lambda: self.LoadCartography_Separated_Files_fun(labview=True,new_tdms=True))
        self.ui.actionLabview_add.triggered.connect(lambda: self.update_status("Loading Labview scan files"))
        self.ui.actionLabview_add.triggered.connect(lambda: self.LoadCartography_Separated_Files_fun(labview=True,new_tdms=False))        
        
        self.ui.actionSeparated_Files.triggered.connect(lambda: self.update_status("Loading Separated Files"))
        self.ui.actionSeparated_Files.triggered.connect(lambda: self.LoadCartography_Separated_Files_fun(labview=False,new_tdms=True))
        self.ui.actionSeparated_Files_add.triggered.connect(lambda: self.update_status("Loading Separated Files"))
        self.ui.actionSeparated_Files_add.triggered.connect(lambda: self.LoadCartography_Separated_Files_fun(labview=False,new_tdms=False))

        self.ui.actionLoad_TDMS.triggered.connect(lambda: self.update_status("Loading TDMS file"))
        self.ui.actionLoad_TDMS.triggered.connect(self.Load_TDMS_fun)
        
        self.ui.actionLoad_1D_Trace.triggered.connect(self.load_1D_dialog)
        self.ui.actionQuit.triggered.connect(self.Quit_fun)
        self.ui.actionDelete_Tree_Element.triggered.connect(self.delete_tdms_data)
        self.ui.action2D_image_as_txt.triggered.connect(self.export_data2D_fun)

        #process the signal/slot connections
        self.ui.merge_spectra_cb.clicked.connect(self.show_ROI_for_average)
        self.ui.merge_spectra_cb.clicked.connect(self.set_roi_connect)
        self.ui.colors_combo.currentTextChanged.connect(self.update_color_regions)
        self.update_color_regions("B")
        #self.load_1D_pb.clicked.connect(self.load_1D_dialog)
        self.ui.cmap_combo.currentTextChanged[str].connect(self.update_cmap)
        self.ui.plot_2D_pb.clicked.connect(lambda: self.update_matplotlib(type="2D",update=False))
        self.ui.plot_1D_pb.clicked.connect(lambda: self.update_matplotlib(type="1D",update=False))
        self.ui.update_plot_pb.clicked.connect(lambda: self.update_matplotlib(update=True))
        self.ui.save_plotting_pb.clicked.connect(self.save_plotting_fun)

        self.ui.set_as_bkg_pb.clicked.connect(self.set_current_as_bkg)
        self.ui.apply_bkg_check.clicked.connect(self.update_plots)
        self.ui.apply_bkg_check.clicked.connect(self.update_measurement)
        self.ui.do_zero_cb.clicked.connect(self.update_plots)
        self.ui.do_zero_cb.clicked.connect(self.update_measurement)
        self.ui.bkg_type.currentTextChanged.connect(self.update_measurement)
        self.ui.bkg_type.currentTextChanged.connect(self.update_plots)
        
        
        self.ui.Data2D_graph.ui.crosshair.crosshair_dragged[float,float].connect(self.find_item_from_crosshair)
        self.ui.Data2D_graph.ui.ROIselect.sigRegionChanged.connect(self.roiChanged)
        #self.ui.Data2D_graph.ui.ROI_combo.currentIndexChanged.connect(self.set_roi_connect) #because when the shape of roi is changed , it loses the connection
        self.ui.Open_Tree.clicked.connect(lambda: self.update_status(""))
        self.ui.Open_Tree.clicked.connect(self.ui.Tree.expandAll)
        self.ui.Close_Tree.clicked.connect(lambda: self.update_status(""))
        self.ui.Close_Tree.clicked.connect(self.ui.Tree.collapseAll)
        self.ui.Open_Tree_Selected.clicked.connect(lambda: self.update_status(""))
        self.ui.Open_Tree_Selected.clicked.connect(self.open_Tree_selection)
        self.ui.process_data_pb.clicked.connect(lambda: self.update_status(""))
        self.ui.process_data_pb.clicked.connect(self.process_data)
        self.ui.measure_type_combo.currentTextChanged[str].connect(self.update_measurement_subtype)
        self.update_measurement_subtype(self.ui.measure_type_combo.currentText(),update=False)
        self.ui.measure_subtype_combo.currentTextChanged.connect(self.update_measurement)
        self.ui.selected_region_blue.sigRegionChangeFinished.connect(self.update_measurement)
        self.ui.selected_region_blue.sigRegionChanged.connect(self.update_measurement)
        self.ui.selected_region_green.sigRegionChangeFinished.connect(self.update_measurement)
        self.ui.selected_region_green.sigRegionChanged.connect(self.update_measurement)
        self.ui.selected_region_red.sigRegionChangeFinished.connect(self.update_measurement)
        self.ui.selected_region_red.sigRegionChanged.connect(self.update_measurement)
        self.ui.Tree.currentItemChanged.connect(self.update_Gui_with_Tree_selection)
        self.ui.Tree.currentItemChanged.connect(self.update_crosshair)
        
        self.ui.save_process_pb.clicked.connect(self.save_processed_data)
    
        self.ui.remove_spikes_cb.clicked.connect(self.update_measurement)
        self.ui.show_despiked_cb.clicked.connect(self.update_measurement)
        self.ui.threshold_sb.valueChanged.connect(self.update_measurement)
        self.ui.despiked_width_average_sb.valueChanged.connect(self.update_measurement)
        self.ui.despiked_width_spikes_sb.valueChanged.connect(self.update_measurement)
        self.ui.despiked_Nloop_sb.valueChanged.connect(self.update_measurement)

    def set_roi_connect(self):
        self.ui.Data2D_graph.ui.ROIselect.sigRegionChanged.connect(self.roiChanged)
        

    def roiChanged(self):
        try:
            if self.ui.merge_spectra_cb.isChecked():
                axes = (0, 1)
                data, coords = self.ui.Data2D_graph.ui.ROIselect.getArrayRegion(self.data_struct.data2D["blue"], self.ui.Data2D_graph.ui.img_blue, axes, returnMappedCoords=True)
                channels=[]
                xcoords=[int(np.rint(num)) for elem in coords[1,:,:].tolist() for num in elem]
                ycoords=[int(np.rint(num)) for elem in coords[0,:,:].tolist() for num in elem]
                
                channels=set([self.parameters.current_carto+"_MoveIU_000_{:04d}".format(indx)+"_MoveIU_001_{:04d}_DetIU_CH00".format(indy)
                          for (indx,indy) in  zip(xcoords,ycoords)]) # I use a set to make sure there is no duplicates
                
                data_spectrum=0
                for channel in channels:
                    try:
                        spectrum=self.parameters.tdms_file.channel_data(self.parameters.current_carto+"_Det1D",channel)
                    except:
                        spectrum=0
                    data_spectrum=data_spectrum+spectrum
                data_spectrum=data_spectrum/len(channels)
                xaxis=self.parameters.tdms_file.channel_data(self.parameters.current_carto+"_Det1D","Xaxis")
                self.ui.curve_1D.setData(xaxis,data_spectrum)

        except Exception as e:
            self.update_status(str(e),self.wait_time)

    def show_ROI_for_average(self,signal):
        self.ui.Data2D_graph.ui.ROIselectBtn.setChecked(signal)
        self.ui.Data2D_graph.roiClicked()

    def update_color_regions(self,txt):
        if txt=="B":
            self.ui.selected_region_blue.setVisible(True)
            self.ui.selected_region_red.setVisible(False)
            self.ui.selected_region_green.setVisible(False)
            self.ui.result_blue_label.setVisible(True)
            self.ui.result_green_label.setVisible(False)
            self.ui.result_red_label.setVisible(False)
            self.ui.result_edit_blue.setVisible(True)
            self.ui.result_edit_green.setVisible(False)
            self.ui.result_edit_red.setVisible(False)
            self.ui.Data2D_graph.ui.img_blue.setVisible(True)
            self.ui.Data2D_graph.ui.img_green.setVisible(False)
            self.ui.Data2D_graph.ui.img_red.setVisible(False)

        elif txt=="BG":
            self.ui.selected_region_blue.setVisible(True)
            self.ui.selected_region_red.setVisible(False)
            self.ui.selected_region_green.setVisible(True)
            self.ui.result_blue_label.setVisible(True)
            self.ui.result_green_label.setVisible(True)
            self.ui.result_red_label.setVisible(False)
            self.ui.result_edit_blue.setVisible(True)
            self.ui.result_edit_green.setVisible(True)
            self.ui.result_edit_red.setVisible(False)
            self.ui.Data2D_graph.ui.img_blue.setVisible(True)
            self.ui.Data2D_graph.ui.img_green.setVisible(True)
            self.ui.Data2D_graph.ui.img_red.setVisible(False)
        elif txt=="RGB":
            self.ui.selected_region_blue.setVisible(True)
            self.ui.selected_region_red.setVisible(True)
            self.ui.selected_region_green.setVisible(True)
            self.ui.result_blue_label.setVisible(True)
            self.ui.result_green_label.setVisible(True)
            self.ui.result_red_label.setVisible(True)
            self.ui.result_edit_blue.setVisible(True)
            self.ui.result_edit_green.setVisible(True)
            self.ui.result_edit_red.setVisible(True)
            self.ui.Data2D_graph.ui.img_blue.setVisible(True)
            self.ui.Data2D_graph.ui.img_green.setVisible(True)
            self.ui.Data2D_graph.ui.img_red.setVisible(True)
        

    def update_cmap(self,cmap):
        pixmap=self.map_to_pixmap(cm.cmap_d[cmap])
        scene=QtWidgets.QGraphicsScene(None)
        scene.addPixmap(pixmap)
        self.ui.cmap_graphicsView.setScene(scene)

    def load_1D_dialog(self):
        try:
            if self.save_in_new_tdms_bt.isChecked():
                tdms_fname = QtWidgets.QFileDialog.getSaveFileName(MainWindow, 'Create a new tdms file',self.ui.Filenamepath.toPlainText(),"TDMS files (*.tdms)")
                tdms_fname=tdms_fname[0]
            else:
                tdms_fname=self.parameters.tdms_file_name
            if not( not(tdms_fname)): #execute if the user didn't cancel the file selection
                self.parameters.tdms_file_name=tdms_fname
                file_names = QtWidgets.QFileDialog.getOpenFileNames(MainWindow, 'Choose 1D data files',self.ui.Filenamepath.toPlainText(),"Data (*.dat *.txt)")
                file_names=file_names[0]
                if not( not(file_names)): #execute if the user didn't cancel the file selection
                    for file_name in file_names:
                        Dialog = QtWidgets.QDialog();
                        prog = Trace1D_selection(Dialog,file_name);
                        prog.selected_data.accept_reject.connect(self.load_1D)
                        Dialog.exec()
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)
    
    @pyqtSlot(list)
    def load_1D(self,data):
        accepted=data[0]
        data_name=data[1]
        xdata=data[2]
        ydata=data[3]
        try:
            if accepted:
                if os.path.isfile(self.parameters.tdms_file_name):
                    writing_mode="a"
                else:
                    writing_mode="w"
                with TdmsWriter_custom(self.parameters.tdms_file_name,mode=writing_mode) as tdms_writer:
                    channels=[]
                    base_group_name=data_name
                    base_group_name= re.sub('[_]', '', base_group_name) #remove any "_" characters in the group names. These "_" are reserved to order the Tree
        
                    group=mylib.GroupObject(base_group_name)
                    tdms_writer.write_segment([group])
                    
                    group_name=base_group_name+"_1DTrace"
                    channels.append(mylib.GroupObject(group_name))
                    channels.append(mylib.ChannelObject(group_name,"Xaxis",xdata))
                    channels.append(mylib.ChannelObject(group_name,"Data",ydata))
                    tdms_writer.write_segment(channels)
                self.parameters.tdms_file=TdmsFile(self.parameters.tdms_file_name)
                self.populate_Tree()
                index=self.ui.Tree.indexFromItem(self.ui.Tree.findItems(self.parameters.current_carto,Qt.MatchExactly| Qt.MatchRecursive,0)[0])
                self.ui.Tree_open_children(index)
                self.ui.Tree_open_parents(index)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def save_plotting_fun(self):
        try:
            image_name = QtWidgets.QFileDialog.getSaveFileName(MainWindow, 'Create a new image file',self.ui.Filenamepath.toPlainText(),"Image (*.png *.jpg *.svg *.pdf)")
            image_name=image_name[0]
            root,ext=os.path.splitext(image_name)
            if not not image_name:
                self.ui.figure.savefig(image_name)
                
    
        except Exception as e:
            self.update_status(str(e))

    def update_matplotlib(self,type="",update=False):
        try:
            if type!="":
                self.type_plot=type
            
            if not update:
                self.ui.figure.clear()
                self.ui.ax1=self.ui.figure.add_subplot(1,1,1)
            
            
            cmap=self.ui.cmap_combo.currentText()
            aspect=self.ui.aspect_combo.currentText()


            if self.type_plot=="2D":
                xaxis=np.unique(self.data_struct.xaxis2D)
                yaxis=np.unique(self.data_struct.yaxis2D)
                data=self.data_struct.data2D["blue"]
                self.pmesh=self.ui.ax1.pcolormesh(xaxis,yaxis,(data), cmap=cmap)
            elif self.type_plot=="1D":
                xaxis=self.data_struct.xaxis1D
                data=self.data_struct.data1D
                self.ui.ax1.plot(xaxis,data)
            else:
                return

            if self.ui.colorbar_cb.isChecked() and self.pmesh!=None:
                if hasattr(self,'colorbar'):
                    self.ui.colorbar.remove()
                self.ui.colorbar=self.ui.figure.colorbar(self.pmesh)
            
            if self.ui.use_labels_cb.isChecked():
                self.ui.ax1.set_xlabel(self.ui.xlabel_edit.text())
                self.ui.ax1.set_ylabel(self.ui.ylabel_edit.text())
                self.ui.ax1.set_title(self.ui.title_edit.text())
                
                
            self.ui.ax1.set_aspect(aspect)
            self.ui.canvas.draw()
           

        except Exception as e:
            self.update_status(str(e))

    def map_to_pixmap(self,cmap):
        sp = SubplotParams(left=0., bottom=0., right=1., top=1.)
        fig = Figure((2.5,.2), subplotpars = sp)
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient, gradient))
        ax.imshow(gradient, aspect=10, cmap=cmap)
        ax.set_axis_off()
        canvas.draw()
        size = canvas.size()
        width, height = size.width(), size.height()
        im = QImage(canvas.buffer_rgba(), width, height, QImage.Format_ARGB32)
        
        return QPixmap(im)

    def set_current_as_bkg(self):
        try:
            if not(self.ui.set_whole_as_bkg_cb.isChecked()):
                if not (not(self.parameters.current_channel)):
                    if "Det1D" in self.parameters.current_group or "1DTrace" in self.parameters.current_group:
                        self.ui.background_edit.setText(self.parameters.current_channel)
                        data=self.parameters.tdms_file.channel_data(self.parameters.current_group,self.parameters.current_channel)
                        self.parameters.current_bkg=self.parameters.current_channel
                        tdms_file_name=self.parameters.tdms_file_name
                        with TdmsWriter_custom(tdms_file_name,mode='a') as tdms_writer: # we append data to existing tdms file
                            group_name=self.parameters.current_group
                            channels=[]
                            channels.append(mylib.ChannelObject(group_name,"Bkg",data,properties=dict([("bkg_name",self.parameters.current_bkg)])))
                            tdms_writer.write_segment(channels)
                    self.parameters.tdms_file=TdmsFile(self.parameters.tdms_file_name)
                    self.populate_Tree()
                    index=self.ui.Tree.indexFromItem(self.ui.Tree.findItems(self.parameters.current_carto,Qt.MatchExactly| Qt.MatchRecursive,0)[0])
                    self.ui.Tree_open_children(index)
                    self.ui.Tree_open_parents(index)
            else:
                self.ui.background_edit.setText(self.parameters.current_carto)
                
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)  
            
    def open_Tree_selection(self):
        try:
            self.ui.Tree_open_children(self.ui.Tree.selectedIndexes()[0])
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    @pyqtSlot(float,float)
    def find_item_from_crosshair(self,xpos,ypos):
        try:
            indx=int(xpos)
            indy=int(ypos)
            channel_name=self.parameters.current_carto+"_MoveIU_000_{:04d}".format(indx)+"_MoveIU_001_{:04d}_DetIU_CH00".format(indy)
            self.ui.Tree.setCurrentIndex(self.ui.Tree.indexFromItem(self.ui.Tree.findItems(channel_name,Qt.MatchExactly| Qt.MatchRecursive,0)[0]))
            
        except Exception as e:
            self.update_status(str(e))

    def update_progress_bar(self,status="",value=0):
        self.ui.status_label.setVisible(True)
        self.ui.status_progressbar.setVisible(True)
        self.ui.status_label.setText(status)
        self.ui.status_progressbar.setValue(value)

    def delete_tdms_data(self):
        group=self.parameters.current_group
        channel=self.parameters.current_channel
        try:
            if not not(group):
                self.ui.MainWindow.setEnabled(False)
                if not not(channel):
                    TdmsWriter_custom.remove_channel(self.parameters.tdms_file_name,group,channel)
                else:
                    TdmsWriter_custom.remove_group(self.parameters.tdms_file_name,group)
                self.parameters.tdms_file=TdmsFile(self.parameters.tdms_file_name)
                self.populate_Tree()
                self.ui.MainWindow.setEnabled(True)
            
                index=self.ui.Tree.indexFromItem(self.ui.Tree.findItems(self.parameters.current_carto,Qt.MatchExactly| Qt.MatchRecursive,0)[0])
                self.Tree_open_children(index)
                self.Tree_open_parents(index)
                self.update_status("Ready",wait_time=self.wait_time)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def export_data2D_fun(self):
        try:
            image_name = QtWidgets.QFileDialog.getSaveFileName(MainWindow, 'Create a new image text file',self.ui.Filenamepath.toPlainText(),"data (*.dat)")
            image_name=image_name[0]
            if not( not(image_name)):
                data_all=np.array([0])
                data_all=np.append(data_all,np.unique(self.data_struct.xaxis2D))
                data_all= np.expand_dims(data_all, axis=0)
                data_y=np.unique(self.data_struct.yaxis2D)
                data_y = np.expand_dims(data_y, axis=1)
                data_y=np.append(data_y,self.data_struct.data2D["blue"],axis=1)
                data_all=np.append(data_all,data_y,axis=0)
                np.savetxt(image_name,data_all,fmt='%.6e',delimiter="\t",header=self.parameters.current_group)
        except Exception as e:
            self.update_status(str(e))

    def LoadCartographyAFM_fun(self,fnames=None,new_tdms=False):
        try:
            if new_tdms:
                tdms_fname = QtWidgets.QFileDialog.getSaveFileName(MainWindow, 'Create a new tdms file',self.ui.Filenamepath.toPlainText(),"TDMS files (*.tdms)")
                tdms_fname=tdms_fname[0]
            else:
                tdms_fname=self.parameters.tdms_file_name
            if not( not(tdms_fname)): #execute if the user didn't cancel the file selection
                self.parameters.tdms_file_name=tdms_fname
                
                if not fnames:
                    path=self.ui.Filenamepath.toPlainText()
                    fnames = QtWidgets.QFileDialog.getOpenFileNames(MainWindow, 'Choose AFM Text files',path,"AFM file (*.txt)")
                    fnames=fnames[0]
                if not( not(fnames[0])): #execute if the user didn't cancel the file selection
                    self.ui.MainWindow.setEnabled(False)
                    for fname in fnames:
                        (head,filename)=os.path.split(fname)
                        #(filename,ext)=os.path.splitext(filename)
                        self.ui.Filenamepath.setPlainText(fname)
                        self.load_AFM_data(fname) #load data and write them in the tdms file
                    self.parameters.tdms_file=TdmsFile(self.parameters.tdms_file_name) #reload locally the tdms file data
                    self.populate_Tree()
                    self.ui.MainWindow.setEnabled(True)
                    self.update_status('Ready',wait_time=self.wait_time)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def load_AFM_data(self,fname):
        data_all=np.loadtxt(fname,skiprows=11)
        x_positions=data_all[:,0]
        x_positions_unique=np.unique(x_positions)
        y_positions=data_all[:,1]
        y_positions_unique=np.unique(y_positions)
        data_AFM=data_all[:,2]
        (head,tail)=os.path.split(fname)
        base_group_name,ext=os.path.splitext(tail)
        base_group_name= re.sub('[_]', '', base_group_name) #remove any "_" characters in the group names. These "_" are reserved to order the Tree
        if os.path.isfile(self.parameters.tdms_file_name):
            writing_mode="a"
        else:
            writing_mode="w"
        with TdmsWriter_custom(self.parameters.tdms_file_name,mode=writing_mode) as tdms_writer:
            channels=[]
            data2D_linear=[]
            group=mylib.GroupObject(base_group_name)
            tdms_writer.write_segment([group])

            #group_name=base_group_name+"_Det1D"
            #channels.append(mylib.GroupObject(group_name))
            #channels.append(mylib.ChannelObject(group_name,"Xaxis",lambda_vect))
            #for ind_line in range(np.size(data_AFM,0)):
                #ind_x=mylib.find_index(x_positions_unique,x_positions[ind_line])[0][0]
                #ind_y=mylib.find_index(y_positions_unique,y_positions[ind_line])[0][0]
                #channel_name=base_group_name+"_MoveIU_000_{:04d}".format(ind_x)+"_MoveIU_001_{:04d}_DetIU_CH00".format(ind_y)
                #channels.append(mylib.ChannelObject(group_name,channel_name, data_AFM[ind_line,:]))
                #data2D_linear.append(np.sum(data_AFM[ind_line,:]))
            #tdms_writer.write_segment(channels)
            #data2D_linear=np.array(data2D_linear)
            data2D_linear=data_AFM
            group_name=base_group_name+"_scan"
            channels=[]
            channels.append(mylib.GroupObject(group_name))
            channels.append(mylib.ChannelObject(group_name,"Xaxis",x_positions))
            channels.append(mylib.ChannelObject(group_name,"Yaxis",y_positions))
            channels.append(mylib.ChannelObject(group_name,"Data",data2D_linear))
            channels.append(mylib.ChannelObject(group_name,"Data2D",data2D_linear,properties=dict([('Ncol',len(x_positions_unique)),('Nline',len(y_positions_unique))])))
            tdms_writer.write_segment(channels)

    def LoadCartographyLabspec_fun(self,fnames=None,new_tdms=False,dual=False):
        try:
            if new_tdms:
                tdms_fname = QtWidgets.QFileDialog.getSaveFileName(MainWindow, 'Create a new tdms file',self.start_path,"TDMS files (*.tdms)")
                tdms_fname=tdms_fname[0]
                self.start_path=os.path.split(tdms_fname)[0]
            else:
                tdms_fname=self.parameters.tdms_file_name
            if not( not(tdms_fname)): #execute if the user didn't cancel the file selection
                self.parameters.tdms_file_name=tdms_fname
                
                if not fnames:
                    path=self.ui.Filenamepath.toPlainText()
                    fnames = QtWidgets.QFileDialog.getOpenFileNames(MainWindow, 'Choose labspec files',self.start_path,"Labspec file (*.txt)")
                    fnames=fnames[0]
                    self.start_path=os.path.split(fnames[0])[0]
                if not( not(fnames[0])): #execute if the user didn't cancel the file selection
                    self.ui.MainWindow.setEnabled(False)
                    for fname in fnames:
                        (head,filename)=os.path.split(fname)
                        #(filename,ext)=os.path.splitext(filename)
                        self.ui.Filenamepath.setPlainText(fname)
                        self.load_labspec_data(fname,dual=dual) #load data and write them in the tdms file
                    self.parameters.tdms_file=TdmsFile(self.parameters.tdms_file_name) #reload locally the tdms file data
                    self.populate_Tree()
                    self.ui.MainWindow.setEnabled(True)
                    self.update_status('Ready',wait_time=self.wait_time)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def load_labspec_data(self,fname,dual=False):
        data_all=np.loadtxt(fname,skiprows=1)
        lambda_vect=np.genfromtxt(fname,max_rows=1)
        if len(lambda_vect)==np.size(data_all,1)-2:
            if not(dual):
                x_positions=data_all[:,1]
                y_positions=data_all[:,0]
            else:
                x_positions=data_all[::2,1]
                y_positions=data_all[::2,0]
            x_positions_unique=np.unique(x_positions)
            y_positions_unique=np.unique(y_positions)
            spectra=data_all[:,2:]
        elif len(lambda_vect)==np.size(data_all,1)-1:
            x_positions=data_all[:,0]
            x_positions_unique=np.unique(x_positions)
            y_positions=np.zeros_like(x_positions)
            y_positions_unique=np.unique(y_positions)
            spectra=data_all[:,1:]
        (head,tail)=os.path.split(fname)
        base_group_name,ext=os.path.splitext(tail)
        base_group_name= re.sub('[_]', '', base_group_name) #remove any "_" characters in the group names. These "_" are reserved to order the Tree
        base_group_name_tot=[base_group_name]
        if dual:
            spectra_tot=[spectra[1::2],spectra[:-1:2,:]]
            base_group_name_tot.append(base_group_name+"-dual")
        else:
            spectra_tot=[spectra]
        if os.path.isfile(self.parameters.tdms_file_name):
            writing_mode="a"
        else:
            writing_mode="w"
        with TdmsWriter_custom(self.parameters.tdms_file_name,mode=writing_mode) as tdms_writer:
            for ind,base_group_name in enumerate(base_group_name_tot):
                spectra=spectra_tot[ind]
                channels=[]
                data2D_linear=[]
                group=mylib.GroupObject(base_group_name)
                tdms_writer.write_segment([group])

                group_name=base_group_name+"_Det1D"
                channels.append(mylib.GroupObject(group_name))
                channels.append(mylib.ChannelObject(group_name,"Xaxis",lambda_vect))
                for ind_line in range(np.size(spectra,0)):
                    ind_x=mylib.find_index(x_positions_unique,x_positions[ind_line])[0][0]
                    ind_y=mylib.find_index(y_positions_unique,y_positions[ind_line])[0][0]
                    channel_name=base_group_name+"_MoveIU_000_{:04d}".format(ind_x)+"_MoveIU_001_{:04d}_DetIU_CH00".format(ind_y)
                    channels.append(mylib.ChannelObject(group_name,channel_name, spectra[ind_line,:]))
                    data2D_linear.append(np.sum(spectra[ind_line,:]))
                tdms_writer.write_segment(channels)
                data2D_linear=np.array(data2D_linear)
                group_name=base_group_name+"_scan"
                channels=[]
                channels.append(mylib.GroupObject(group_name))
                channels.append(mylib.ChannelObject(group_name,"Xaxis",x_positions))
                channels.append(mylib.ChannelObject(group_name,"Yaxis",y_positions))
                channels.append(mylib.ChannelObject(group_name,"Data",data2D_linear))
                channels.append(mylib.ChannelObject(group_name,"Data2D",data2D_linear,properties=dict([('Ncol',len(x_positions_unique)),('Nline',len(y_positions_unique))])))
                tdms_writer.write_segment(channels)





    def LoadCartography_Separated_Files_fun(self,fnames=None,labview=True,new_tdms=False):
        try:
            if new_tdms:
                tdms_fname = QtWidgets.QFileDialog.getSaveFileName(MainWindow, 'Create a new tdms file',self.start_path,"TDMS files (*.tdms)")
                tdms_fname=tdms_fname[0]
                self.start_path=os.path.split(tdms_fname)[0]
            else:
                tdms_fname=self.parameters.tdms_file_name
            if not( not(tdms_fname)): #execute if the user didn't cancel the file selection
                self.parameters.tdms_file_name=tdms_fname
                
                if not fnames:
                    path=self.ui.Filenamepath.toPlainText()
                    if labview:
                        fnames = QtWidgets.QFileDialog.getOpenFileNames(MainWindow, 'Choose Separated files on the form: CartoNNN_MoveIU_000_XXXX_MoveIU_001_YYYY_DetIU.dat',self.start_path,"Spectra files (*.dat)")
                    else:
                        fnames = QtWidgets.QFileDialog.getOpenFileNames(MainWindow, 'Choose Separated files on the form: filename_XXX_YYY or filename_XXX',self.start_path,"Spectra files (*.txt)")
                    fnames=fnames[0]
                    self.start_path=os.path.split(fnames[0])[0]
                if not( not(fnames[0])): #execute if the user didn't cancel the file selection
                    self.ui.MainWindow.setEnabled(False)
                    (head,filename)=os.path.split(fnames[0])
                    self.ui.Filenamepath.setPlainText(fnames[0])
                    self.load_Separated_Files_data(fnames,labview=labview) #load data and write them in the tdms file
                    self.parameters.tdms_file=TdmsFile(self.parameters.tdms_file_name) #reload locally the tdms file data
                    self.populate_Tree()
                    self.ui.MainWindow.setEnabled(True)
                    self.update_status('Ready',wait_time=self.wait_time)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def load_Separated_Files_data(self,fnames,labview=True):
        x_positions=[]
        y_positions=[]
        if labview:
            data_all=np.loadtxt(fnames[0],skiprows=2)
        else:
            data_all=np.loadtxt(fnames[0],skiprows=0)
        lambda_vect=data_all[:,0]
        Nchannels=np.size(data_all,1)-1
        spectra=np.zeros((len(fnames),len(lambda_vect),Nchannels))

        for ind_file,fname in enumerate(fnames):
            (head,tail)=os.path.split(fname)
            base_group_name,ext=os.path.splitext(tail)
            m=re.findall('(?<=_)\d*',base_group_name)
            msplit=re.split('_',base_group_name)

            if labview:
                x_positions.append(float(m[-5]))
                y_positions.append(float(m[-2]))
                base_group_name=msplit[0]
            else:
                if len(m)==1:
                    x_positions.append(float(m[0]))
                    y_positions.append(0)
                    base_group_name= re.sub('_'+str(m[0]), '', base_group_name) #remove any "_" characters in the group names. These "_" are reserved to order the Tree
                    base_group_name= re.sub('_', '', base_group_name)
                else:
                    if m[-2]!="":
                        x_positions.append(float(m[-2]))
                        y_positions.append(float(m[-1]))
                        base_group_name= re.sub('_'+str(m[-1]), '', base_group_name) #remove any "_" characters in the group names. These "_" are reserved to order the Tree
                        base_group_name= re.sub('_'+str(m[-2]), '', base_group_name) #remove any "_" characters in the group names. These "_" are reserved to order the Tree
                        base_group_name= re.sub('_', '', base_group_name)
                    else:
                        x_positions.append(float(m[-1]))
                        y_positions.append(0)
                        base_group_name= re.sub('_'+str(m[-1]), '', base_group_name) #remove any "_" characters in the group names. These "_" are reserved to order the Tree
                        base_group_name= re.sub('_', '', base_group_name)
            if labview:
                data_all=np.loadtxt(fnames[ind_file],skiprows=2)
            else:
                data_all=np.loadtxt(fnames[ind_file],skiprows=0)
            
            spectra[ind_file,:,:]=data_all[:,1:]

        x_positions=np.array(x_positions)
        y_positions=np.array(y_positions)
        x_positions_unique=np.unique(x_positions)
        y_positions_unique=np.unique(y_positions)

        if os.path.isfile(self.parameters.tdms_file_name):
            writing_mode="a"
        else:
            writing_mode="w"
        with TdmsWriter_custom(self.parameters.tdms_file_name,mode=writing_mode) as tdms_writer:
            channels=[]
            data2D_linear=[]
            group=mylib.GroupObject(base_group_name)
            tdms_writer.write_segment([group])

            group_name=base_group_name+"_Det1D"
            channels.append(mylib.GroupObject(group_name))
            channels.append(mylib.ChannelObject(group_name,"Xaxis",lambda_vect))
            
            for ind_line in range(np.size(spectra,0)):
                ind_x=mylib.find_index(x_positions_unique,x_positions[ind_line])[0][0]
                ind_y=mylib.find_index(y_positions_unique,y_positions[ind_line])[0][0]
                for ind_channel in range(Nchannels):
                    channel_name=base_group_name+"_MoveIU_000_{:04d}".format(ind_x)+"_MoveIU_001_{:04d}_DetIU_CH{:02d}".format(ind_y,ind_channel)
                    channels.append(mylib.ChannelObject(group_name,channel_name, spectra[ind_line,:,ind_channel]))
                data2D_linear.append(np.sum(spectra[ind_line,:,0]))
            tdms_writer.write_segment(channels)
            data2D_linear=np.array(data2D_linear)
            group_name=base_group_name+"_scan"
            channels=[]
            channels.append(mylib.GroupObject(group_name))
            channels.append(mylib.ChannelObject(group_name,"Xaxis",x_positions))
            channels.append(mylib.ChannelObject(group_name,"Yaxis",y_positions))
            channels.append(mylib.ChannelObject(group_name,"Data",data2D_linear))
            channels.append(mylib.ChannelObject(group_name,"Data2D",data2D_linear,properties=dict([('Ncol',len(x_positions_unique)),('Nline',len(y_positions_unique))])))
            tdms_writer.write_segment(channels)







    def update_measurement(self):
        
        try:
            if self.ui.colors_combo.currentText()=="B":
                limits_blue=self.ui.selected_region_blue.getRegion()
                limits_green=None
                limits_red=None
            elif self.ui.colors_combo.currentText()=="BG":
                limits_blue=self.ui.selected_region_blue.getRegion()
                limits_green=self.ui.selected_region_green.getRegion()
                limits_red=None
            elif self.ui.colors_combo.currentText()=="RGB":
                limits_blue=self.ui.selected_region_blue.getRegion()
                limits_green=self.ui.selected_region_green.getRegion()
                limits_red=self.ui.selected_region_red.getRegion()
            self.selected_limits=dict(blue=limits_blue,green=limits_green,red=limits_red)

            mtype=self.ui.measure_type_combo.currentText()
            msubtype=self.ui.measure_subtype_combo.currentText() ##to do: write a class that holds values for the subtype and change the GUI according to mtype
            msub_ind=self.ui.measure_subtype_combo.currentIndex()
            self.measurement_class=DAQ_Navigation_process_analysis(self.selected_limits,self.parameters.tdms_file,[self.parameters.current_channel],
                    self.parameters.current_carto,self.parameters.current_group,self.ui)
            self.measurement_class.curve_fitting_sig[list].connect(self.show_fit)
            
            data1D=self.data_struct.data1D

            if self.ui.apply_bkg_check.isChecked():

                if not(self.ui.set_whole_as_bkg_cb.isChecked()):
                    channel_names=[channel.channel for channel in self.parameters.tdms_file.group_channels(self.parameters.current_group)]
                    if "Bkg" in channel_names:
                        bkg=self.parameters.tdms_file.channel_data(self.parameters.current_group, "Bkg")
                else:
                    if self.ui.background_edit.text() is not "":
                        parent_item=self.ui.Tree.findItems(self.ui.background_edit.text()+"_Det1D",Qt.MatchExactly| Qt.MatchRecursive,0)[0]
                        for ind_child in range(parent_item.childCount()):
                            if parent_item.child(ind_child).text(0)=='CH00':
                                bkg_item=parent_item.child(ind_child).child(self.parameters.current_channel_index)
                                break
                        channel_name=bkg_item.text(0)
                        bkg=self.parameters.tdms_file.channel_data(self.ui.background_edit.text()+"_Det1D", channel_name)

                if self.ui.bkg_type.currentText()=="Sub.":
                    data1D=data1D-bkg
                elif self.ui.bkg_type.currentText()=="Ratio":
                    data1D=data1D/bkg
                if self.ui.do_zero_cb.isChecked():
                    data1D=data1D*(data1D>=0)
            if self.ui.remove_spikes_cb.isChecked():
                for ind in range(self.ui.despiked_Nloop_sb.value()):
                    data1D,indices=self.measurement_class.thresholding(data1D,self.ui.threshold_sb.value(),self.ui.despiked_width_average_sb.value(),self.ui.despiked_width_spikes_sb.value())
            self.show_despiked(data1D)
            
                

            colors=["blue","green","red"]
            for color in colors:
                if self.selected_limits[color] is not None:
                    xmin=self.selected_limits[color][0]
                    xmax=self.selected_limits[color][1]
                    (status,result_measurement)=self.measurement_class.update_measurement(xmin,xmax,self.data_struct.xaxis1D,data1D,mtype,msubtype,msub_ind)
                    self.update_status(status,wait_time=self.wait_time)
                    if color is "blue":
                        self.ui.result_edit_blue.setText("{:.3e}".format(result_measurement))
                    elif color is "green":
                        self.ui.result_edit_green.setText("{:.3e}".format(result_measurement))
                    elif color is "red":
                        self.ui.result_edit_red.setText("{:.3e}".format(result_measurement))

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)
            result_measurement=0
            self.ui.result_edit_blue.setText("{:.3e}".format(result_measurement))
            self.ui.result_edit_green.setText("{:.3e}".format(result_measurement))
            self.ui.result_edit_red.setText("{:.3e}".format(result_measurement))
            return result_measurement


    def save_processed_data(self):
        try:
            colors=[]
            if self.data_struct.data_linear['blue'] is not None:
                colors.append("blue")
            if self.data_struct.data_linear['green'] is not None:
                colors.append("green")
            if self.data_struct.data_linear['red'] is not None:
                colors.append("red")
            for color in colors:
                tdms_file_name=self.parameters.tdms_file_name
                with TdmsWriter_custom(tdms_file_name,mode='a') as tdms_writer: # we append data to existing tdms file
                    groups=self.parameters.tdms_file.groups()
                    ind=0
                    for group in groups:
                        if (self.parameters.current_carto in group) and ("analysis" in group):
                            m = re.search('(?<=_)\d+', group)
                            if m!=None:
                                ind=int(m.group(0))+1
                    group_name=self.parameters.current_carto+"_analysis_{:03d}".format(ind)
                    channels=[]
                    channels.append(mylib.GroupObject(group_name,properties=self.get_process_properties(self.selected_limits[color])))
                    channels.append(mylib.ChannelObject(group_name,"Xaxis",self.data_struct.xaxis2D))
                    channels.append(mylib.ChannelObject(group_name,"Yaxis",self.data_struct.yaxis2D))
                    channels.append(mylib.ChannelObject(group_name,"Data",self.data_struct.data_linear[color]))
                    channels.append(mylib.ChannelObject(group_name,"Data2D",self.data_struct.data_linear[color],properties=dict([('Ncol',self.data_struct.Ncol),('Nline',self.data_struct.Nline)])))
                    tdms_writer.write_segment(channels)
                self.parameters.tdms_file=TdmsFile(self.parameters.tdms_file_name)
            self.populate_Tree()
            index=self.ui.Tree.indexFromItem(self.ui.Tree.findItems(self.parameters.current_carto,Qt.MatchExactly| Qt.MatchRecursive,0)[0])
            self.Tree_open_children(index)
            self.Tree_open_parents(index)
        except Exception as e:
            self.update_status(str(e),self.wait_time)

    def update_data_process(self):
        
        self.data_process.measurement_type=self.ui.measure_type_combo.currentText()
        self.data_process.measurement_subtype=self.ui.measure_subtype_combo.currentText()
        self.data_process.operation=self.ui.operation_edit.toPlainText()
        self.data_process.formula_params=self.ui.variables_edit.text()
        self.data_process.formula=self.ui.formula_edit.toPlainText()
        self.data_process.do_operation=self.ui.do_operation_cb.isChecked()
        

    def get_process_properties(self,selected_limits):
        xmin=selected_limits[0]
        xmax=selected_limits[1]
        properties=OrderedDict([("Measurement type",self.data_process.measurement_type),("Measurement subtype",self.data_process.measurement_subtype),
                         ("Formula parameters",self.data_process.formula_params),("Formula",self.data_process.formula),
                         ("Operation",self.data_process.operation),("Do_operation",self.data_process.do_operation),("Xmin",xmin),
                         ("Xmax",xmax),("Bkg state",self.ui.apply_bkg_check.isChecked()),("Comments",self.ui.comments_edit.toPlainText())])
        if self.ui.apply_bkg_check.isChecked():
            properties.update(dict([("Bkg type",self.ui.bkg_type.currentText()),("Bkg name",self.parameters.current_bkg)]))
        return properties
        

    def process_data(self):
        try:
            
            if self.ui.colors_combo.currentText()=="B":
                limits_blue=self.ui.selected_region_blue.getRegion()
                self.ui.Data2D_graph.ui.img_blue.setVisible(True)
                self.ui.Data2D_graph.ui.blue_cb.setChecked(True)
                limits_green=None
                limits_red=None
            elif self.ui.colors_combo.currentText()=="BG":
                limits_blue=self.ui.selected_region_blue.getRegion()
                limits_green=self.ui.selected_region_green.getRegion()
                self.ui.Data2D_graph.ui.img_blue.setVisible(True)
                self.ui.Data2D_graph.ui.img_green.setVisible(True)
                self.ui.Data2D_graph.ui.blue_cb.setChecked(True)
                self.ui.Data2D_graph.ui.green_cb.setChecked(True)
                limits_red=None
            elif self.ui.colors_combo.currentText()=="RGB":
                limits_blue=self.ui.selected_region_blue.getRegion()
                limits_green=self.ui.selected_region_green.getRegion()
                limits_red=self.ui.selected_region_red.getRegion()
                self.ui.Data2D_graph.ui.img_blue.setVisible(True)
                self.ui.Data2D_graph.ui.img_green.setVisible(True)
                self.ui.Data2D_graph.ui.img_red.setVisible(True)
                self.ui.Data2D_graph.ui.blue_cb.setChecked(True)
                self.ui.Data2D_graph.ui.green_cb.setChecked(True)
                self.ui.Data2D_graph.ui.red_cb.setChecked(True)
            selected_limits=dict(blue=limits_blue,green=limits_green,red=limits_red)

            
            mtype=self.ui.measure_type_combo.currentText()
            msubtype=self.ui.measure_subtype_combo.currentText() ##to do: write a class that holds values for the subtype and change the GUI according to mtype
            msub_ind=self.ui.measure_subtype_combo.currentIndex()

            self.update_data_process()

            child=self.ui.Tree.currentItem()
            parent=child.parent()
            Nchildren=parent.childCount()
            channels=[parent.child(index).text(0) for index in range(Nchildren)]
        
            self.measurement_thread=QThread()
            process_module = DAQ_Navigation_process_analysis(selected_limits,self.parameters.tdms_file,channels,self.parameters.current_carto,
                   self.parameters.current_group,self.ui)
            process_module.data_process_sig[list].connect(self.update_data2D_from_process)
            ##process_module.finished.connect(self.done)
            process_module.status_sig[str].connect(self.thread_status)
            self.ui.status_progressbar.setVisible(True)
            process_module.progress_bar_sig[int].connect(self.ui.status_progressbar.setValue)
            self.start_process.connect(process_module.do_process)
            
            process_module.moveToThread(self.measurement_thread)
             
            self.measurement_thread.start()
            self.start_process.emit()

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)
            pass
        
    def Quit_fun(self):
        # insert anything that needs to be closed before leaving
        self.close()

    def update_status(self,txt,wait_time=0):
        self.ui.statusbar.showMessage(txt,wait_time)
    
    def update_crosshair(self,signal):
        try:
            m = re.findall('(?<=_)(\d+)', signal.text(0))
            self.ui.Data2D_graph.crosshair.set_crosshair_position(int(m[1]),int(m[3]))
        except:
            pass

    def update_Gui_with_Tree_selection(self,signal):
        try:
            self.parameters.current_item=signal.text(0)
            self.parameters.current_channel_index=signal.parent().indexOfChild(signal) 
            current_carto=self.find_carto_name(self,signal)
            (current_group,current_channel)=self.find_group_name(current_carto,signal)
            self.ui.Current_Group_edit.setText(current_group)
            self.ui.Current_Channel_edit.setPlainText(current_channel)
            self.ui.Current_Carto_edit.setText(current_carto)
            
            if self.parameters.current_carto!=current_carto:
                self.update_2D_data(current_carto)

            self.parameters.current_carto=current_carto
            self.parameters.current_group=current_group
            self.parameters.current_channel=current_channel
            
            self.ui.table_properties.clearContents()
            self.ui.table_properties.setRowCount(0)
            if not(not(current_group)):
                self.update_properties_table()
            if not(not(current_channel)):
                self.load_TDMS_data()
                self.update_plots()
                self.update_measurement()
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)
        
    def update_2D_data(self,current_carto):
        try:
            current_group=current_carto+"_scan"
            self.data_struct.data_linear=dict(blue=self.parameters.tdms_file.channel_data(current_group, "Data"))
            obj=self.parameters.tdms_file.object(current_group,"Data2D")
            self.data_struct.xaxis2D=self.parameters.tdms_file.channel_data(current_group, "Xaxis")
            self.data_struct.yaxis2D=self.parameters.tdms_file.channel_data(current_group, "Yaxis")
            self.data_struct.Nline=obj.property('Nline')
            self.data_struct.Ncol=obj.property('Ncol')
            data_tmp=self.parameters.tdms_file.channel_data(current_group, "Data2D")
            self.data_struct.data2D=self.data_struct.reshape_from_coordinates()
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def load_TDMS_data(self):
        tdms_file=self.parameters.tdms_file
        current_carto=self.parameters.current_carto
        current_group=self.parameters.current_group
        current_channel=self.parameters.current_channel
        channel_names=[channel.channel for channel in tdms_file.group_channels(current_group)]

        if "Data2D" in current_channel:

            self.data_struct.data_linear=tdms_file.channel_data(current_group, "Data")
            obj=tdms_file.object(current_group,current_channel)
            self.data_struct.xaxis2D=tdms_file.channel_data(current_group, "Xaxis")
            self.data_struct.yaxis2D=tdms_file.channel_data(current_group, "Yaxis")
            self.data_struct.Nline=obj.property('Nline')
            self.data_struct.Ncol=obj.property('Ncol')
            data_tmp=tdms_file.channel_data(current_group, "Data2D")
            self.data_struct.data2D=self.data_struct.reshape_from_coordinates()
            
        else:
            self.data_struct.xaxis1D=tdms_file.channel_data(current_group, "Xaxis")
            self.data_struct.data1D=tdms_file.channel_data(current_group, current_channel)
            if not(self.ui.set_whole_as_bkg_cb.isChecked()):
                
                if "Bkg" in channel_names:
                    self.data_struct.bkg=tdms_file.channel_data(current_group, "Bkg")
                
                    obj=tdms_file.object(current_group, "Bkg")
                
                    self.parameters.current_bkg=obj.property("bkg_name")
            else:
                bkg_name=self.ui.background_edit.text()
                if bkg_name is not "":
                    parent_item=self.ui.Tree.findItems(bkg_name+"_Det1D",Qt.MatchExactly| Qt.MatchRecursive,0)[0]
                    for ind_child in range(parent_item.childCount()):
                        if parent_item.child(ind_child).text(0)=='CH00':
                            bkg_item=parent_item.child(ind_child).child(self.parameters.current_channel_index)
                            break
                    channel_name=bkg_item.text(0)
                    self.data_struct.bkg=tdms_file.channel_data(bkg_name+"_Det1D", channel_name)
    
    def update_properties_table(self):
        
        group_obj=self.parameters.tdms_file.object(self.parameters.current_group)
        group_properties=group_obj.properties
        if not (not self.parameters.current_channel):
            channel_obj=self.parameters.tdms_file.object(self.parameters.current_group,self.parameters.current_channel)   
            channel_properties=channel_obj.properties
            properties=mylib.merge_two_dicts(group_properties,channel_properties)
        else:
            properties=group_properties
        self.ui.table_properties.setRowCount(len(properties))
        for ind,property in enumerate(properties):
            item0=QtWidgets.QTableWidgetItem(property)
            item0.setFlags(item0.flags() ^ Qt.ItemIsEditable)
            item1=QtWidgets.QTableWidgetItem(str(properties[property]))
            item1.setFlags(item1.flags() ^ Qt.ItemIsEditable)
            self.ui.table_properties.setItem(ind,0,item0)
            self.ui.table_properties.setItem(ind,1,item1)
       
        
                  
    def update_plots(self):
        current_channel=self.parameters.current_channel
        if "Data2D" in current_channel:
            self.update_2D_graph()
        else:
           self.update_1D_graph()
   
    def update_2D_graph(self):
        self.ui.Data2D_graph.setImage(self.data_struct.data2D['blue'],self.data_struct.data2D['green'],self.data_struct.data2D['red'])
        self.ui.Data2D_graph.ui.isoLine.setValue(np.mean(np.mean(self.data_struct.data2D['blue'])))
        self.ui.Data2D_graph.updateIsocurve()
        self.ui.Data2D_graph.ui.iso.setData(pg.gaussianFilter(self.data_struct.data2D['blue'], (2, 2)))
        self.ui.Data2D_graph.crosshairChanged()
            
    def update_1D_graph(self):
        try:
            channel=self.parameters.current_channel
            if "DetIU" in channel and self.ui.apply_bkg_check.isChecked():
                if self.ui.bkg_type.currentText()=="Sub.":
                    data=self.data_struct.data1D-self.data_struct.bkg
                elif self.ui.bkg_type.currentText()=="Ratio":
                    data=self.data_struct.data1D/self.data_struct.bkg
                if self.ui.do_zero_cb.isChecked():
                    data=data*(data>=0)
                self.ui.curve_1D.setData(self.data_struct.xaxis1D,data)
            else:
                if "Xaxis" in channel or "Yaxis" in channel:
                    self.ui.curve_1D.setData(self.data_struct.data1D)
                else:
                    self.ui.curve_1D.setData(self.data_struct.xaxis1D,self.data_struct.data1D)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)
             
    @staticmethod
    def find_carto_name(self,item):
        #item=QtWidgets.QTreeWidgetItem();
        
        item_txt=item.text(0)
        ind=item_txt.find("_")
        if item==None:
            current_carto=""
            return
        if ind!=-1:
            current_carto=item_txt[0:ind]
        else:
            try:
                current_carto=self.find_carto_name(self,item.parent())
            except:
                current_carto=item.text(0)

        return current_carto
        
    def find_group_name(self,current_carto,item):
        #item=QtWidgets.QTreeWidgetItem();
        
        item_txt=item.text(0)

        
        if item_txt==(current_carto):
            group_name=""
            channel_name=""
        elif (current_carto+"_scan") == item_txt:
            group_name=item_txt
            channel_name=""
        elif (current_carto+"_Det1D") == item_txt:
            group_name=item_txt
            channel_name=""
        elif (current_carto+"_analysis") in item_txt:
            group_name=item_txt
            channel_name=""
        elif "DetIU_CH" in item_txt:
            parent=item.parent()
            gdparent=parent.parent()
            group_name=gdparent.text(0)
            channel_name=item_txt
        elif "CH" in item_txt:
            parent=item.parent()
            group_name=parent.text(0)
            channel_name=""
        else:
            parent=item.parent()
            group_name=parent.text(0)
            channel_name=item.text(0)
            
        return (group_name,channel_name)

    def Load_TDMS_fun(self,fname=None):
        try:
            if not fname:
                path=self.ui.Filenamepath.toPlainText()
                fname = QtWidgets.QFileDialog.getOpenFileName(MainWindow, 'Choose a tdms file',self.start_path,"TDMS file (*.tdms)")
                fname=fname[0]
                self.start_path=os.path.split(fname)[0]
            if not( not(fname)): #execute if the user didn't cancel the file selection
                (head,filename)=os.path.split(fname)
                #(filename,ext)=os.path.splitext(filename)
                self.ui.MainWindow.setEnabled(False)
                self.ui.Filenamepath.setPlainText(fname)
                self.parameters.tdms_file=TdmsFile(fname)
                self.parameters.tdms_file_name=fname
                self.populate_Tree()
                self.ui.MainWindow.setEnabled(True)
                self.update_status('Ready',wait_time=self.wait_time)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def map_tree_items_text_index(self,item,list_item_text,list_item_index):
        list_item_index.append(self.ui.Tree.indexFromItem(item))
        list_item_text.append(item.text(0))
        for ind in range(item.childCount()):
            (list_item_text,list_item_index)=self.map_tree_items_text_index(item.child(ind),list_item_text,list_item_index)
        return (list_item_text,list_item_index)



    def populate_Tree(self):
        tdms_file=self.parameters.tdms_file
        #DAQ_Support.generate_Tree_from_tdms(self.ui.Tree,self.tdms_file)
        self.ui.Tree.setSelectionBehavior(self.ui.Tree.SelectRows)
        model =self.ui.Tree.model()
            
        #model=QtGui.QStandardItemModel()
        #model.setHorizontalHeaderLabels(['Data'])
        #self.ui.Tree.setModel(model)
            
        self.ui.Tree.setHeaderLabel(self.parameters.tdms_file_name)
        self.ui.Tree.setUniformRowHeights(True)
        self.ui.Tree.clear()

        groups=tdms_file.groups()
        cartos=list()
        for group in groups:
            ind=group.find("_")
            if ind!=-1:
                carto_name=group[0:ind]
                cartos.append(carto_name)
            #else:
            #    cartos.append(group)

        cartos_unique=mylib.remove_replica_list(cartos)
        cartos_unique.sort() 
        tree_dict=dict()


        for i,carto in enumerate(cartos_unique):
                
            carto_groups=[]
            for group in groups:
                if carto in group:
                    carto_groups.append(group)

            parent = QtWidgets.QTreeWidgetItem([carto])
            if (carto+"_scan") in groups:
                child_scan = QtWidgets.QTreeWidgetItem([carto+"_scan"])
                channels=tdms_file.group_channels(carto+"_scan")
                child_list=[]
                for channel in channels:
                    child_list.append(QtWidgets.QTreeWidgetItem([channel.channel]))
                child_scan.addChildren(child_list)
                parent.addChild(child_scan)
                self.ui.Tree.addTopLevelItem(parent)

            for group in carto_groups:
                
                if "1DTrace" in group:
                        child_scan = QtWidgets.QTreeWidgetItem([group])
                        channels=tdms_file.group_channels(group)
                        child_list=[]
                        for channel in channels:
                            child_list.append(QtWidgets.QTreeWidgetItem([channel.channel]))
                        child_scan.addChildren(child_list)
                        parent.addChild(child_scan)
                        self.ui.Tree.addTopLevelItem(parent)

                if "analysis" in group:
                    child_scan = QtWidgets.QTreeWidgetItem([group])
                    channels=tdms_file.group_channels(group)
                    child_list=[]
                    for channel in channels:
                        child_list.append(QtWidgets.QTreeWidgetItem([channel.channel]))
                    child_scan.addChildren(child_list)
                    parent.addChild(child_scan)
                    self.ui.Tree.addTopLevelItem(parent)

            if (carto+"_Det1D") in groups:
                child_det1d = QtWidgets.QTreeWidgetItem([carto+"_Det1D"])
                    
                child_det1d.addChild(QtWidgets.QTreeWidgetItem([tdms_file.object(carto+"_Det1D","Xaxis").channel]))
                
                channels=tdms_file.group_channels(carto+"_Det1D")
                channel_names=[channel.channel for channel in channels]
                if "Bkg" in channel_names:
                    child_det1d.addChild(QtWidgets.QTreeWidgetItem([tdms_file.object(carto+"_Det1D","Bkg").channel]))
                data_channels=[]
                for j,channel in enumerate(channels):
                    channel_str=channel.channel
                    ind=channel_str.find("DetIU_")
                    if ind!=-1:
                        data_channels.append(channel.channel[ind+6:])
                data_channels=mylib.remove_replica_list(data_channels)
                for data_channel in data_channels:
                    channel_child= QtWidgets.QTreeWidgetItem([data_channel])
                        
                    channels=tdms_file.group_channels(carto+"_Det1D")
                    for j,channel in enumerate(channels):
                        channel_str=channel.channel
                        if data_channel in channel_str:
                            sub_child = QtWidgets.QTreeWidgetItem([channel_str])
                            channel_child.addChild(sub_child)
                    child_det1d.addChild(channel_child)
                parent.addChild(child_det1d)


            parent.addChildren(child_list)
            self.ui.Tree.addTopLevelItem(parent)

        #(self.list_item_text,self.list_item_index)=self.map_tree_items_text_index(self.ui.Tree.invisibleRootItem(),[],[])

                # span container columns
            #self.ui.Tree.setFirstColumnSpanned(i, self.ui.Tree.rootIndex(), True)
    
    
    def Tree_open_children(self,item_index):
        if not(item_index.isValid()):
            return

        self.ui.Tree.expand(item_index)

    def Tree_open_parents(self,item_index):
        if not(item_index.isValid()):
            return
        flag=True
        empty=QtCore.QModelIndex()
        parent=item_index
        while flag:
            parent=parent.parent()
            if parent!=empty:
                self.ui.Tree.expand(parent)
            else:
                flag=False
                break


    @pyqtSlot(str)
    def update_measurement_subtype(self,mtype,update=True):
        [variables,self.formula,self.measurement_subitems]=Measurement_type.update_measurement_subtype(Measurement_type,mtype)
        
        try:
            self.ui.measure_subtype_combo.clear()    
            self.ui.measure_subtype_combo.addItems(self.measurement_subitems)
            self.ui.formula_edit.setPlainText(self.formula)
            
            if update:
                self.update_measurement()
        except Exception as e:
            self.update_status(str(e))

    @pyqtSlot(str)
    def thread_status(self,status):
        self.update_status(status,wait_time=self.wait_time)
    
    @pyqtSlot(list)
    def show_fit(self,items):
        if items[0]:
            self.ui.curve_1D_fit.setData(*items[1:])
        else:
            self.ui.curve_1D_fit.clear()
    
    def show_despiked(self,data=[]):
        if self.ui.show_despiked_cb.isChecked() and data is not []:
            self.ui.curve_1D_despiked.setData(self.data_struct.xaxis1D,data)
        else:
            self.ui.curve_1D_despiked.clear()
    

    @pyqtSlot(list)
    def update_data2D_from_process(self,items):
        self.ui.status_progressbar.setVisible(False)
        self.data_struct.xaxis2D=items[0]
        self.data_struct.yaxis_2D=items[1]
        self.data_struct.data_linear=items[2] #dict(blue=,green=,red=)
        self.data_struct.Nline=items[3]
        self.data_struct.Ncol=items[4]
        self.data_struct.data2D=self.data_struct.reshape_from_coordinates()
        self.update_2D_graph()
        


    def done(self):
        self.update_status("Processing Done!",wait_time=self.wait_time)

        

class DAQ_Navigation_Visu_struct():
    def __init__(self, tdms_file=None,current_item="",current_carto="",current_group="",current_channel="",tdms_file_name="",current_bkg=""):
        self.tdms_file = tdms_file
        self.current_item=current_item
        self.current_carto=current_carto
        self.current_group=current_group
        self.current_channel=current_channel
        self.tdms_file_name=tdms_file_name
        self.current_bkg=current_bkg
        self.current_channel_index=None

class DAQ_Navigation_Visu_process():
    def __init__(self, measurement_type=None,measurement_subtype=None,formula_params=None,formula=None,operation=None,do_operation=False,analysis_bounds=None):
        self.measurement_type = measurement_type
        self.measurement_subtype=measurement_subtype
        self.formula_params=formula_params
        self.formula=formula
        self.operation=operation
        self.do_operation=do_operation
        self.analysis_bounds=analysis_bounds




class DAQ_Navigation_Visu_Data():
    def __init__(self, xaxis1D=None, xaxis2D=None, yaxis2D=None, data1D=None,data_linear=None, data2D=None, Ncol=None, Nline=None):
        self.xaxis1D = xaxis1D
        self.xaxis2D=xaxis2D
        self.yaxis2D=yaxis2D
        self.data1D=data1D
        self.bkg=None
        self.data_linear=data_linear
        self.data2D=data2D
        
        self.Ncol=Ncol
        self.Nline=Nline
        self.reshape_types=["Linear seq.","Linear","Spiral","from coordinates"]

    def reshape(self,data,reshape_type):
        if reshape_type==self.reshape_types[0]:
            data_tmp=np.reshape(data,(self.Nline,self.Ncol))
        elif reshape_type==self.reshape_types[1]:
            data_tmp=np.reshape(data,(self.Nline,self.Ncol))
            for ind_col in range(self.Ncol):
                if mylib.odd_even(ind_col):
                    data_tmp[:,ind_col]=np.flipud(data_tmp[:,ind_col])
        elif reshape_type==self.reshape_types[2]:
            pass
        elif reshape_type==self.reshape_types[3]:
            data_tmp=self.reshape_from_coordinates()
        return data_tmp
            
    def reshape_from_coordinates(self):
        data_out=dict(blue=None,green=None,red=None)
        colors=['blue','green','red']
        if isinstance(self.data_linear,dict):
            for color in colors:
                if color in self.data_linear.keys():
                    if self.data_linear[color] is not None:
                        data_tmp=np.zeros((self.Nline,self.Ncol))
                        xaxis_unique=np.unique(self.xaxis2D)
                        yaxis_unique=np.unique(self.yaxis2D)
                        x_indexes=mylib.find_index(xaxis_unique,(self.xaxis2D).tolist())
                        y_indexes=mylib.find_index(yaxis_unique,(self.yaxis2D).tolist())
                        for ind in range(len(x_indexes)):
                            data_tmp[y_indexes[ind][0],x_indexes[ind][0]]=self.data_linear[color][ind]
                        data_out[color]=data_tmp
        else:
            data_tmp=np.zeros((self.Nline,self.Ncol))
            xaxis_unique=np.unique(self.xaxis2D)
            yaxis_unique=np.unique(self.yaxis2D)
            x_indexes=mylib.find_index(xaxis_unique,(self.xaxis2D).tolist())
            y_indexes=mylib.find_index(yaxis_unique,(self.yaxis2D).tolist())
            for ind in range(len(x_indexes)):
                data_tmp[y_indexes[ind][0],x_indexes[ind][0]]=self.data_linear[ind]
            data_out['blue']=data_tmp
        
        return data_out




class DAQ_Navigation_process_analysis(QObject):
    status_sig = pyqtSignal(str)
    data_process_sig = pyqtSignal(list)
    curve_fitting_sig= pyqtSignal(list)
    progress_bar_sig=pyqtSignal(int)

    def __init__(self,selected_limits,tdms_file,channels,current_carto,current_group,GUI):
        super(DAQ_Navigation_process_analysis,self).__init__()
        self.selected_limits=selected_limits
        self.GUI=GUI
        self.tdms_file=tdms_file
        self.channels=channels
        self.current_carto=current_carto
        self.current_group=current_group

        self.mtype=self.GUI.measure_type_combo.currentText()
        self.msubtype=self.GUI.measure_subtype_combo.currentText()
        self.msub_ind=self.GUI.measure_subtype_combo.currentIndex()
        self.custom_formula=self.GUI.formula_edit.toPlainText()
        self.custom_parameters=self.GUI.variables_edit.text()
        self.custom_parameters_number=len(self.custom_parameters.split(","))
        self.do_operation=self.GUI.do_operation_cb.isChecked()
        self.operation_formula=self.GUI.operation_edit.toPlainText()
        self.apply_bkg=self.GUI.apply_bkg_check.isChecked()
        self.bkg_type=self.GUI.bkg_type.currentText()
        self.Tree=self.GUI.Tree
        self.bkg_whole=self.GUI.set_whole_as_bkg_cb.isChecked()
        self.bkg_name=self.GUI.background_edit.text()
        self.do_zero_bkg=self.GUI.do_zero_cb.isChecked()

        self.do_despiking=self.GUI.remove_spikes_cb.isChecked()
        self.despiking_Nloop=self.GUI.despiked_Nloop_sb.value()
        self.threshold=self.GUI.threshold_sb.value()
        self.width_average=self.GUI.despiked_width_average_sb.value()
        self.width_spikes=self.GUI.despiked_width_spikes_sb.value()
        

    def __del__(self):
        pass
       
    def thresholding(self,data,threshold,width_average,width_spike):
        indices=[]
        mask=[]
        data_out=np.copy(data)
        for ind in range(len(data)):
            if data[ind]>threshold*np.mean(np.mean(data[int(ind-width_average/2):int(ind-width_spike/2)])+np.mean(data[int(ind+width_spike/2):int(ind+width_average/2)])):
                indices.append(ind)
                mask.append(True)
            else:
                mask.append(False)
        data_masked=np.ma.array(data.tolist(),mask=mask)
        for ind in indices:
            data_out[ind]=data_masked[np.rint(ind-width_average/2):np.rint(ind+width_average)].mean()
        return data_out,indices

    def gaussian_func(self,x,amp,dx,x0,offset):
        return amp * np.exp(-2*np.log(2)*(x-x0)**2/dx**2) + offset

    def laurentzian_func(self,x,alpha,gamma,x0,offset):
        return alpha/np.pi * 1/2*gamma /((x-x0)**2+(1/2*gamma)**2) + offset

    def decaying_func(self,x,N0,gamma,offset):
        return N0 * np.exp(-gamma*x)+offset

    def custom_func(self,x,*args):
        from math import exp, acos, acosh, asin, asinh, atan, atan2, atanh, cos, cosh, erf, exp, factorial, log, log10, pi, pow, sin, sinh, sqrt, tan, tanh 
        params=self.custom_parameters.split(",")
        globals_dict=dict([("x",x),('exp',exp),('acos',acos), ('acosh',acosh),('asin',asin), ('asinh',asinh),
                           ('atan',atan),('atan2',atan2),('atanh',atanh),('cos',cos),('cosh',cosh),('erf',erf),
                           ('exp',exp), ('factorial',factorial),('log',log),('log10',log10),('pi',pi),('pow',pow),('sin',sin),('sinh',sinh),
                           ('sqrt',sqrt),('tan',tan),('tanh',tan)])
        for ind,param in enumerate(params):
            globals_dict.update(dict([(param,args[ind])]))
        result=np.zeros_like(x)
        for ind,xscal in enumerate(x):
            globals_dict["x"]=xscal
            result[ind]=eval(self.custom_formula,globals_dict)
                
        return result
        
    def update_measurement(self,xmin,xmax,xaxis,data1D,mtype,msubtype,msub_ind):
        try:
            boundaries=mylib.find_index(xaxis,[xmin,xmax])
            sub_xaxis=xaxis[boundaries[0][0]:boundaries[1][0]]
            sub_data=data1D[boundaries[0][0]:boundaries[1][0]]
            mtypes=Measurement_type.names(Measurement_type)
            if mtype==mtypes[0]:#"Cursor Intensity Integration":
                if msubtype=="sum":
                    result_measurement=np.sum(sub_data)
                elif msubtype=="mean":
                    result_measurement=np.mean(sub_data)
                elif msubtype=="std":
                    result_measurement=np.std(sub_data)
                else:
                    result_measurement=0
                self.curve_fitting_sig.emit([False])
            elif mtype==mtypes[1]:#"Max":
                result_measurement=np.max(sub_data)
                self.curve_fitting_sig.emit([False])
            elif mtype==mtypes[2]:#"Min":
                result_measurement=np.min(sub_data)
                self.curve_fitting_sig.emit([False])
            elif mtype==mtypes[3]:#"Gaussian Fit":
                offset=np.min(sub_data)
                amp=np.max(sub_data)-np.min(sub_data)
                m=mylib.my_moment(sub_xaxis,sub_data)
                p0=[amp,m[1],m[0],offset]
                popt, pcov = curve_fit(self.gaussian_func, sub_xaxis, sub_data,p0=p0)
                self.curve_fitting_sig.emit([True,sub_xaxis,self.gaussian_func(sub_xaxis,*popt)])
                result_measurement=popt[msub_ind]
            elif mtype==mtypes[4]:#"Lorentzian Fit":
                offset=np.min(sub_data)
                amp=np.max(sub_data)-np.min(sub_data)
                m=mylib.my_moment(sub_xaxis,sub_data)
                p0=[amp,m[1],m[0],offset]
                popt, pcov = curve_fit(self.laurentzian_func, sub_xaxis, sub_data,p0=p0)
                self.curve_fitting_sig.emit([True,sub_xaxis,self.laurentzian_func(sub_xaxis,*popt)])
                
                if msub_ind==4:#amplitude
                    result_measurement=popt[0]*2/(np.pi*popt[1])#2*alpha/(pi*gamma)
                else:
                    result_measurement=popt[msub_ind]
            elif mtype==mtypes[5]:#"Exponential Decay Fit":
                offset=min([sub_data[0],sub_data[-1]])
                N0=np.max(sub_data)-offset
                polynome=np.polyfit(sub_xaxis,-np.log((sub_data-0.99*offset)/N0),1)
                p0=[N0,polynome[0],offset]
                popt, pcov = curve_fit(self.decaying_func, sub_xaxis, sub_data,p0=p0)
                self.curve_fitting_sig.emit([True,sub_xaxis,self.decaying_func(sub_xaxis,*popt)])
                result_measurement=popt[msub_ind]
            #elif mtype=="Custom Formula":
            #    #offset=np.min(sub_data)
            #    #amp=np.max(sub_data)-np.min(sub_data)
            #    #m=mylib.my_moment(sub_xaxis,sub_data)
            #    #p0=[amp,m[1],m[0],offset]
            #    popt, pcov = curve_fit(self.custom_func, sub_xaxis, sub_data,p0=[140,750,50,15])
            #    self.curve_fitting_sig.emit([sub_xaxis,self.gaussian_func(sub_xaxis,*popt)])
            #    result_measurement=popt[msub_ind]
            else:
                result_measurement=0
            status=""
            if self.do_operation:
                x=result_measurement
                #result_measurement=eval(self.operation_formula,dict([("x",result_measurement)]))
                result_measurement=eval(self.operation_formula)
            
            return (status,result_measurement)
        except Exception as e:
            result_measurement=0
            status=str(e)
            return (status,result_measurement)

    def do_process(self):
        try:
            self.status_sig.emit("Processing")
            xaxis_2D=self.tdms_file.channel_data(self.current_carto+"_scan","Xaxis")
            yaxis_2D=self.tdms_file.channel_data(self.current_carto+"_scan","Yaxis")
            obj=self.tdms_file.object(self.current_carto+"_scan","Data2D")
            Nline=obj.property('Nline')
            Ncol=obj.property('Ncol')
        
            channel_names=[channel.channel for channel in self.tdms_file.group_channels(self.current_group)]
            data_linear=dict(blue=None,green=None,red=None)
            colors=["blue","green","red"]
            N=len(self.channels)
            for color in colors:
                if self.selected_limits[color] is not None:
                    data_linear[color]=[]
                    for ind,channel in  enumerate(self.channels):
                        self.progress_bar_sig.emit(int(ind/(N-1)*100))
                        QtCore.QCoreApplication.processEvents()
                        self.current_channel=channel
                        self.xaxis=self.tdms_file.channel_data(self.current_group, "Xaxis")
                        data1D=self.tdms_file.channel_data(self.current_group, self.current_channel)
                        if self.apply_bkg:

                            if not(self.bkg_whole):
                                
                                if "Bkg" in channel_names:
                                    bkg=self.tdms_file.channel_data(self.current_group, "Bkg")
                            else:
                                if not(self.bkg_name==""):
                                    parent_item=self.Tree.findItems(self.bkg_name+"_Det1D",Qt.MatchExactly| Qt.MatchRecursive,0)[0]
                                    for ind_child in range(parent_item.childCount()):
                                        if parent_item.child(ind_child).text(0)=='CH00':
                                            bkg_item=parent_item.child(ind_child).child(ind)
                                            break
                                    channel_name=bkg_item.text(0)
                                    bkg=self.tdms_file.channel_data(self.bkg_name+"_Det1D", channel_name)

                            if self.bkg_type=="Sub.":
                                data1D=data1D-bkg
                            elif self.bkg_type=="Ratio":
                                data1D=data1D/bkg
                            if self.do_zero_bkg:
                                data1D=data1D*(data1D>=0)
                        if self.do_despiking:
                            for ind in range(self.despiking_Nloop):
                                data1D,indices=self.thresholding(data1D,self.threshold,self.width_average,self.width_spikes)
                                

                        xmin=self.selected_limits[color][0]
                        xmax=self.selected_limits[color][1]
                        (status,result_measurement)=self.update_measurement(xmin,xmax,self.xaxis,data1D,self.mtype,self.msubtype,self.msub_ind)
                        data_linear[color].append(result_measurement)
                    data_linear[color]=np.array(data_linear[color])
            self.data_process_sig.emit([xaxis_2D,yaxis_2D,data_linear,Nline,Ncol])
            
        except Exception as e:
            status=str(e)
            self.status_sig.emit(status)
            
            






if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv);
    MainWindow=QtWidgets.QMainWindow();
    prog = DAQ_Navigation_Visu(MainWindow);
    MainWindow.show();
    #prog.Load_TDMS_fun("D:\\Data\\2016\\Vincent\\PL SiNCs_NWs\\test.tdms")
    sys.exit(app.exec_());
    