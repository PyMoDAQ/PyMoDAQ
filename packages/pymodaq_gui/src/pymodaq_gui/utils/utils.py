import os
import sys

from qtpy.QtCore import QObject, Signal, QEvent, QBuffer, QIODevice, Qt
from qtpy import QtWidgets, QtCore, QtGui

from pathlib import Path
from pymodaq_utils.config import Config
from pymodaq_utils.logger import set_logger, get_module_name
from pyqtgraph import mkQApp as mkQApppg


config = Config()
logger = set_logger(get_module_name(__file__))

def create_nested_menu(layers, items_per_layer, pattern="Menu", prefix_pattern="Sub", use_index_tracking=False):
    """
    Creates a nested dictionary structure with specified layers and items per layer.
    
    Args:
        layers (int): Number of layers in the nested structure
        items_per_layer (int or list): Number of items per layer. 
                                     Can be an integer (same for all layers) 
                                     or a list (specific count for each layer)
        pattern (str): Base pattern for naming items (default: "Menu")
        prefix_pattern (str): Prefix pattern for sub-levels (default: "Sub")
        use_index_tracking (bool): If True, adds _ijk tracking to names (default: False)
    
    Returns:
        dict: Nested dictionary structure
    
    Examples:
        create_nested_menu(3, 2, use_index_tracking=True) creates:
        {
            'Menu_1': {
                'SubMenu_11': ['SubSubMenu_111', 'SubSubMenu_112'],
                'SubMenu_12': ['SubSubMenu_121', 'SubSubMenu_122']
            },
            'Menu_2': {
                'SubMenu_21': ['SubSubMenu_211', 'SubSubMenu_212'],
                'SubMenu_22': ['SubSubMenu_221', 'SubSubMenu_222']
            }
        }
    """
    
    if layers <= 0:
        return {}
    
    # Handle items_per_layer as int or list
    if isinstance(items_per_layer, int):
        items_counts = [items_per_layer] * layers
    else:
        items_counts = list(items_per_layer)
        # Pad with last value if not enough items specified
        if len(items_counts) < layers:
            items_counts.extend([items_counts[-1]] * (layers - len(items_counts)))
    
    def build_layer(current_layer, parent_index=""):
        """Recursively build nested structure"""
        # Generate layer name based on current layer
        if current_layer == 1:
            layer_name = pattern
        else:
            if prefix_pattern:
                layer_name = prefix_pattern * (current_layer - 1) + pattern
            else:
                layer_name = pattern
        
        if current_layer == layers:
            # Last layer - return list of items
            result = []
            for i in range(items_counts[current_layer-1]):
                if use_index_tracking:
                    index_suffix = f"_{parent_index}{i+1}"
                    item_name = f"{layer_name}{index_suffix}"
                else:
                    item_name = f"{layer_name}{i+1}"
                result.append(item_name)
            return result
        
        # Not last layer - return dictionary
        result = {}
        for i in range(items_counts[current_layer-1]):
            if use_index_tracking:
                index_suffix = f"_{parent_index}{i+1}"
                key = f"{layer_name}{index_suffix}"
                new_parent_index = f"{parent_index}{i+1}"
            else:
                key = f"{layer_name}{i+1}"
                new_parent_index = ""
            
            result[key] = build_layer(current_layer + 1, new_parent_index)
        
        return result
    
    return build_layer(1)



def first_available_integer(liste):
    i = 0
    while i in liste:
        i += 1
    return i


here = Path(__file__).parent
custom_folder = here.parent.joinpath('QtDesigner_Ressources/custom/')
QtCore.QDir.addSearchPath('custom', str(custom_folder))


