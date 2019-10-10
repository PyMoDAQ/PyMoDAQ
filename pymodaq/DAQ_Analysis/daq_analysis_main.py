from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QByteArray

import sys
import pymodaq
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.daq_utils import select_file


from collections import OrderedDict
import numpy as np

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.daq_utils.tree_layout.tree_layout_main import Tree_layout
import pymodaq.daq_utils.daq_utils as utils
import os
from easydict import EasyDict as edict
from pyqtgraph.dockarea import DockArea, Dock
import tables



class DAQ_Analysis(QtWidgets.QWidget,QObject):
    """

        ======================== =========================================
        **Attributes**            **Type**

        *dockarea*                instance of pyqtgraph.DockArea
        *mainwindow*              instance of pyqtgraph.DockArea
        *title*                   string
        *waitime*                 int
        *h5file*                  instance class File from tables module
        *loaded_data*             2D array
        *loaded_data_scan_type*   string
        *x_axis*                  float array
        *y_axis*                  float array
        *data_buffer*             list of data
        *ui*                      QObject
        ======================== =========================================

        Raises
        ------
        parent Exception
            If parent argument is None in constructor abort

        See Also
        --------
        set_GUI


        References
        ----------
        PyQt5, pyqtgraph, QtWidgets, QObject

    """
    command_DAQ_signal=pyqtSignal(list)
    log_signal=pyqtSignal(str)

    def __init__(self,parent=None,title=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_Analysis,self).__init__()
        if parent is None:
            raise Exception('no valid parent container, expected dockarea')
            # parent=DockArea()
            # exit(0)

        self.dockarea=parent
        self.mainwindow=parent.parent()


        if title is None:
            title='DAQ_Analysis'
        self.title=title
        self.mainwindow.setWindowTitle(self.title)

        self.wait_time=2000

        self.h5file=None
        self.loaded_data=None
        self.loaded_data_scan_type=None
        self.x_axis=None
        self.y_axis=None

        self.data_buffer=[] #convenience list to store data to be displayed

        self.ui=QObject() #the user interface
        self.set_GUI()

    def set_GUI(self):
        """
            Create the graphic interface of the h5 file analyser, including:
                * *h5 file dock* : QtreeWidget (custom instance of Tree_layout) showing the contents of the h5 file
                * *status bar* : the top_down information bar
                * *tree_dock* : The QTree viewer
                * *1D viewer dock* : the preview window of 1D data
                * *2D viewer dock* : the preview window of 2D data
                * *Navigator viewer dock* : the global navigator graphic interface

            See Also
            --------
            show_h5_attributes, show_h5_data, daq_utils.custom_parameter_tree.Table_custom, update_viewer_data
        """
        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # h5 file dock
        V_splitter=QtWidgets.QSplitter(Qt.Vertical)
        H_splitter=QtWidgets.QSplitter(Qt.Horizontal)

        Form = QtWidgets.QWidget()
        self.ui.h5file_tree = Tree_layout(Form,col_counts=2,labels=["Node",'Pixmap'])
        self.ui.h5file_tree.ui.Tree.setMinimumWidth(250)
        self.ui.h5file_tree.ui.Tree.itemClicked.connect(self.show_h5_attributes)
        self.ui.h5file_tree.ui.Tree.itemDoubleClicked.connect(self.show_h5_data)
        V_splitter.addWidget(Form)
        self.ui.attributes_table=custom_tree.Table_custom()
        V_splitter.addWidget(self.ui.attributes_table)
        H_splitter.addWidget(V_splitter)
        self.ui.settings_tree=ParameterTree()
        self.ui.settings_tree.setMinimumWidth(300)
        H_splitter.addWidget(self.ui.settings_tree)
        self.ui.menubar=self.mainwindow.menuBar()
        self.create_menu(self.ui.menubar)

        #%%create status bar
        self.ui.statusbar=QtWidgets.QStatusBar()
        self.ui.statusbar.setMaximumHeight(25)


        #%% create tree dock
        file_dock = Dock("File data", size=(1, 1), autoOrientation=False)     ## give this dock the minimum possible size
        file_dock.setOrientation('vertical')
        file_dock.addWidget(H_splitter)
        file_dock.addWidget(self.ui.statusbar)
        self.settings=Parameter.create(name='Param', type='group')
        self.ui.settings_tree.setParameters(self.settings, showTop=False)

        ##%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        ##% 1D viewer Dock
        viewer1D_widget=QtWidgets.QWidget()
        self.ui.viewer1D=Viewer1D(viewer1D_widget)
        dock1D=Dock('Viewer1D')
        dock1D.addWidget(viewer1D_widget)


        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        #% 2D viewer Dock
        viewer2D_widget=QtWidgets.QWidget()
        self.ui.viewer2D=Viewer2D(viewer2D_widget)
        dock2D=Dock('Viewer2D')
        dock2D.addWidget(viewer2D_widget)

        ##%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        ##% Navigator viewer Dock
        navigator1D_widget=QtWidgets.QWidget()
        self.ui.navigator1D=Viewer1D(navigator1D_widget)
        self.ui.navigator1D.ui.crosshair.crosshair_dragged.connect(self.update_viewer_data)
        self.ui.navigator1D.ui.crosshair_pb.click()
        navigator2D_widget=QtWidgets.QWidget()
        self.ui.navigator2D=Viewer2D(navigator2D_widget)
        self.ui.navigator2D.crosshair_dragged.connect(self.update_viewer_data) #export scaled position in conjonction with 2D scaled axes
        self.ui.navigator2D.ui.crosshair_pb.click()
        dock_nav=Dock('Navigator')
        dock_nav.addWidget(navigator1D_widget)
        dock_nav.addWidget(navigator2D_widget,1,0)

        self.dockarea.addDock(file_dock,'top')
        self.dockarea.addDock(dock2D,'right',file_dock)
        self.dockarea.addDock(dock1D,'bottom',dock2D)
        self.dockarea.addDock(dock_nav,'right',dock2D)

    def update_status(self,txt,wait_time=1000,log=''):
        """
            | Update the statut bar showing a Message with a delay of wait_time ms (1s by default)

            ================ ======== ===========================
            **Parameters**   **Type**     **Description**

             *txt*            string   the text message to show

             *wait_time*      int      the delay time of showing
            ================ ======== ===========================

        """
        self.ui.statusbar.showMessage(txt,wait_time)
        if log=='log':
            self.log_signal.emit(txt)


    def Quit_fun(self):
        """
            |
            | close the current instance of DAQ_Analysis

        """
        if self.h5file is not None:
            if self.h5file.isopen:
                self.h5file.close()
        self.mainwindow.close()

    def create_menu(self,menubar):
        """
             Set the filemenu structure with three elements splited by a separator at the 2nd position :
                * *open DAQ_scan file* : calling the do_load intern method
                * *close h5 file*      : calling the close_h5 intern method
                * *Quit*               : calling the quit_fun intern method

            ================ =============================================== ====================================
             **Parameters**           **Type**                                      **Description**

             *menubar*        instance of pyqtgraph.DockArea menuBar object   the generic menuBar object of menu
            ================ =============================================== ====================================

            See Also
            --------
            do_load, close_h5, quit_fun
        """
        file_menu=menubar.addMenu('File')
        open_action=file_menu.addAction("Open DAQ_Scan file")
        open_action.triggered.connect(self.do_load)
        close_action=file_menu.addAction("close h5 file")
        close_action.triggered.connect(self.close_h5)
        file_menu.addSeparator()
        quit_action=file_menu.addAction("Quit")
        quit_action.triggered.connect(self.Quit_fun)

    def close_h5(self):
        """
            | close the loaded h5 file if exists with clearing the ui-h5 tree structure

        """
        if self.h5file is not None:
            if self.h5file.isopen:
                self.h5file.close()
        self.ui.h5file_tree.ui.Tree.clear()

