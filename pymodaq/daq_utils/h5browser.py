from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QByteArray, QBuffer
import sip
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.daq_utils.tree_layout.tree_layout_main import Tree_layout
from pymodaq.daq_utils.daq_utils import h5tree_to_QTree, select_file, getLineInfo, capitalize

import sys
import tables
import numpy as np
from pymodaq.daq_utils.plotting.viewerND.viewerND_main import ViewerND
from collections import OrderedDict
from pathlib import Path
import warnings
import os
from copy import deepcopy

class H5Browser(QtWidgets.QWidget,QObject):
    data_node_signal=pyqtSignal(str) # the path of a node where data should be monitored, displayed...whatever use from the caller 
    status_signal=pyqtSignal(str)

    def __init__(self,parent,h5file=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(H5Browser,self).__init__()
        if not (isinstance(parent, QtWidgets.QWidget) or isinstance(parent, QtWidgets.QMainWindow)):
            raise Exception('no valid parent container, expected a QWidget or a QMainWindow')

        self.h5file=None


        if isinstance(parent, QtWidgets.QMainWindow):
            self.main_window = parent
            self.parent = QtWidgets.QWidget()
            self.main_window.setCentralWidget(self.parent)
        else:
            self.main_window = None
            self.parent = parent

        self.ui = QObject()  # the user interface
        self.set_GUI()

        self.load_file(h5file)

        self.ui.h5file_tree.ui.Open_Tree.click()



    def add_comments(self):
        try:
            item = self.ui.h5file_tree.ui.Tree.currentItem()
            self.current_node_path = item.text(2)
            node = self.h5file.get_node(item.text(2))
            if 'comments' in node._v_attrs:
                tmp = node._v_attrs['comments']
            else:
                tmp = ''
            text, res = QtWidgets.QInputDialog.getMultiLineText(None, 'Enter comments', 'Enter comments here:', tmp)
            if res and text != '':
                    node._v_attrs['comments'] = text
            self.h5file.flush()

        except Exception as e:
            self.status_signal.emit(getLineInfo() + str(e))

    def export_data(self):
        try:
            item = self.ui.h5file_tree.ui.Tree.currentItem()
            self.current_node_path = item.text(2)
            node = self.h5file.get_node(item.text(2))
            if 'ARRAY' in node._v_attrs['CLASS']:
                data = node.read()
                if isinstance(data, np.ndarray):
                    file = select_file(save=True, ext='txt')
                    if file != '':
                        np.savetxt(file, data, '%.6e', '\t')
            elif 'GROUP' in node._v_attrs['CLASS']:
                children_names = list(node._v_children)
                data = []
                header = []
                for subnode_name in node._v_children:
                    subnode = node._f_get_child(subnode_name)
                    if 'ARRAY' in subnode._v_attrs['CLASS']:
                        if len(subnode.shape) == 1:
                            data.append(subnode.read())
                            header.append(subnode_name)

                file = select_file(save=True, ext='txt')
                if file != '':
                    np.savetxt(file, np.array(data).T, '%.6e', '\t', header='\t'.join(header))



        except Exception as e:
            self.status_signal.emit(getLineInfo() + str(e))

    def load_file(self, h5file=None):
        if h5file is None:
            h5file=str(select_file(start_path=None,save=False, ext='h5'))
        if isinstance(h5file, str) or isinstance(h5file, Path):
            h5file=tables.open_file(str(h5file), 'a')
        elif isinstance(h5file, tables.File):
            pass
        else:
            raise Exception('not a valid h5 file or path to a h5 file')
        self.h5file=h5file

        self.populate_tree()

    def save_file(self):

        filename=select_file(None, save=True, ext='h5')
        self.h5file.copy_file(str(filename))

    def quit_fun(self):
        """
        """
        try:
            if self.h5file is not None:
                self.h5file.flush()
                if self.h5file.isopen:
                    self.h5file.close()

            self.parent.close()

        except Exception as e:
            pass

    def create_menu(self):
        """

        """
        self.menubar = self.main_window.menuBar()

        #%% create Settings menu
        self.file_menu=self.menubar.addMenu('File')
        load_action=self.file_menu.addAction('Load file')
        load_action.triggered.connect(lambda: self.load_file(None))
        save_action=self.file_menu.addAction('Save file')
        save_action.triggered.connect(self.save_file)

        self.file_menu.addSeparator()
        quit_action=self.file_menu.addAction('Quit')
        quit_action.triggered.connect(self.quit_fun)

        #help menu
        help_menu=self.menubar.addMenu('?')
        action_about=help_menu.addAction('About')
        action_about.triggered.connect(self.show_about)
        action_help=help_menu.addAction('Help')
        action_help.triggered.connect(self.show_help)
        action_help.setShortcut(QtCore.Qt.Key_F1)

    def show_about(self):
        splash_path = os.path.join(os.path.split(__file__)[0], 'splash.png')
        splash = QtGui.QPixmap(splash_path)
        self.splash_sc=QtWidgets.QSplashScreen(splash,QtCore.Qt.WindowStaysOnTopHint)
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage("PyMoDAQ version {:}\nModular Acquisition with Python\nWritten by Sébastien Weber".format(get_version()), QtCore.Qt.AlignRight, QtCore.Qt.white)


    def show_help(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://pymodaq.cnrs.fr"))

    def set_GUI(self):

        if self.main_window is not None:
            self.create_menu()

        layout=QtWidgets.QGridLayout()

        V_splitter=QtWidgets.QSplitter(Qt.Vertical)
        V_splitter2=QtWidgets.QSplitter(Qt.Vertical)
        H_splitter=QtWidgets.QSplitter(Qt.Horizontal)

        Form = QtWidgets.QWidget()
        #self.ui.h5file_tree = Tree_layout(Form,col_counts=2,labels=["Node",'Pixmap'])
        self.ui.h5file_tree = Tree_layout(Form, col_counts=1, labels=["Node"])
        self.ui.h5file_tree.ui.Tree.setMinimumWidth(300)
        self.ui.h5file_tree.ui.Tree.itemClicked.connect(self.show_h5_attributes)
        self.ui.h5file_tree.ui.Tree.itemDoubleClicked.connect(self.show_h5_data)

        self.export_action = QtWidgets.QAction("Export data as *.txt file")
        self.add_comments_action = QtWidgets.QAction("Add comments to this node")
        self.export_action.triggered.connect(self.export_data)
        self.add_comments_action.triggered.connect(self.add_comments)
        self.ui.h5file_tree.ui.Tree.addAction(self.export_action)
        self.ui.h5file_tree.ui.Tree.addAction(self.add_comments_action)

        V_splitter.addWidget(Form)
        self.ui.attributes_tree = ParameterTree()
        self.ui.attributes_tree.setMinimumWidth(300)
        V_splitter.addWidget(self.ui.attributes_tree)

        self.settings_raw = Parameter.create(name='Param_raw', type='group')
        self.ui.attributes_tree.setParameters(self.settings_raw, showTop=False)

        H_splitter.addWidget(V_splitter)
        self.pixmap_widget=QtWidgets.QWidget()
        self.pixmap_widget.setMaximumHeight(100)
        V_splitter2.addWidget(self.pixmap_widget)
        self.ui.settings_tree=ParameterTree()
        self.ui.settings_tree.setMinimumWidth(300)
        V_splitter2.addWidget(self.ui.settings_tree)
        self.ui.text_list=QtWidgets.QListWidget()


        V_splitter2.addWidget(self.ui.text_list)



        H_splitter.addWidget(V_splitter2)
        
        form_viewer=QtWidgets.QWidget()
        self.hyperviewer=ViewerND(form_viewer)
        H_splitter.addWidget(form_viewer)


        layout.addWidget(H_splitter)
        self.parent.setLayout(layout)


        self.settings=Parameter.create(name='Param', type='group')
        self.ui.settings_tree.setParameters(self.settings, showTop=False)

    def show_h5_attributes(self,item,col):
        """

        """
        try:
            self.current_node_path=item.text(2)
            node=self.h5file.get_node(item.text(2))
            attrs=node._v_attrs
            attrs_names=attrs._f_list('all')
            attr_dict=OrderedDict([])
            for attr in attrs_names:
                #if attr!='settings':
                attr_dict[attr]=attrs[attr]
            for child in self.settings_raw.children():
                child.remove()
            params = []
            for attr in attr_dict:
                params.append({'title': attr, 'name': attr, 'type': 'str', 'value': attr_dict[attr], 'readonly': True})

            self.settings_raw.addChildren(params)

            if 'settings' in attrs:
                if attrs['settings'] != '':
                    for child in self.settings.children():
                        child.remove()
                    QtWidgets.QApplication.processEvents() #so that the tree associated with settings updates
                    params=custom_tree.XML_string_to_parameter(attrs.settings.decode())
                    self.settings.addChildren(params)
            if 'scan_settings' in attrs:
                if attrs['scan_settings'] != '':
                    params=custom_tree.XML_string_to_parameter(attrs.scan_settings.decode())
                    self.settings.addChildren(params)
            pixmaps=[]
            for attr in attrs_names:
                if 'pixmap' in attr:
                    pixmaps.append(attrs[attr])
            if pixmaps==[]:
                self.pixmap_widget.setVisible(False)
            else:
                self.pixmap_widget.setVisible(True)
                self.show_pixmaps(pixmaps)

        except Exception as e:
            self.status_signal.emit(getLineInfo()+str(e))

    def show_pixmaps(self,pixmaps=[]):
        if self.pixmap_widget.layout() is None:
            layout=QtWidgets.QHBoxLayout()
            self.pixmap_widget.setLayout(layout)
        while 1:
            child=self.pixmap_widget.layout().takeAt(0)
            if not child:
                break
            child.widget().deleteLater()
            QtWidgets.QApplication.processEvents()


        labs=[]
        for pix in pixmaps:
            buff=QtCore.QBuffer()
            buff.open(QtCore.QIODevice.WriteOnly)
            buff.write(pix)
            dat=buff.data()
            pixmap=QtGui.QPixmap()
            pixmap.loadFromData(dat,'PNG')
            labs.append(QtWidgets.QLabel())
            labs[-1].setPixmap(pixmap)
            self.pixmap_widget.layout().addWidget(labs[-1])

        

    def show_h5_data(self,item,col):
        """
        """
        try:
            self.current_node_path=item.text(2)
            self.show_h5_attributes(item,col)
            node=self.h5file.get_node(item.text(2))
            self.data_node_signal.emit(node._v_pathname)
            if 'ARRAY' in node._v_attrs['CLASS']:
                data = node.read()
                nav_axes = []
                axes = dict([])
                x_axis = None
                y_axis = None
                nav_x_axis = None
                nav_y_axis = None
                if isinstance(data, np.ndarray):
                    data = np.squeeze(data)
                    if 'type' in node._v_attrs:
                        if 'data' in node._v_attrs['type'] or 'channel' in node._v_attrs['type'].lower():
                            parent_path = node._v_parent._v_pathname
                            children = list(node._v_parent._v_children)

                            if 'data_dimension' not in node._v_attrs: #for backcompatibility
                                data_dim = node._v_attrs['data_type']
                            else:
                                data_dim = node._v_attrs['data_dimension']

                            tmp_axes = ['x_axis', 'y_axis']
                            for ax in tmp_axes:
                                if capitalize(ax) in children:
                                    axis_node = self.h5file.get_node(parent_path+'/{:s}'.format(capitalize(ax)))
                                    axes[ax] = dict(data=axis_node.read())
                                    if 'units' in axis_node._v_attrs:
                                        axes[ax]['units'] = axis_node._v_attrs['units']
                                    if 'label' in axis_node._v_attrs:
                                        axes[ax]['label'] = axis_node._v_attrs['label']
                                else:
                                    axes[ax] = dict(units='', label='')


                            if 'scan_type' in node._v_attrs:
                                scan_type = node._v_attrs['scan_type'].lower()
                                if scan_type == 'scan1d' or scan_type == 'scan2d':
                                    scan_path = node._v_parent._v_parent._v_parent._v_parent._v_pathname
                                    children = list(node._v_parent._v_parent._v_parent._v_parent._v_children)

                                    tmp_nav_axes = ['x_axis', 'y_axis']
                                    if scan_type == 'scan1d' or scan_type == 'scan2d':
                                        nav_axes = []
                                        for ind_ax, ax in enumerate(tmp_nav_axes):
                                            if 'Scan_{:s}'.format(ax) in children:
                                                nav_axes.append(ind_ax)
                                                axis_node = self.h5file.get_node(scan_path + '/Scan_{:s}'.format(ax))
                                                axes['nav_{:s}'.format(ax)] = dict(data=np.unique(axis_node.read()))
                                                if axes['nav_{:s}'.format(ax)]['data'].shape[0] != data.shape[ind_ax]:  #could happen in case of linear back to start type of scan
                                                    tmp_ax=[]
                                                    for ix in axes['nav_{:s}'.format(ax)]['data']:
                                                        tmp_ax.extend([ix, ix])
                                                        axes['nav_{:s}'.format(ax)]=dict(data=np.array(tmp_ax))

                                                if 'units' in axis_node._v_attrs:
                                                    axes['nav_{:s}'.format(ax)]['units'] = axis_node._v_attrs['units']
                                                if 'label' in axis_node._v_attrs:
                                                    axes['nav_{:s}'.format(ax)]['label'] = axis_node._v_attrs['label']
                        elif 'axis' in node._v_attrs['type']:
                            axis_node = node
                            axes['y_axis'] = dict(data=axis_node.read())
                            if 'units' in axis_node._v_attrs:
                                axes['y_axis']['units'] = axis_node._v_attrs['units']
                            if 'label' in axis_node._v_attrs:
                                axes['y_axis']['label'] = axis_node._v_attrs['label']
                            axes['x_axis'] = dict(data=np.linspace(0, axis_node.shape[0]-1, axis_node.shape[0]),
                                                  units='pxls',
                                                  label='')
                    self.hyperviewer.show_data(deepcopy(data), nav_axes = nav_axes, **deepcopy(axes))
                    self.hyperviewer.init_ROI()
                elif isinstance(data, list):
                    if isinstance(data[0], str):
                        self.ui.text_list.clear()
                        for txt in node.read():
                            self.ui.text_list.addItem(txt)
            

        except Exception as e:
            self.status_signal.emit(getLineInfo()+str(e))

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
                base_tree_item,pixmap_items=h5tree_to_QTree(self.h5file,base_node)
                self.ui.h5file_tree.ui.Tree.addTopLevelItem(base_tree_item)
                self.add_widget_totree(pixmap_items)

                
        except Exception as e:
            self.status_signal.emit(getLineInfo()+str(e))

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




def browse_data(fname=None, ret_all = False):
    """
        | Browse data present in any h5 file, when user has selected the one,
        |
        |  press OK and returns the selected data

        =============== ====================================    ==================================================
        **Parameters**   **Type**                                **Description**

            *fname*         str, Path object                        The path as a Path object or string
        =============== ====================================    ==================================================
        =============== ====================================    ==================================================
        **Returns**     **Type**                                **Description**

            *data*         ndarray                                Data as a numpy array
        =============== ====================================    ==================================================


    """
    if fname is None:
        fname=str(select_file(start_path=None,save=False, ext='h5'))
    
    if type(fname)!=str:
        try:
            fname=str(fname)
        except:
            raise Exception('filename in browse data is not valid')
    if fname != '':
        (root,ext)=os.path.splitext(fname)
        if not( 'h5' in ext or 'hdf5' in ext):
            warnings.warn('This is not a PyMODAQ h5 file, there could be issues',Warning)

        with tables.open_file(fname) as h5file:
            dialog=QtWidgets.QDialog()
            dialog.setWindowTitle('Select a data node in the tree')
            vlayout=QtWidgets.QVBoxLayout()
            form= QtWidgets.QWidget()
            browser=H5Browser(form,h5file)

            vlayout.addWidget(form)
            dialog.setLayout(vlayout)
            buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)



            dialog.setLayout(vlayout)
            buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)

            buttonBox.addButton('OK',buttonBox.AcceptRole)
            buttonBox.accepted.connect(dialog.accept)
            buttonBox.addButton('Cancel',buttonBox.RejectRole)
            buttonBox.rejected.connect(dialog.reject)

            vlayout.addWidget(buttonBox)
            dialog.setWindowTitle('Select data to be loaded')
            res=dialog.exec()

            if res==dialog.Accepted:
                node_path=browser.current_node_path
                data=h5file.get_node(node_path).read()#save preset parameters in a xml file
            else:
                data=None
                node_path = None
        if ret_all:
            return data, fname, node_path
        else:
            return data
    return None, '', ''

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    #h5file=tables.open_file('C:\\Users\\Weber\\Labo\\Programmes Python\\pymodaq\\daq_utils\\test.h5')
    prog = H5Browser(win)
    win.show()
    sys.exit(app.exec_())
