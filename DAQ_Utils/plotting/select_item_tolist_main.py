from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize
from PyQt5.QtWidgets import QAbstractItemView
import sys
from PyMoDAQ.DAQ_Utils.plotting.select_item_tolist_GUI import Ui_Form
from PyMoDAQ.DAQ_Utils.DAQ_enums import Items_Lockin_SR830


#class Select_item_tolist(Ui_Form,QObject):
#    updated_items=pyqtSignal(list)
#    def __init__(self,parent,items_list=[],preset_items=[]):
#        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
#        super(Select_item_tolist,self).__init__()
        
#        self.ui=Ui_Form()
#        self.ui.setupUi(parent)
#        self.ui.parent=parent

#        self.ui.item_list=custom_list_widget(self)
#        self.ui.horizontalLayout.addWidget(self.ui.item_list)
#        self.item_list=items_list
#        self.preset_items=preset_items

#        self.ui.items_cb.addItems(items_list)
#        self.ui.all_items_list.addItems(items_list)
#        self.ui.item_list.addItems(preset_items)

#        self.ui.add_item_pb.clicked.connect(self.add_item)
#        self.ui.remove_item_pb.clicked.connect(self.remove_item)
#        self.items=[item for item in preset_items]
  
#    def populate_items_cb(self,items):
#        self.ui.items_cb.clear()
#        self.ui.items.addItems(items)
#        self.ui.all_items_list.clear()
#        self.ui.all_items_list.addItems(items)

#    def ini_items(self,items_tot):
#        self.item_list=items_tot['all_items']
#        self.preset_items=items_tot['preset']
#        self.ui.items_cb.clear()
#        self.ui.item_list.clear()
#        self.ui.all_items_list.clear()
#        self.ui.items_cb.addItems(self.item_list)
#        self.ui.all_items_list.addItems(self.item_list)
#        self.ui.item_list.addItems(self.preset_items)
#        self.items=self.all_items_func()
            
#    def get_value(self):
#        return dict(all_items=self.item_list,preset=self.items)

#    def add_item(self):
        
#        items_str=self.all_items_func()
#        if not(self.ui.items_cb.currentText() in items_str):
#            self.ui.item_list.addItem(self.ui.items_cb.currentText())
#        self.items=self.all_items_func()
        

#    def remove_item(self):
#        self.ui.item_list.takeItem(self.ui.item_list.currentRow())
#        self.items=self.all_items_func()
        

#    def all_items_func(self):
#        Nitems=self.ui.item_list.count()
#        items_str=[]
#        for ind in range (Nitems):
#            items_str.append(self.ui.item_list.item(ind).text())
#        self.updated_items.emit(items_str)
#        return items_str

class custom_list_widget(QtWidgets.QListWidget):
     def __init__(self,parent,items_list=[],preset_items=[]):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(custom_list_widget,self).__init__()
        self.parent=parent
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setToolTip('list of scan items')

     def dropEvent(self,event):
        item_txt=event.source().currentItem().text()
        index_from=event.source().currentIndex().row()
        index_to=self.indexAt(event.pos()).row()
        
        if event.source()==self:
            if index_to>index_from:
                index_to=index_to
            if index_to<0:
                index_to=0
            if index_from==index_to:
                pass
            else:
                item=self.takeItem(index_from)
                self.insertItem(index_to,item.text())
            
        else:
           if item_txt not in self.parent.items:
                index=0
                index=self.indexAt(event.pos()).row()+1
                self.insertItem(index,item_txt)
                
        self.parent.items=self.parent.all_items_func()


#%%
class Select_item_tolist_simpler(QtWidgets.QWidget):
    updated_items=pyqtSignal(list)
    def __init__(self,items_list=[],preset_items=[]):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(Select_item_tolist_simpler,self).__init__()
        self.initUI()

        self.all_items=items_list
        self.preset_items=preset_items

        self.all_items_list.addItems(items_list)
        self.current_items_list.addItems(preset_items)
        self.current_items_list.itemDoubleClicked[QtWidgets.QListWidgetItem].connect(self.remove_item)
#        self.add_item_pb.clicked.connect(self.add_item)
#        self.remove_item_pb.clicked.connect(self.remove_item)
        self.items=[item for item in preset_items]


    def initUI(self):
        
        #self.setGeometry(300, 300, 300, 220)
        self.setWindowTitle('test')
        
        self.hor_layout_label=QtWidgets.QHBoxLayout()
        self.label1=QtWidgets.QLabel('Select from:')
        self.label2=QtWidgets.QLabel('Selected:')
        self.hor_layout_label.addWidget(self.label1)
        self.hor_layout_label.addWidget(self.label2)
        
        self.hor_layout=QtWidgets.QHBoxLayout()
        self.all_items_list=QtWidgets.QListWidget()
        self.all_items_list.setMaximumHeight(100)
        self.all_items_list.setDragEnabled(True)
        self.all_items_list.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.current_items_list=custom_list_widget(self)
        self.current_items_list.setMaximumHeight(100)
        self.hor_layout.addWidget(self.all_items_list)
        self.hor_layout.addWidget(self.current_items_list)
        
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addLayout(self.hor_layout_label)
        self.vbox.addLayout(self.hor_layout)
        
        self.setLayout(self.vbox)
        
  
    def populate_items_cb(self,items):
        self.ui.items_cb.clear()
        self.ui.items.addItems(items)
        self.ui.all_items_list.clear()
        self.ui.all_items_list.addItems(items)

    def ini_items(self,items_tot):
        self.all_items=items_tot['all_items']
        self.preset_items=items_tot['preset']
        self.all_items_list.clear()
        self.current_items_list.clear()
        self.all_items_list.addItems(self.all_items)
        self.current_items_list.addItems(self.preset_items)
        self.items=self.all_items_func()
            
    def get_value(self):
        return dict(all_items=self.all_items,preset=self.items)

    @pyqtSlot(QtWidgets.QListWidgetItem)
    def remove_item(self,item):
        self.current_items_list.takeItem(self.current_items_list.row(item))

        self.items=self.all_items_func()
        

    def all_items_func(self):
        Nitems=self.current_items_list.count()
        items_str=[]
        for ind in range (Nitems):
            items_str.append(self.current_items_list.item(ind).text())
        self.updated_items.emit(items_str)
        
        return items_str







if __name__ == '__main__':
    items=Items_Lockin_SR830.names(Items_Lockin_SR830);
    preset_items=items[2:4];
                      
    app = QtWidgets.QApplication(sys.argv);
    ex=Select_item_tolist_simpler(items,preset_items)
    ex.show()                     
#    prog = Select_item_tolist(Form,items,preset_items);                              
#    Form = QtWidgets.QWidget();
#    
#    Form.show();
    sys.exit(app.exec_())

