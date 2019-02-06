from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QByteArray, QBuffer
import sip
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.daq_utils.tree_layout.tree_layout_main import Tree_layout
from pymodaq.daq_utils.daq_utils import h5tree_to_QTree, select_file

import sys
import tables
import numpy as np
from pymodaq.daq_utils.plotting.viewerND.viewerND_main import ViewerND
from collections import OrderedDict

import warnings
import os

class H5Browser(QtWidgets.QWidget,QObject):
    data_node_signal=pyqtSignal(str) # the path of a node where data should be monitored, displayed...whatever use from the caller 
    status_signal=pyqtSignal(str)

    def __init__(self,parent,h5file=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(H5Browser,self).__init__()
        if type(parent) is not QtWidgets.QWidget:
            raise Exception('no valid parent container, expected a QWidget')

        self.parent=parent
        if h5file is None:
            h5file=str(select_file(start_path=None,save=False, ext='h5'))
        if type(h5file)==str:
            h5file=tables.open_file(h5file)
        elif type(h5file)==tables.File:
            pass
        else:
            raise Exception('not a valid h5 file or path to a h5 file')
        self.h5file=h5file

        self.ui=QObject() #the user interface
        self.set_GUI()

        self.populate_tree()

        self.ui.h5file_tree.ui.Open_Tree.click()

    def set_GUI(self):

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
        V_splitter.addWidget(Form)
        self.ui.attributes_table=custom_tree.Table_custom()
        V_splitter.addWidget(self.ui.attributes_table)

        
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
            self.ui.attributes_table.set_table_value(attr_dict)
            
            if 'settings' in attrs:
                for child in self.settings.children():
                    child.remove()
                QtWidgets.QApplication.processEvents() #so that the tree associated with settings updates
                params=custom_tree.XML_string_to_parameter(attrs.settings.decode())
                self.settings.addChildren(params)
            if 'scan_settings' in attrs:
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
            self.status_signal.emit(str(e))

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

                if isinstance(data, np.ndarray):
                    self.hyperviewer.show_data(node.read())
                elif isinstance(data, list):
                    if isinstance(data[0], str):
                        self.ui.text_list.clear()
                        for txt in node.read():
                            self.ui.text_list.addItem(txt)
            

        except Exception as e:
            self.status_signal.emit(str(e))

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
            self.status_signal.emit(str(e))

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




def browse_data(fname=None):
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

    (root,ext)=os.path.splitext(fname)
    if not( 'h5' in ext or 'hdf5' in ext):
        warnings.warn('This is not a PyMODAQ h5 file, there could be issues',Warning) 

    with tables.open_file(fname) as h5file:
        dialog=QtWidgets.QDialog()
        vlayout=QtWidgets.QVBoxLayout()
        form= QtWidgets.QWidget()
        browser=H5Browser(form,h5file)

        vlayout.addWidget(form)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog);



        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog);

        buttonBox.addButton('OK',buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel',buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Select data to be loaded')
        res=dialog.exec()

        if res==dialog.Accepted:
            path=browser.current_node_path
            data=h5file.get_node(path).read()#save preset parameters in a xml file
        else:
            data=None

    return data

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv);
    win = QtWidgets.QWidget()
    #h5file=tables.open_file('C:\\Users\\Weber\\Labo\\Programmes Python\\pymodaq\\daq_utils\\test.h5')
    prog = H5Browser(win)
    win.show()
    sys.exit(app.exec_())
