import warnings
from qtpy import QtWidgets


def deprecation_msg(message):
    warnings.warn(message, DeprecationWarning, stacklevel=3)


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