def set_dark_palette(app):
    from qtpy.QtGui import QPalette, QColor
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53,53,53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(42,42,42))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Dark, QColor(35,35,35))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(20,20,20))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(250,250,250))
    palette.setColor(QPalette.Disabled, QPalette.ColorRole.ButtonText, Qt.GlobalColor.darkGray)
    palette.setColor(QPalette.Disabled, QPalette.ColorRole.WindowText, Qt.GlobalColor.darkGray)
    palette.setColor(QPalette.Disabled, QPalette.ColorRole.Text, Qt.GlobalColor.darkGray)
    palette.setColor(QPalette.Disabled, QPalette.ColorRole.Light, QColor(53, 53, 53))

    app.setPalette(palette)

    # Checkbox are not visible in dark style but it is not possible to
    # modify QCheckBox style without messing up the check mark (it disappears)
    # so images are needed to avoid the problem.
    app.setStyleSheet("""
        QCheckBox::indicator {
            width: 1em;
            height: 1em; 
        }
        QCheckBox::indicator:unchecked {
            image: url('custom:checkbox/unchecked.png');
        }
        QCheckBox::indicator:unchecked:disabled {
            image: url('custom:checkbox/unchecked_disabled.png');
        }
        QCheckBox::indicator:unchecked:focus {
            image: url('custom:checkbox/unchecked_focus.png');
        }
        QCheckBox::indicator:unchecked:pressed {
            image: url('custom:checkbox/unchecked_pressed.png');
        }
        QCheckBox::indicator:checked {
            image: url('custom:checkbox/checked.png');
        }
        QCheckBox::indicator:checked:disabled {
            image: url('custom:checkbox/checked_disabled.png');
        }
        QCheckBox::indicator:checked:focus {
            image: url('custom:checkbox/checked_focus.png');
        }
        QCheckBox::indicator:checked:pressed {
            image: url('custom:checkbox/checked_pressed.png');
        }
        QCheckBox::indicator:indeterminate {
            image: url('custom:checkbox/indeterminate.png');
        }
        QCheckBox::indicator:indeterminate:disabled {
            image: url('custom:checkbox/indeterminate_disabled.png');
        }
        QCheckBox::indicator:indeterminate:focus {
            image: url('custom:checkbox/indeterminate_focus.png');
        }
        QCheckBox::indicator:indeterminate:pressed {
            image: url('custom:checkbox/indeterminate_pressed.png');
        }

        QToolBarExtension {
            background: #555555;
            qproperty-icon: url('custom:arrow/right.png');
        }
        QToolTip {
            color: white;
            background-color: #555555;
            border: 1px solid white; 
        }
        """)

def clickable(widget):
    class Filter(QObject):
        clicked = Signal()

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
        klass = node.attrs['CLASS']
        tooltip = []

        if 'origin' in node.attrs.attrs_name:
            tooltip.append(node.attrs['origin'])
        elif klass == 'GROUP':
            for c in node.children().values():
                if 'origin' in c.attrs.attrs_name:
                    tooltip.append(c.attrs['origin'])
                    break

        if hasattr(node, 'title') and node.title:
            tooltip.append(node.title)

        child.setToolTip(0, '/'.join(tooltip))

        if 'pixmap' in node.attrs.attrs_name:
            pixmap_items.append(dict(node=node, item=child))

        if klass == 'GROUP':
            h5tree_to_QTree(node, child, pixmap_items)

        base_tree_elt.addChild(child)
    return base_tree_elt, pixmap_items


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


def widget_to_png_to_bytes(widget, keep_aspect=True, width=200, height=100):
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

    png = png.scaled(int(width), int(height), QtCore.Qt.KeepAspectRatio)
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.WriteOnly)
    png.save(buffer, "png")
    return buffer.data().data()


def pngbinary2Qlabel(databinary, scale_height: int = None):
    buff = QBuffer()
    buff.open(QIODevice.WriteOnly)
    buff.write(databinary)
    dat = buff.data()
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(dat, 'PNG')
    if scale_height is not None and isinstance(scale_height, int):
        pixmap = pixmap.scaledToHeight(scale_height)
    label = QtWidgets.QLabel()
    label.setPixmap(pixmap)
    return label


def start_qapplication() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication(sys.argv)
    if config('style', 'darkstyle'):
        set_dark_palette(app)
    return app


def mkQApp(name: str):
    app = mkQApppg(name)
    if config('style', 'darkstyle'):
        set_dark_palette(app)
    return app


def exec():
    app = mkQApp('a name')
    return app.exec() if hasattr(app, 'exec') else app.exec_()
