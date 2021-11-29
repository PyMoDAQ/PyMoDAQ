from qtpy import QtWidgets, QtCore, QtGui
from pyqtgraph.parametertree.Parameter import ParameterItem
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem
from pyqtgraph.parametertree import Parameter


class ItemSelect_pb(QtWidgets.QWidget):
    def __init__(self):

        super(ItemSelect_pb, self).__init__()
        self.initUI()

    def initUI(self):
        self.hor_layout = QtWidgets.QHBoxLayout()
        self.itemselect = ItemSelect()
        self.add_pb = QtWidgets.QPushButton()
        self.add_pb.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Add2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.add_pb.setIcon(icon3)
        self.hor_layout.addWidget(self.itemselect)
        self.hor_layout.addWidget(self.add_pb)
        self.hor_layout.setSpacing(0)

        self.setLayout(self.hor_layout)


class ItemSelect(QtWidgets.QListWidget):
    def __init__(self):
        QtWidgets.QListWidget.__init__(self)

    def get_value(self):
        """
            Get the dictionnary of values contained in the QtWidget attribute.

            Returns
            -------
            dictionnary
                The dictionnary of all_items compared to the slelectedItems.
        """
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
        allitems = [item.text() for item in self.all_items()]
        if allitems != values['all_items']:
            self.clear()
            self.addItems(values['all_items'])
            QtWidgets.QApplication.processEvents()

        self.clearSelection()
        for item in self.all_items():
            if item.text() in values['selected']:
                item.setSelected(True)


class ItemSelectParameterItem(WidgetParameterItem):
    def makeWidget(self):
        """
            | Make and initialize an instance of ItemSelect_pb with itemselect value.
            | Connect the created object with the buttonClicked function.

        """
        self.asSubItem = True
        self.hideWidget = False
        opts = self.param.opts
        w = ItemSelect_pb()
        w.itemselect.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        if 'height' in opts:
            w.itemselect.setMaximumHeight(opts['height'])
        else:
            w.itemselect.setMaximumHeight(70)
        # w.setReadOnly(self.param.opts.get('readonly', False))
        if 'show_pb' in opts:
            w.add_pb.setVisible(opts['show_pb'])
        else:
            w.add_pb.setVisible(False)
        if 'tip' in opts:
            w.setToolTip(opts['tip'])
        w.value = w.itemselect.get_value
        w.setValue = w.itemselect.set_value
        w.sigChanged = w.itemselect.itemSelectionChanged
        w.add_pb.clicked.connect(self.buttonClicked)
        return w

    def buttonClicked(self):
        """
           Append to the param attribute the dictionnary obtained from the QtWidget add parameter procedure.
        """

        text, ok = QtWidgets.QInputDialog.getText(None, "Enter a value to add to the parameter",
                                                  "String value:", QtWidgets.QLineEdit.Normal)
        if ok and not (text == ""):
            all = self.param.value()['all_items']
            all.append(text)
            sel = self.param.value()['selected']
            sel.append(text)
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



