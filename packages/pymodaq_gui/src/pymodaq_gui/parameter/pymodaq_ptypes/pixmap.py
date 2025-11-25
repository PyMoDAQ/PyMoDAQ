import numpy as np
from qtpy import QtWidgets, QtGui
from qtpy.QtCore import QByteArray, QObject
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter
from qtpy import QtWidgets, QtGui
from qtpy.QtCore import QByteArray
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem


class PixmapCheckData:
    def __init__(self, data: np.ndarray, path: str = '', checked: bool = False, info: str = ''):
        if data is not None:
            data = data / np.max(data) * 255
            data = data.astype(np.uint8)
            self.data = data[:, :]
        else:
            self.data = []
        self.path = path
        self.checked = checked
        self.info = info

    def __eq__(self, other):
        if other is None:
            return False
        else:
            status = np.all(np.isclose(self.data, other.data))
            status = status and self.checked == other.checked
            status = status and self.path == other.path
            return status


class PixmapCheckWidget(QtWidgets.QWidget):
    """ value of this parameter is a PixmapCheckData

    See Also
    --------
    PixmapCheckedData
    """

    def __init__(self):

        super().__init__()
        self._data: PixmapCheckData = None
        self.checkbox: QtWidgets.QCheckBox = None
        self.label: QtWidgets.QLabel = None
        self.info_label: QtWidgets.QLabel = None
        self.initUI()

    def initUI(self):
        """
            Init the User Interface.
        """
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.label = QtWidgets.QLabel()
        self.label.setMaximumWidth(100)
        self.label.setMinimumHeight(50)
        self.label.setMaximumHeight(50)
        self.layout().addWidget(self.label)

        ver_widget = QtWidgets.QWidget()
        ver_widget.setLayout(QtWidgets.QVBoxLayout())
        self.checkbox = QtWidgets.QCheckBox('Show/Hide')
        self.info_label = QtWidgets.QLabel()
        # self.info.setReadOnly(True)
        self.checkbox.setChecked(False)
        ver_widget.layout().addWidget(self.info_label)
        ver_widget.layout().addWidget(self.checkbox)
        ver_widget.layout().setSpacing(0)
        ver_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(ver_widget)

    def setValue(self, data: PixmapCheckData):


        im = QtGui.QImage(data.data, *data.data.shape, QtGui.QImage.Format_Indexed8)
        a = QtGui.QPixmap.fromImage(im)

        self.label.setPixmap(a)
        self.checkbox.setChecked(data.checked)
        self.info_label.setText(data.info)
        self._data = data

    def value(self):
        return PixmapCheckData(data=self._data.data if self._data is not None else None,
                               checked=self.checkbox.isChecked(),
                               info=self._data.info if self._data is not None else '',
                               path=self._data.path if self._data is not None else '')


class PixmapParameterItem(WidgetParameterItem):
    """Registered parameter type which displays a QPixmap in a QLabel"""

    def makeWidget(self):
        w = QtWidgets.QLabel()
        w.sigChanged = None
        w.value = w.pixmap
        w.setValue = w.setPixmap
        return w


class PixmapCheckParameterItem(WidgetParameterItem):
    """Registered parameter type which displays a PixmapCheckWidget custom widget"""

    def makeWidget(self):
        w = PixmapCheckWidget()
        w.sigChanged = w.checkbox.clicked
        w.value = w.value
        w.setValue = w.setValue
        self.hideWidget = False
        return w


class PixmapCheckParameter(SimpleParameter):
    itemClass = PixmapCheckParameterItem

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class PixmapParameter(SimpleParameter):
    itemClass = PixmapParameterItem

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def main_widget():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    prog = PixmapCheckWidget()
    prog.show()
    data = np.arange(128 * 256).reshape((256, 128))
    data = data / np.max(data) * 255
    data = data.astype(np.uint8)
    prog.setValue(PixmapCheckData(data=data,
                                  checked=True,
                                  info='this is an info'))

    def print_toggled(status):
        print(f"toggled: {status}")

    prog.checkbox.toggled.connect(print_toggled)

    sys.exit(app.exec_())


def main_parameter():
    from pymodaq.utils.managers.parameter_manager import ParameterManager
    data = np.arange(128 * 256).reshape((256, 128))
    data = data / np.max(data) * 255
    data = data.astype(np.uint8)

    class PixmapParameter(ParameterManager):
        params = {'title': 'Overlays', 'name': 'overlays', 'type': 'group', 'children': [
            {'name': f'Overlay{0:03.0f}', 'type': 'pixmap_check',
             'value': PixmapCheckData(data=data, checked=False,
                                      info=f'This is an info')},
            {'name': 'other', 'type': 'bool_push', 'value': True},
            {'name': 'otherp', 'type': 'led_push', 'value': True},
        ]},

        def value_changed(self, param):
            print(f'Value changed for {param}: {param.value()}')

    import sys
    app = QtWidgets.QApplication(sys.argv)
    prog = PixmapParameter()
    prog.settings_tree.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main_parameter()
