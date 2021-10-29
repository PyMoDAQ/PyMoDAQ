from qtpy import QtWidgets, QtGui
from qtpy.QtCore import QByteArray
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem


class PixmapCheckWidget(QtWidgets.QWidget):
    """ value of this parameter is a dict with checked, data for the pixmap and optionally path in h5 node
    """

    # valuechanged=Signal(dict)

    def __init__(self):

        super().__init__()
        self.path = ''
        self.data = None
        self.checked = False
        self.initUI()

    def initUI(self):
        """
            Init the User Interface.
        """
        self.ver_layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel()
        self.checkbox = QtWidgets.QCheckBox('Show/Hide')
        self.info = QtWidgets.QLineEdit()
        self.info.setReadOnly(True)
        self.checkbox.setChecked(False)
        self.ver_layout.addWidget(self.label)
        self.ver_layout.addWidget(self.info)
        self.ver_layout.addWidget(self.checkbox)
        self.ver_layout.setSpacing(0)
        self.ver_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.ver_layout)

    def setValue(self, dic):
        if 'data' in dic:
            if not isinstance(dic['data'], QtGui.QPixmap):
                self.data = QByteArray(dic['data'])
                im = QtGui.QImage.fromData(self.data)
                a = QtGui.QPixmap.fromImage(im)
            else:
                a = dic['data']
        else:
            a = dic['pixmap']
        if 'path' in dic:
            self.path = dic['path']
        else:
            self.path = ''
        if 'info' in dic:
            info = dic['info']
        else:
            info = ''
        self.label.setPixmap(a)
        self.checkbox.setChecked(dic['checked'])
        self.info.setText(info)
        # self.valuechanged.emit(dic)

    def value(self):
        return dict(pixmap=self.label.pixmap(), checked=self.checkbox.isChecked(), path=self.path)


class PixmapParameterItem(WidgetParameterItem):
    """Registered parameter type which displays a QLineEdit"""

    def makeWidget(self):
        w = QtWidgets.QLabel()
        w.sigChanged = None
        w.value = w.pixmap
        w.setValue = w.setPixmap
        return w


class PixmapCheckParameterItem(WidgetParameterItem):
    """Registered parameter type which displays a QLineEdit"""

    def makeWidget(self):
        w = PixmapCheckWidget()
        w.sigChanged = w.checkbox.toggled
        w.value = w.value
        w.setValue = w.setValue
        return w


