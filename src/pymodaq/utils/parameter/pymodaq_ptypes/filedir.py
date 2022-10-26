import os
from pathlib import Path
from qtpy import QtWidgets, QtCore, QtGui
from pyqtgraph.parametertree.Parameter import ParameterItem
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem
from pyqtgraph.parametertree import Parameter


class FileDirWidget(QtWidgets.QWidget):
    """
        ================ =========================
        **Attributes**    **Type**
        *value_changed*   instance of pyqt Signal
        *path*            string
        ================ =========================

        See Also
        --------
        browse_path
    """
    value_changed = QtCore.Signal(str)

    def __init__(self, init_path='D:/Data', file_type=False):

        super().__init__()
        self.filetype = file_type
        self.path = init_path
        self.initUI()

        self.base_path_browse_pb.clicked.connect(self.browse_path)

    def browse_path(self):
        """
            Browse the path attribute if exist.

            See Also
            --------
            set_path
        """
        if self.filetype is True:
            folder_name = QtWidgets.QFileDialog.getOpenFileName(None, 'Choose File', os.path.split(self.path)[0])[0]
        elif self.filetype is False:
            folder_name = QtWidgets.QFileDialog.getExistingDirectory(None, 'Choose Folder', self.path)

        elif self.filetype == "save":
            folder_name = QtWidgets.QFileDialog.getSaveFileName(None, 'Enter a Filename', os.path.split(self.path)[0])[
                0]

        if not (not(folder_name)):  # execute if the user didn't cancel the file selection
            self.set_path(folder_name)
            self.value_changed.emit(folder_name)

    def set_path(self, path_file):
        """
            Set the base path attribute with the given path_file.

            =============== =========== ===========================
            **Parameters**    **Type**    **Description**
            *path_file*       string      the pathname of the file
            =============== =========== ===========================
        """
        if isinstance(path_file, Path):
            path_file = str(path_file)
        self.base_path_edit.setPlainText(path_file)
        self.path = path_file

    def get_value(self):
        """
            Get the value of the base_path_edit attribute.

            Returns
            -------
            string
                the path name
        """
        return self.base_path_edit.toPlainText()

    def initUI(self):
        """
            Init the User Interface.
        """

        self.hor_layout = QtWidgets.QHBoxLayout()
        self.base_path_edit = QtWidgets.QPlainTextEdit(self.path)
        self.base_path_edit.setMaximumHeight(50)
        self.base_path_browse_pb = QtWidgets.QPushButton()
        self.base_path_browse_pb.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Browse_Dir_Path.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.base_path_browse_pb.setIcon(icon3)
        self.hor_layout.addWidget(self.base_path_edit)

        verlayout = QtWidgets.QVBoxLayout()
        verlayout.addWidget(self.base_path_browse_pb)
        verlayout.addStretch()
        self.hor_layout.addLayout(verlayout)
        self.hor_layout.setSpacing(0)
        self.setLayout(self.hor_layout)


class FileDirParameterItem(WidgetParameterItem):
    def makeWidget(self):
        """
            Make an initialized file_browser object with parameter options dictionnary ('readonly' key)0

            Returns
            -------
            w : filebrowser
                The initialized file browser.

            See Also
            --------
            file_browser
        """
        self.asSubItem = True
        self.hideWidget = False
        if 'filetype' in self.param.opts:
            self.filetype = self.param.opts['filetype']
        else:
            self.filetype = True

        self.w = FileDirWidget(self.param.value(), file_type=self.filetype)

        # if 'tip' in self.param.opts:
        #     self.w.setToolTip(self.param.opts['tip'])

        self.w.base_path_edit.setReadOnly(self.param.opts['readonly'])
        self.w.value = self.w.get_value
        self.w.setValue = self.w.set_path
        self.w.sigChanged = self.w.value_changed
        return self.w


class FileDirParameter(Parameter):
    """
        Editable string; displayed as large text box in the tree.
        See Also
        --------
        file_browserParameterItem
    """
    itemClass = FileDirParameterItem