#should be one function from here
    def do_load(self,check_state):
        """
            | Call the loading h5 file procedure

            ================ ========= =============================
            **Parameters**   **Type**      **Description**

            *check_state*     none       not used
            ================ ========= =============================

            See Also
            --------
            load_h5_file
        """
        self.load_h5_file()

    def load_h5_file(self,path=None):
        """
            | Load the specific h5 file calling the open_h5_file procedure

            ================ ============ =======================================
            **Parameters**    **Type**            **Description**

             *path*           string        the current path to the file to load
            ================ ============ =======================================

            See Also
            --------
            open_h5_file, update_status, daq_utils.select_file
        """
        try:
            filename=select_file(start_path=path,save=False,ext='h5')
            if filename is not "":
                self.open_h5_file(filename)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def read_external_h5file(self,h5file):
        try:
            self.h5file=h5file
            self.populate_tree()
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def open_h5_file(self,filename):
        """
            | Store the h5 file from the tables attributes and populate tree with raw h5 data

            =============== ========== =============================
            **Parameters**   **Type**         **Description**

             *filename*      string     name of the h5 file to load
            =============== ========== =============================

            See Also
            --------
            populate_tree, update_status
        """
        try:
            self.h5file=tables.open_file(str(filename))
            self.populate_tree()
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)
#to here (see do_load.py)

    def populate_tree(self):
        """
            | Init the ui-tree and store data into calling the h5_tree_to_Qtree convertor method

            See Also
            --------
            h5tree_to_QTree, update_status
        """
        try:
            if self.h5file is not None:
                self.ui.h5file_tree.ui.Tree.clear()
                base_node=self.h5file.root
                base_tree_item,pixmap_items=utils.h5tree_to_QTree(self.h5file,base_node)
                self.ui.h5file_tree.ui.Tree.addTopLevelItem(base_tree_item)
                self.add_widget_totree(pixmap_items)

                
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def add_widget_totree(self,pixmap_items):
        
        for item in pixmap_items:
            widget=QtWidgets.QWidget()

            vLayout=QtWidgets.QVBoxLayout()
            label1D=QtWidgets.QLabel()
            bytes=QByteArray(item['node']._v_attrs['pixmap1D'])
            im1=QtGui.QImage.fromData(bytes)
            a=QtGui.QPixmap.fromImage(im1)
            label1D.setPixmap(a)

            label2D=QtWidgets.QLabel()
            bytes=QByteArray(item['node']._v_attrs['pixmap2D'])
            im2=QtGui.QImage.fromData(bytes)
            b=QtGui.QPixmap.fromImage(im2)
            label2D.setPixmap(b)

            vLayout.addWidget(label1D)
            VLayout.addwidget(label2D)
            widget.setLayout(vLayout)
            self.ui.h5file_tree.ui.Tree.setItemWidget(item['item'],1,widget)


    def show_h5_attributes(self,item,col):
        """
            | Show the h5 attribute using the intern tree structure and update settings and User Interface custom tree

            ================= ====================== ====================================
            **Parameters**      **Type**              **Description**

             *item*           tables Group instance   contain the root node of the tree

             *col*                                    not used
            ================= ====================== ====================================

            See Also
            --------
            daq_utils.custom_parameter_tree.XML_string_to_parameter, update_status
        """
        try:
            node=self.h5file.get_node(item.text(2))
            attrs=node._v_attrs
            attrs_names=attrs._f_list('all')
            attr_dict=OrderedDict([])
            for attr in attrs_names:
                if attr!='settings':
                    attr_dict[attr]=attrs[attr]
            self.ui.attributes_table.set_table_value(attr_dict)

            if hasattr(attrs,'settings'):
                for child in self.settings.children():
                    child.remove()
                QtWidgets.QApplication.processEvents() #so that the tree associated with settings updates
                params=custom_tree.XML_string_to_parameter(attrs.settings.decode())
                self.settings.addChildren(params)
                if hasattr(attrs,'scan_settings'):
                    params=custom_tree.XML_string_to_parameter(attrs.scan_settings.decode())
                    self.settings.addChildren(params)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)


    def show_h5_data(self,item,col):
        """
             Show the h5 data reading in the tree structure with update (if needed) of :
                * viewer 1D
                * viewer 2D
                * navigator 1D
                * navigator 2D

            =============== ====================== ===================================
            **Parameters**   **Type**               **Description**

             *item*          tables Group instance  contain the root node of the tree
             *col*                                  not used
            =============== ====================== ===================================

            See Also
            --------
            show_h5_attributes, set_axis, get_scan_parent_node, get_scan_parent_node,  update_viewer_data, update_status
        """
        try:
            self.data_buffer=[]
            self.show_h5_attributes(item,col)
            node=self.h5file.get_node(item.text(2))
            attrs=node._v_attrs
            attrs_names=attrs._f_list('all')
            if attrs.CLASS=='ARRAY' or attrs.CLASS=='CARRAY': #means there is data to be plotted
                if 'scan_type' not in attrs_names: #means one of the navigation axis or other type of data
                    self.loaded_data=node.read()
                    self.loaded_data_scan_type=None
                    shape=self.loaded_data.shape
                    if len(shape)==1:
                        self.ui.viewer1D.remove_plots()
                        self.ui.viewer1D.x_axis=None
                        self.ui.viewer1D.show_data([self.loaded_data])
                    elif len(shape)==2:
                        #self.ui.viewer2D.remove_plots()
                        self.ui.viewer2D.setImage(self.loaded_data)

                elif attrs.scan_type=='Scan1D':
                    self.loaded_data_scan_type=attrs.scan_type
                    scan_node=self.get_scan_parent_node(node)
                    if scan_node is None:
                        return
                    self.ui.navigator1D.parent.setVisible(True)
                    self.ui.navigator2D.parent.setVisible(False)
                    self.loaded_data=node.read()
                    shape=self.loaded_data.shape
                    self.nav_x_axis=self.set_axis(scan_node,'scan_x_axis_unique',self.loaded_data.shape[0])
                    self.nav_y_axis=[0]
                    self.ui.navigator1D.remove_plots()
                    self.ui.navigator1D.x_axis=self.nav_x_axis
                    if attrs.data_type=='0D':
                        self.ui.navigator1D.show_data([self.loaded_data])
                    elif attrs.data_type=='1D':
                        self.x_axis=self.set_axis(node._v_parent,'x_axis',self.loaded_data.shape[1])
                        self.ui.navigator1D.show_data([np.sum(self.loaded_data,axis=1)])
                    elif attrs.data_type=='2D':
                        self.x_axis=self.set_axis(node._v_parent,'x_axis',self.loaded_data.shape[2])
                        self.y_axis=self.set_axis(node._v_parent,'y_axis',self.loaded_data.shape[1])
                        self.ui.navigator1D.show_data([np.sum(self.loaded_data,axis=(1,2))])
                    else:
                        pass

                elif attrs.scan_type=='Scan2D':
                    self.loaded_data_scan_type=attrs.scan_type
                    scan_node=self.get_scan_parent_node(node)
                    if scan_node is None:
                        return
                    self.ui.navigator1D.parent.setVisible(False)
                    self.ui.navigator2D.parent.setVisible(True)
                    self.loaded_data=node.read()
                    self.nav_x_axis=self.set_axis(scan_node,'scan_x_axis_unique',self.loaded_data.shape[0])
                    self.nav_y_axis=self.set_axis(scan_node,'scan_x_axis_unique',self.loaded_data.shape[1])
                    self.ui.navigator2D.set_scaling_axes(
                        scaling_options=edict(scaled_xaxis=edict(label="x axis",units=None,offset=np.min(self.nav_x_axis),scaling=self.nav_x_axis[1]-self.nav_x_axis[0]),
                                            scaled_yaxis=edict(label="y axis",units=None,offset=np.min(self.nav_y_axis),scaling=self.nav_y_axis[1]-self.nav_y_axis[0])))
                    if attrs.data_type=='0D':
                        self.ui.navigator2D.setImage(self.loaded_data)
                    elif attrs.data_type=='1D':
                        self.x_axis=self.set_axis(node._v_parent,'x_axis',self.loaded_data.shape[2])
                        self.ui.navigator2D.setImage(np.sum(self.loaded_data,axis=2))
                    elif attrs.data_type=='2D':
                        self.x_axis=self.set_axis(node._v_parent,'x_axis',self.loaded_data.shape[3])
                        self.y_axis=self.set_axis(node._v_parent,'y_axis',self.loaded_data.shape[2])
                        self.ui.navigator2D.setImage(np.sum(self.loaded_data,axis=(2,3)))
                    else:
                        pass
                self.update_viewer_data(self.nav_x_axis[0],self.nav_y_axis[0])


            else:
                return
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def update_viewer_data(self,posx=0,posy=0):
        """
            | Update the viewer informations from an x/y given position and store data.
            | Ruled by the viewer type (0D,1D,2D)

            ================ ========= ==============================
            **Parameters**   **Type**        **Description**

             *posx*           int       the x position of the viewer

             *posy*           int       the y position of the viewer
            ================ ========= ==============================

            See Also
            --------
            update_status
        """
        try:
            if self.loaded_data is not None:
                shape=self.loaded_data
                scan_type=self.loaded_data_scan_type
                if scan_type=='Scan1D':
                    ind_x=utils.find_index(self.nav_x_axis,posx)[0][0]
                    data=self.loaded_data[ind_x]
                elif scan_type=='Scan2D':
                    ind_x=utils.find_index(self.nav_x_axis,posx)[0][0]
                    ind_y=utils.find_index(self.nav_y_axis,posy)[0][0]
                    data=self.loaded_data[ind_y,ind_x]

                if len(data.shape)==0: #means 0D data, plot on 1D viewer
                    self.data_buffer.append(data)
                    self.ui.viewer1D.show_data([np.array(self.data_buffer)])
                elif len(data.shape)==1: #means 1D data, plot on 1D viewer
                    self.ui.viewer1D.remove_plots()
                    self.ui.viewer1D.x_axis=self.x_axis
                    self.ui.viewer1D.show_data([data])
                elif len(data.shape)==2: #means 2D data, plot on 2D viewer
                    self.ui.viewer2D.set_scaling_axes(
                            scaling_options=edict(scaled_xaxis=edict(label="x axis",units=None,offset=np.min(self.x_axis),scaling=self.x_axis[1]-self.x_axis[0]),
                                                scaled_yaxis=edict(label="y axis",units=None,offset=np.min(self.y_axis),scaling=self.y_axis[1]-self.y_axis[0])))
                    self.ui.viewer2D.setImage(data)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)


    def set_axis(self,node,axis_type,Npts):
        """
            | Set axis values from node and a linspace regular distribution

            ================ ======================= ==========================================
            **Parameters**     **Type**                **Description**

             *node*           tables Group instance   the root node of the local treated tree
            ================ ======================= ==========================================

            Returns
            -------
            float array
                the computed values axis.

        """
        try:
            axis=node._f_get_child(axis_type).read()# try to load some data relative to the axis
        except:
            axis=np.linspace(0,Npts,Npts,endpoint=False)

        return axis

    def get_scan_parent_node(self,node):
        """
            | Get the root level node from the given node (if exists)

            ================ ===================== ==========================================
            **Parameters**    **Type**              **Description**

             *node*           tables Node instance   the root node of the local treated tree
            ================ ===================== ==========================================

            Returns
            -------
            Node instance
                root level node.
        """
        while 'Scan' not in node._v_name:
            node=node._v_parent
            if node._v_name=='/': #reached root level
                node=None
                break
        return node

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow();
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000,500)
    prog = DAQ_Analysis(area,title='DAQ_Analysis')
    win.show()
    prog.open_h5_file('C:\\Data\\2018\\20180212\\Dataset_20180212_000\\Dataset_20180212_000.h5')
    sys.exit(app.exec_())
