from unittest import mock

from qtpy import QtWidgets

from pymodaq_gui.managers.h5manager import H5Manager


def test_create_new_file_error_does_not_block_the_caller(qtbot):
    """A failing file creation warns the user, but returns at once: the modal static
    QMessageBox.warning blocked forever when nobody was there to close it."""
    manager = mock.Mock()
    manager._h5saver.init_file.side_effect = OSError('no such folder')

    H5Manager.create_new_file(manager)  # would hang with a modal dialog

    boxes = [w for w in QtWidgets.QApplication.topLevelWidgets()
             if isinstance(w, QtWidgets.QMessageBox) and w.windowTitle() == 'New File Error']
    assert len(boxes) == 1
    assert 'no such folder' in boxes[0].text()
    boxes[0].close()
