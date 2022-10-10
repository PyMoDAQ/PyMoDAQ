from qtpy.QtCore import QObject
from qtpy import QtWidgets


class ListPicker(QObject):

    def __init__(self, list_str):
        super(ListPicker, self).__init__()
        self.list = list_str

    def pick_dialog(self):
        self.dialog = QtWidgets.QDialog()
        self.dialog.setMinimumWidth(500)
        vlayout = QtWidgets.QVBoxLayout()

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(self.list)

        vlayout.addWidget(self.list_widget, 10)
        self.dialog.setLayout(vlayout)

        buttonBox = QtWidgets.QDialogButtonBox()
        buttonBox.addButton('Apply', buttonBox.AcceptRole)
        buttonBox.accepted.connect(self.dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        vlayout.addWidget(buttonBox)
        self.dialog.setWindowTitle('Select an entry in the list')

        res = self.dialog.show()

        pass
        if res == self.dialog.Accepted:
            # save managers parameters in a xml file
            return [self.list_widget.currentIndex(), self.list_widget.currentItem().text()]
        else:
            return [-1, ""]