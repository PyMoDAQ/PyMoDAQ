import warnings
from qtpy import QtWidgets, QtCore


MESSAGE_SEVERITIES = ['critical', 'information', 'question', 'warning']


def messagebox(severity='warning', title='this is a title', text='blabla'):
    """
    Display a popup messagebox with a given severity
    Parameters
    ----------
    severity: (str) one in ['critical', 'information', 'question', 'warning']
    title: (str) the displayed popup title
    text: (str) the displayed text in the message

    Returns
    -------
    bool: True if the user clicks on Ok
    """
    assert severity in MESSAGE_SEVERITIES
    messbox = getattr(QtWidgets.QMessageBox, severity)
    ret = messbox(None, title, text)
    return ret == QtWidgets.QMessageBox.Ok


def dialog(title='', message='', widget=None):
    dlg = QtWidgets.QDialog()
    dlg.setWindowTitle(title)
    dlg.setLayout(QtWidgets.QVBoxLayout())
    label = QtWidgets.QLabel(message)
    label.setAlignment(QtCore.Qt.AlignCenter)
    dlg.layout().addWidget(label)
    dlg.layout().addWidget(widget)
    button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    dlg.layout().addWidget(button_box)
    button_box.accepted.connect(dlg.accept)
    button_box.rejected.connect(dlg.reject)
    ret = dlg.exec()
    return ret


def show_message(message="blabla", title="Error"):
    DeprecationWarning('Using show_message is deprecated, please use messagebox in daq_utils.messenger module')
    messagebox('Warning', title=title, text=message)


