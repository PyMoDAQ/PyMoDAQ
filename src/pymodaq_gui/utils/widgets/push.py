from pathlib import Path

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtWidgets import QWidget
from pymodaq_gui.utils.widgets.spinbox import SpinBox


EDIT_PUSH_TYPES = ['abs', 'rel']


class PushButtonIcon(QtWidgets.QPushButton):
    def __init__(self, icon_name: str, text: str, checkable=False, tip="", menu=None):
        super().__init__(text)
        self._menu = menu
        if icon_name != '':
            icon = QtGui.QIcon()
            if Path(icon_name).is_file():
                icon.addPixmap(QtGui.QPixmap(icon_name), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
            else:
                icon.addPixmap(QtGui.QPixmap(f":/icons/Icon_Library/{icon_name}.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
            self.setIcon(icon)
        self.setCheckable(checkable)
        self.setToolTip(tip)
        
    def contextMenuEvent(self, event):
        if self._menu is not None:
            self._menu.exec(event.globalPos())


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


class ActionMenu(QtWidgets.QAction):
    def __init__(self, *args, menu=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._menu = menu

    def contextMenuEvent(self, event):
        if self._menu is not None:
            self._menu.exec(event.globalPos())


def main(init_qt=True):
    import sys

    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

    widget = QtWidgets.QWidget()
    widget.setLayout(QtWidgets.QVBoxLayout())
    toolbar = QtWidgets.QToolBar()
    widget.layout().addWidget(toolbar)

    action = QtWidgets.QAction('blabla')
    toolbar.addAction(action)

    menu1 = QtWidgets.QMenu()
    menu1.addAction('Add new task')
    menu1.addAction('Edit current row')
    menu1.addAction('Remove selected rows')
    menu1.addSeparator()
    menu1.addAction('Affect Responsable')
    menu2 = QtWidgets.QMenu()
    menu2.addAction('Affect volunteers')
    menu2.addAction('Remove volunteers')
    menu2.addSeparator()
    menu2.addAction('Show localisation')

    icon = QtGui.QIcon()
    icon.addPixmap(QtGui.QPixmap(f":/icons/Icon_Library/{'run2'}.png"), QtGui.QIcon.Normal,
                   QtGui.QIcon.Off)
    action2 = ActionMenu(icon, 'grab', menu=menu1)

    toolbar.addAction(action2)
    grab_pb = PushButtonIcon('run2', text='', checkable=True, menu=menu2)
    grab_pb.setFlat(True)
    toolbar.addWidget(grab_pb)

    otherpb = PushButtonIcon('run2', 'grab me')
    widget.layout().addWidget(otherpb)

    widget.show()
    if init_qt:
        sys.exit(app.exec_())


if __name__ == '__main__':
    main()

