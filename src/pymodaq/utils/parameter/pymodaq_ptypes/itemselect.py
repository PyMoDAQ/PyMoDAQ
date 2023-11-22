from qtpy import QtWidgets, QtCore, QtGui
from pyqtgraph.parametertree.Parameter import ParameterItem
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem
from pyqtgraph.parametertree import Parameter


class ItemSelect_pb(QtWidgets.QWidget):
    def __init__(self,checkbox=False,):

        super(ItemSelect_pb, self).__init__()
        self.initUI(checkbox,)

    def initUI(self, checkbox=False,):        
        #### Widgets ###        
        # ListWidget
        self.itemselect = ItemSelect(checkbox)
        # Pushbutton Add
        self.add_pb = QtWidgets.QPushButton()
        self.add_pb.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Add2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.add_pb.setIcon(icon3)        
        # Pushbutton Remove
        self.remove_pb = QtWidgets.QPushButton()
        self.remove_pb.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/remove.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.remove_pb.setIcon(icon3)               
        #### Layout ###
        self.ver_layout = QtWidgets.QVBoxLayout()    
        self.ver_layout.addWidget(self.add_pb)        
        self.ver_layout.addWidget(self.remove_pb)            
        self.ver_layout.setSpacing(0)
                
        self.hor_layout = QtWidgets.QHBoxLayout()        
        self.hor_layout.addWidget(self.itemselect)
        self.hor_layout.addLayout(self.ver_layout)
        
        self.hor_layout.setSpacing(0)
        self.setLayout(self.hor_layout)


class ItemSelect(QtWidgets.QListWidget):
    def __init__(self, hasCheckbox=False):
        QtWidgets.QListWidget.__init__(self)
        self.hasCheckbox = hasCheckbox # Boolean indicating if listwidget item uses checkbox ot not

    def get_value(self):
        """
            Get the dictionnary of values contained in the QtWidget attribute.

            Returns
            -------
            dictionnary
                The dictionnary of all_items compared to the selectedItems.                                
        """
        if self.hasCheckbox:            
            selitems = [item.text() for item in self.all_items() if item.checkState()!=0]            
        else:
            selitems = [item.text() for item in self.selectedItems()]
            
        allitems = [item.text() for item in self.all_items()]
        return dict(all_items=allitems, selected=selitems)

    def all_items(self):
        """
            Get the all_items list from the self QtWidget attribute.

            Returns
            -------
            list
                The item list.
        """
        return [self.item(ind) for ind in range(self.count())]

    def set_value(self, values):
        """
            Set values to the all_items attributes filtering values by the 'selected' key.

            =============== ============== =======================================
            **Parameters**    **Type**       **Description**
            *values*          dictionnary    the values dictionnary to be setted.
            =============== ============== =======================================
        """
        allitems = []
        # Check existing items
        for item in self.all_items():     
            if item.text() not in values['all_items']: # Remove items from list if text not in values
                item = self.takeItem(self.row(item))
                del item # Qt recommand to delete the item when removed
            else:
                allitems.append(item.text()) # Add items to list
        # Loop through all values
        for value in values['all_items']: # Loop through all values
            if value not in allitems: # Test if object already exists
                item = QtWidgets.QListWidgetItem(value) # Create object
                if self.hasCheckbox: # Add checkbox if required
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                    item.setCheckState(QtCore.Qt.Unchecked)                  
                self.addItem(item) # Add object to widget
            QtWidgets.QApplication.processEvents()
        if not self.hasCheckbox:
            self.clearSelection() # Restart selection
            for item in self.all_items():
                if item.text() in values['selected']:
                    item.setSelected(True)

class ItemSelectParameterItem(WidgetParameterItem):
    
    def makeWidget(self):
        """
            | Make and initialize an instance of ItemSelect_pb with itemselect value.
            | Connect the created object with the plus and minus buttonClicked function.

        """
        self.asSubItem = True
        self.hideWidget = False
        opts = self.param.opts
        
        if 'checkbox' in opts and opts['checkbox']:      
            w = ItemSelect_pb(checkbox=opts['checkbox'])
            w.sigChanged = w.itemselect.itemChanged
        else:
            w = ItemSelect_pb()
            w.sigChanged = w.itemselect.itemSelectionChanged
            
        if 'dragdrop' in opts and opts['dragdrop']:        
            w.itemselect.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        w.itemselect.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        if 'minheight' in opts:
            w.itemselect.setMinimumHeight(opts['min_height'])

        if 'height' in opts:
            w.itemselect.setMaximumHeight(opts['height'])
        else:
            w.itemselect.setMaximumHeight(70)
        # w.setReadOnly(self.param.opts.get('readonly', False))
        if 'show_pb' in opts:
            w.add_pb.setVisible(opts['show_pb'])
        else:
            w.add_pb.setVisible(False)
            
        if 'show_mb' in opts:
            w.remove_pb.setVisible(opts['show_mb'])
        else:
            w.remove_pb.setVisible(False)

        if 'tip' in opts:
            w.setToolTip(opts['tip'])
        w.value = w.itemselect.get_value
        w.setValue = w.itemselect.set_value
        w.add_pb.clicked.connect(self.pb_buttonClicked)
        w.remove_pb.clicked.connect(self.mb_buttonClicked)        
        return w

    def pb_buttonClicked(self):
        """
           Append to the param attribute the dictionnary obtained from the QtWidget add parameter procedure.
        """

        text, ok = QtWidgets.QInputDialog.getText(None, "Enter a value to add to the parameter",
                                                  "String value:", QtWidgets.QLineEdit.Normal)
        if text in self.param.value()['all_items']:
            print('Entry already exists, please use a different name.')
            return
        if ok and not (text == ""):
            all = self.param.value()['all_items']
            all.append(text)
            sel = self.param.value()['selected']
            sel.append(text)
            val = dict(all_items=all, selected=sel)
            self.param.setValue(val)
            self.param.sigValueChanged.emit(self.param, val)
            
    def mb_buttonClicked(self):
        """
           Remove the selected Qwidget items by removing the entries in the parameter attribute.
        """                       
        items_to_be_removed = self.widget.itemselect.selectedItems()
        if len(items_to_be_removed) > 0:
            all = self.param.value()['all_items']
            sel = self.param.value()['selected'] 
            for i in items_to_be_removed:
                if i.text() in all:
                    all.remove(i.text())
                if i.text() in sel:
                    sel.remove(i.text())
            val = dict(all_items=all, selected=sel)
            self.param.setValue(val)
            self.param.sigValueChanged.emit(self.param, val)            

    def optsChanged(self, param, opts):
        """
            Called when any options are changed that are not name, value, default, or limits.

            See Also
            --------
            optsChanged
        """
        # print "opts changed:", opts
        ParameterItem.optsChanged(self, param, opts)

        if 'show_pb' in opts:
            self.widget.add_pb.setVisible(opts['show_pb'])
        if 'show_mb' in opts:
            self.widget.remove_pb.setVisible(opts['show_mb'])
            


class ItemSelectParameter(Parameter):
    """
        Editable string; displayed as large text box in the tree.

        =============== ======================================
        **Attributes**    **Type**
        *itemClass*       instance of ItemSelectParameterItem
        *sigActivated*    instance of pyqt Signal
        =============== ======================================
    """
    itemClass = ItemSelectParameterItem
    sigActivated = QtCore.Signal(object)

    def activate(self):
        """
            Activate the "Activated" signal attribute0
        """
        self.sigActivated.emit(self)
        self.emitStateChanged('activated', None)



