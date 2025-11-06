import os
from pathlib import Path
from qtpy import QtWidgets, QtCore, QtGui
from pyqtgraph.parametertree.Parameter import ParameterItem
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem
from pyqtgraph.parametertree import Parameter


class PlainTextWidget(QtWidgets.QWidget):
    """
        ================ ========================
        **Attributes**    **Type**
        *value_changed*   instance of pyqt Signal
        ================ ========================

        See Also
        --------
        initUI, emitsignal
    """
    value_changed = QtCore.Signal(str)

    def __init__(self):

        super().__init__()

        self.initUI()
        self.text_edit.textChanged.connect(self.emitsignal)

    def emitsignal(self):
        """
            Emit the value changed signal from the text_edit attribute.
        """
        text = self.text_edit.toPlainText()
        self.value_changed.emit(text)

    def set_value(self, txt):
        """
            Set the value of the text_edit attribute.

            =============== =========== ================================
            **Parameters**    **Type**    **Description**
            *txt*             string      the string value to be setted
            =============== =========== ================================
        """
        self.text_edit.setPlainText(txt)

    def get_value(self):
        """
            Get the value of the text_edit attribute.

            Returns
            -------
            string
                The string value of text_edit.
        """
        return self.text_edit.toPlainText()

    def initUI(self):
        """
            Init the User Interface.
        """

        self.hor_layout = QtWidgets.QHBoxLayout()
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumHeight(50)

        self.add_pb = QtWidgets.QPushButton()
        self.add_pb.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap("icons:Add2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.add_pb.setIcon(icon3)
        self.hor_layout.addWidget(self.text_edit)

        verlayout = QtWidgets.QVBoxLayout()
        verlayout.addWidget(self.add_pb)
        verlayout.addStretch()
        self.hor_layout.addLayout(verlayout)
        self.hor_layout.setSpacing(0)
        self.setLayout(self.hor_layout)


class PlainTextParameterItem(WidgetParameterItem):

    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.subItem = QtWidgets.QTreeWidgetItem()
        self.addChild(self.subItem)

    def treeWidgetChanged(self):
        # # TODO: fix so that superclass method can be called
        # # (WidgetParameter should just natively support this style)
        # WidgetParameterItem.treeWidgetChanged(self)
        if self.treeWidget() is not None:
            self.subItem.setFirstColumnSpanned(True)
            self.treeWidget().setItemWidget(self.subItem, 0, self.w)

            # for now, these are copied from ParameterItem.treeWidgetChanged
            self.setHidden(not self.param.opts.get('visible', True))
            self.setExpanded(self.param.opts.get('expanded', True))

    def makeWidget(self):
        """
            Make and initialize an instance of Plain_text_pb object from parameter options dictionnary (using 'readonly' key).

            Returns
            -------
            Plain_text_pb object
                The initialized object.

            See Also
            --------
            Plain_text_pb, buttonClicked
        """
        self.w = PlainTextWidget()
        self.w.text_edit.setReadOnly(self.param.opts.get('readonly', False))
        self.w.value = self.w.get_value
        self.w.setValue = self.w.set_value
        self.w.sigChanged = self.w.value_changed
        self.w.add_pb.clicked.connect(self.buttonClicked)
        return self.w

    def buttonClicked(self):
        text, ok = QtWidgets.QInputDialog.getText(None, "Enter a value to add to the parameter",
                                                  "String value:", QtWidgets.QLineEdit.Normal)
        if ok and not (text == ""):
            self.param.setValue(self.param.value() + '\n' + text)


class PlainTextPbParameter(Parameter):
    """Editable string; displayed as large text box in the tree."""
    itemClass = PlainTextParameterItem
    sigActivated = QtCore.Signal(object)

    def activate(self):
        """
            Send the Activated signal.
        """
        self.sigActivated.emit(self)
        self.emitStateChanged('activated', None)

