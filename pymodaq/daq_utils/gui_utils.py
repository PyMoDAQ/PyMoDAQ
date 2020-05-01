from PyQt5.QtCore import QObject, pyqtSignal, QEvent, QBuffer, QIODevice
from PyQt5 import QtGui, QtWidgets, QtCore
import re
import numpy as np
from pathlib import Path
from pyqtgraph.dockarea import DockArea


dashboard_submodules_params = [
    {'title': 'Save 2D datas and above:', 'name': 'save_2D', 'type': 'bool', 'value': False},
    {'title': 'Save raw datas only:', 'name': 'save_raw_only', 'type': 'bool', 'value': True, 'tooltip':
        'if True, will not save extracted ROIs used to do live plotting, only raw datas will be saved'},
    {'title': 'Do Save:', 'name': 'do_save', 'type': 'bool', 'default': False, 'value': False},
    {'title': 'N saved:', 'name': 'N_saved', 'type': 'int', 'default': 0, 'value': 0, 'visible': False},
    ]


def clickable(widget):
    class Filter(QObject):
        clicked = pyqtSignal()
        def eventFilter(self, obj, event):
            if obj == widget:
                if event.type() == QEvent.MouseButtonRelease:
                    if obj.rect().contains(event.pos()):
                        self.clicked.emit()
                        # The developer can opt for .emit(obj) to get the object within the slot.
                        return True
            return False
     
    filter = Filter(widget)
    widget.installEventFilter(filter)
    return filter.clicked




def h5tree_to_QTree(base_node, base_tree_elt=None, pixmap_items=[]):
    """
        | Convert a loaded h5 file to a QTreeWidgetItem element structure containing two columns.
        | The first is the name of the h5 current node, the second is the path of the node in the h5 structure.
        |
        | Recursive function discreasing on base_node.

        ==================   ======================================== ===============================
        **Parameters**        **Type**                                 **Description**

          *h5file*            instance class File from tables module   loaded h5 file

          *base_node*         pytables h5 node                         parent node

          *base_tree_elt*     QTreeWidgetItem                          parent QTreeWidgetItem element
        ==================   ======================================== ===============================

        Returns
        -------
        QTreeWidgetItem
            h5 structure copy converted into QtreeWidgetItem structure.

        See Also
        --------
        h5tree_to_QTree

    """

    if base_tree_elt is None:
        base_tree_elt = QtWidgets.QTreeWidgetItem([base_node.name, "", base_node.path])
    for node_name, node in base_node.children().items():
        child = QtWidgets.QTreeWidgetItem([node_name, "", node.path])
        if 'pixmap' in node.attrs.attrs_name:
            pixmap_items.append(dict(node=node, item=child))
        if node.attrs['CLASS'] == 'GROUP':
            h5tree_to_QTree(node, child, pixmap_items)
        base_tree_elt.addChild(child)
    return base_tree_elt, pixmap_items


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

        buttonBox = QtWidgets.QDialogButtonBox();
        buttonBox.addButton('Apply', buttonBox.AcceptRole)
        buttonBox.accepted.connect(self.dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        vlayout.addWidget(buttonBox)
        self.dialog.setWindowTitle('Select an entry in the list')

        res = self.dialog.show()

        pass
        if res == self.dialog.Accepted:
            # save preset parameters in a xml file
            return  [self.list_widget.currentIndex(), self.list_widget.currentItem().text()]
        else:
            return [-1, ""]


def select_file(start_path=None, save=True, ext=None):
    """Save or open a file with Qt5 file dialog, to be used within an Qt5 loop.

    Usage::

        from pymodaq.daq_utils.daq_utils import select_file
        select_file(start_path="C:\\test.h5",save=True,ext='h5')

    =============== ======================================= ===========================================================================
    **Parameters**     **Type**                              **Description**

    *start_path*       Path object or str or None, optional  the path Qt5 will open in te dialog
    *save*             bool, optional                        * if True, a savefile dialog will open in order to set a savefilename
                                                             * if False, a openfile dialog will open in order to open an existing file
    *ext*              str, optional                         the extension of the file to be saved or opened
    =============== ======================================= ===========================================================================

    Returns
    -------
    Path object
        the Path object pointing to the file

    Examples
    --------



    """
    if ext is None:
        ext = '*'
    if not save:
        if not isinstance(ext, list):
            ext = [ext]

        filter = "Data files ("
        for ext_tmp in ext:
            filter += '*.' + ext_tmp + " "
        filter += ")"
    if start_path is not None:
        if not isinstance(start_path, str):
            start_path = str(start_path)
    if save:
        fname = QtWidgets.QFileDialog.getSaveFileName(None, 'Enter a .' + ext + ' file name', start_path,
                                                      ext + " file (*." + ext + ")")
    else:
        fname = QtWidgets.QFileDialog.getOpenFileName(None, 'Select a file name', start_path, filter)

    fname = fname[0]
    if fname != '':  # execute if the user didn't cancel the file selection
        fname = Path(fname)
        if save:
            parent = fname.parent
            filename = fname.stem
            fname = parent.joinpath(filename + "." + ext)  # forcing the right extension on the filename
    return fname  # fname is a Path object

class DockArea(DockArea, QObject):
    """
    Custom Dockarea class subclassing from the standard DockArea class and QObject so it can emit a signal when docks
    are moved around (one subclassed method: moveDock)
    See Also
    --------
    pyqtgraph.dockarea
    """
    dock_signal = pyqtSignal()

    def __init__(self, temporary=False, home=None):
        super(DockArea, self).__init__(temporary, home)

    def moveDock(self, dock, position, neighbor):
        """
        Move an existing Dock to a new location.
        """
        ## Moving to the edge of a tabbed dock causes a drop outside the tab box
        if position in ['left', 'right', 'top', 'bottom'] and neighbor is not None and neighbor.container() is not None and neighbor.container().type() == 'tab':
            neighbor = neighbor.container()
        self.addDock(dock, position, neighbor)
        self.dock_signal.emit()


def set_enable_recursive(children, enable=False):
    """Apply the enable state on all children widgets, do it recursively

    Parameters
    ----------
    children: (list) elements children ofa pyqt5 element
    enable: (bool) set enabled state (True) of all children widgets
    """
    for child in children:
        if not children:
            return
        elif isinstance(child, QtWidgets.QSpinBox) or isinstance(child, QtWidgets.QComboBox) or \
                isinstance(child, QtWidgets.QPushButton) or isinstance(child, QtWidgets.QListWidget):
            child.setEnabled(enable)
        else:
            set_enable_recursive(child.children(), enable)


def widget_to_png_to_bytes(widget, keep_aspect= True, width=200, height=100):
    """
    Renders the widget content in a png format as a bytes string
    Parameters
    ----------
    widget: (QWidget) the widget to render
    keep_aspect: (bool) if True use width and the widget aspect ratio to calculate the height
                        if False use set values of width and height to produce the png
    width: (int) the rendered width of the png
    height: (int) the rendered width of the png

    Returns
    -------
    binary string

    """
    png = widget.grab().toImage()
    wwidth = widget.width()
    wheight = widget.height()
    if keep_aspect:
        height = width * wheight / wwidth

    png = png.scaled(width, height, QtCore.Qt.KeepAspectRatio)
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.WriteOnly)
    png.save(buffer, "png")
    return buffer.data().data()


def pngbinary2Qlabel(databinary):
    buff = QBuffer()
    buff.open(QIODevice.WriteOnly)
    buff.write(databinary)
    dat = buff.data()
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(dat, 'PNG')
    label = QtWidgets.QLabel()
    label.setPixmap(pixmap)
    return label