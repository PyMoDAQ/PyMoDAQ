from pathlib import Path

from qtpy import QtWidgets, QtCore, QtGui
from pyqtgraph import SpinBox


EDIT_PUSH_TYPES = ['abs', 'rel']


class PushButtonIcon(QtWidgets.QPushButton):
    def __init__(self, icon_name: str, text: str):
        super().__init__(text)
        if icon_name != '':
            icon = QtGui.QIcon()
            if Path(icon_name).is_file():
                icon.addPixmap(QtGui.QPixmap(icon_name), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
            else:
                icon.addPixmap(QtGui.QPixmap(f":/icons/Icon_Library/{icon_name}.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
            self.setIcon(icon)


class EditPushInfo:
    def __init__(self, type:str, value: float):
        if type not in EDIT_PUSH_TYPES:
            raise ValueError(f'Possible types are {EDIT_PUSH_TYPES}')
        self.type = type
        self.value = value


class EditPush(QtWidgets.QWidget):
    clicked = QtCore.Signal(EditPushInfo)

    def __init__(self, icon_name: str, ini_value=0.1, text=''):
        super().__init__()
        self._edit_push_type = 'abs'
        self.setLayout(QtWidgets.QHBoxLayout())
        self._edit = SpinBox(value=ini_value, dec=True, step=0.1, minStep=0.001)
        self._edit.setMinimumHeight(20)
        self._edit.setMaximumWidth(60)
        self._edit.setMinimumWidth(60)
        self.layout().addWidget(self._edit)
        self.set_pushs(icon_name, text)

    def set_pushs(self, icon_name, text):
        self._push = PushButtonIcon(icon_name, text)
        self._push.setMaximumWidth(40)
        self._push.clicked.connect(lambda: self.emit_clicked())
        self.layout().addWidget(self._push)

    def emit_clicked(self, coeff=1):
        """will emit a signal containing a float value calculated from the product of the coeff and the internal
        spinbox value.

        See Also
        --------
        EditPushRel
        """
        self.clicked.emit(EditPushInfo(type=self._edit_push_type, value=coeff * self._edit.value()))


class EditPushRel(EditPush):

    def __init__(self, icon_name: str, text='', ini_value=0.15):
        super().__init__(icon_name, text=text, ini_value=ini_value)
        self._edit_push_type = 'rel'

    def set_pushs(self, icon_name, text):
        vlayout = QtWidgets.QVBoxLayout()
        self.layout().addLayout(vlayout)

        self._push_plus = PushButtonIcon(icon_name, f'+{text}')
        self._push_plus.setMaximumWidth(40)
        self._push_minus = PushButtonIcon(icon_name, f'-{text}')
        self._push_minus.setMaximumWidth(40)

        vlayout.addWidget(self._push_plus)
        vlayout.addWidget(self._push_minus)

        self._push_plus.clicked.connect(lambda: self.emit_clicked(1))
        self._push_minus.clicked.connect(lambda: self.emit_clicked(-1))



