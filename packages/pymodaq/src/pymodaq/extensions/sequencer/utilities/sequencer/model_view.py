from pathlib import Path
from typing import Iterable, TYPE_CHECKING

from qtpy.QtWidgets import QStyle
from qtpy import QtWidgets, QtCore
from qtpy.QtGui import QKeySequence

from qtpy.QtCore import QModelIndex, QMimeData, Qt
from qt_themes import get_theme

from serializall import SerializableFactory

import yaml

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.utils import select_file, CustomApp
from pymodaq_gui.utils.menu_utils import MenuButton, IterableMenu


from ..element_factory import SeqEltFactory, SeqEltBase, MIME_TYPE
from ..elements.button import AddButtonPlaceholder
from ..elements.root import RootElt
from ..styling import button_style, menu_style, color_from_depth
from ... import get_set_sequencer_path
from ..yaml_utils import PrettyListDumper


if TYPE_CHECKING:
    from pymodaq.scripting import Dashboard
    from pymodaq.extensions.sequencer.utilities.sequencer.sequence import Sequence

seq_factory = SeqEltFactory()
ser_factory = SerializableFactory()


class FrameClosing(QtWidgets.QFrame):
    popup_hiding = QtCore.Signal()

    def hideEvent(self, event):  # for when the popup is "hidden" (when pressing enter for instance)
        self.popup_hiding.emit()
        super().hideEvent(event)



def elt_level(index: QModelIndex) -> int:
    """ Calculate nesting depth of the element with the specified index """
    depth = 0
    parent = index.parent()
    while parent.isValid():
        depth += 1
        parent = parent.parent()
    return depth


class SequenceWidgetDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_bg = get_theme().mantle

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QModelIndex):
        view = editor.parentWidget()
        if not view:
            return

        if index.isValid():
            elt: SeqEltBase = index.internalPointer()
            if elt.name == AddButtonPlaceholder.elt_name:
                super().updateEditorGeometry(editor, option, index)
                return
            else:
                mouse_global_pos = view.cursor().pos()
                #editor.resize(option.rect.width(), option.rect.height())
                editor.setGeometry(
                    mouse_global_pos.x(),
                    mouse_global_pos.y(),
                    max(elt.size_hint().width(), option.rect.width()),
                    elt.size_hint().height()
                )
                #editor.move(mouse_global_pos)

    def createEditor(self, parent, option, index: QModelIndex):
        if not index.isValid():
            return super().createEditor(parent, option, index)

        seq_elt: SeqEltBase = index.internalPointer()
        if seq_elt:
            if seq_elt.name == AddButtonPlaceholder.elt_name:
                return None
            container = FrameClosing(parent)
            container.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
            widget = seq_elt.create_widget(container)
            container.setObjectName("container")
            container.setStyleSheet("""
                #container {
                    border: 2px solid #888888;
                    border-radius: 4px;
                    background-color: palette(window);
                }
            """)
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(1, 1, 1, 1)
            layout.addWidget(widget)
            container.setFocusProxy(widget)
            return container

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        # Get data from model and populate the custom widget
        pass

    def setModelData(self, editor, model, index):
        pass

    def sizeHint(self, option, index):
        """Provide size hint for cells with widgets"""
        view_width = option.rect.width() if option.rect.width() > 0 else 100

        if index.isValid():
            elt = index.internalPointer()
            if elt and elt.name == AddButtonPlaceholder.elt_name:
                return QtCore.QSize(view_width, 35)
            qt_width = super().sizeHint(option, index).width()
            final_width = qt_width if qt_width > 0 else view_width
            return QtCore.QSize(final_width, 40)
        return QtCore.QSize(view_width, 40)

    def paint(self, painter, option, index):
        painter.save()

        # Calculate nesting depth
        depth = elt_level(index)

        level_color = color_from_depth(self.base_bg, depth)

        # Draw level background unless the row is currently highlighted/selected
        if not (option.state & QStyle.StateFlag.State_Selected):
            painter.fillRect(option.rect, level_color)

        painter.restore()
        super().paint(painter, option, index)


class SequenceTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, parent_sequence: 'Sequence' = None,
                 parent: QtCore.QObject = None,
                 dashboard: 'Dashboard' = None
                 ):

        super().__init__(parent)
        self.root_elt =  RootElt(parent_sequence=parent_sequence)
        self.insert_data(QtCore.QModelIndex(), 0, AddButtonPlaceholder())
        self._dashboard = dashboard
        self._ind_elt: int = 0
        self.parent_sequence = parent_sequence

    @property
    def dashboard(self) -> 'Dashboard':
        return self._dashboard

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_elt = self.root_elt
        else:
            parent_elt = parent.internalPointer()

        child_elt = parent_elt.children[row]
        if child_elt:
            return self.createIndex(row, column, child_elt)
        return QModelIndex()

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()

        child_elt: SeqEltBase = self.get_elt_from_index(child)
        parent_elt = child_elt.parent

        if parent_elt == self.root_elt:
            return QModelIndex()

        grandparent_elt = parent_elt.parent
        row = grandparent_elt.children.index(parent_elt)
        return self.createIndex(row, 0, parent_elt)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0

        parent_elt = self.get_elt_from_index(parent)

        if parent_elt is None:
            return 0
        return len(parent_elt.children)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole):
        if not index.isValid():
            return None

        elt: SeqEltBase = index.internalPointer()
        # --- HANDLE THE BUTTON PLACEHOLDER ---
        if elt.elt_name == AddButtonPlaceholder.elt_name:
            if role == Qt.ItemDataRole.DisplayRole:
                return None
            if role == Qt.ItemDataRole.SizeHintRole:
                return QtCore.QSize(100, 28)
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return repr(elt)
        elif role == Qt.ItemDataRole.EditRole:
            return elt
        return None

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid():
            node: SeqEltBase = index.internalPointer()
            if node.name == AddButtonPlaceholder.elt_name:
                return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            if node.children_allowed:
                return (default_flags |
                        Qt.ItemFlag.ItemIsEnabled |
                        Qt.ItemFlag.ItemIsSelectable |
                        Qt.ItemFlag.ItemIsDragEnabled |
                        Qt.ItemFlag.ItemIsEditable |
                        Qt.ItemFlag.ItemIsDropEnabled)

            return (default_flags |
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsSelectable |
                    Qt.ItemFlag.ItemIsDragEnabled |
                    Qt.ItemFlag.ItemIsEditable)
        else:
            return default_flags | Qt.ItemFlag.ItemIsDropEnabled

    def insert_data(self, parent_index: QModelIndex,
                    row: int,
                    new_object: SeqEltBase) -> bool:
        """
        Inserts an instance of SeqEltBase (or real implementation) under the given parent item.
        """
        parent_object = self.get_elt_from_index(parent_index)
        has_add_button = False
        for child in parent_object.children:
            if child.elt_name == AddButtonPlaceholder.elt_name:
                has_add_button = True
                break

        index_to_subtract = 1 if has_add_button else 0

        if row < 0 or row > len(parent_object.children) - index_to_subtract:
            row = len(parent_object.children) - index_to_subtract #-1 because there is a AddButton

        self.beginInsertRows(parent_index, row, row)
        new_object.parent = parent_object
        parent_object.children.insert(row, new_object)
        self.endInsertRows()

        return True

    def clear(self, clear_add=False):
        """ remove all elements but the AddButton"""
        if clear_add:
            count = len(self.root_elt.children)
        else:
            count = len(self.root_elt.children) - 1
        self.removeRows(0, count, parent=QModelIndex())

    def clear_children(self, parent: QModelIndex):
        """ Clear all children of the parent Element (or children of itself if children allowed)
        BUT the AddButton
        """

        while self.rowCount(parent) > 1:
            self.removeRow(0, parent)

    def removeRow(self, row: int, parent = QModelIndex()):
        parent_elt = self.get_elt_from_index(parent)
        child = parent_elt.children[row]
        if child.name == AddButtonPlaceholder.elt_name:
            return False

        self.beginRemoveRows(parent, row, row)
        if row - 1 < len(parent_elt.children):
            del parent_elt.children[row]
        self.endRemoveRows()
        return True

    def removeRows(self, row, count, parent=QModelIndex()):
        parent_elt = self.get_elt_from_index(parent)

        self.beginRemoveRows(parent, row, row + count - 1)
        if row + count - 1 < len(parent_elt.children):
            del parent_elt.children[row: row + count]
        self.endRemoveRows()
        return True

    def insert_data_by_elt(self, parent_elt: SeqEltBase,
                            row: int, new_object: SeqEltBase) -> bool:
        """
        Inserts a new object using a raw Python parent node instead of a QModelIndex.
        """
        parent_index = self.index_from_element(parent_elt)
        if parent_index.isValid():
            self.insert_data(parent_index, row, new_object)

    def index_from_element(self, elt: SeqEltBase) -> QModelIndex:
        if elt == self.root_elt:
            index = QModelIndex()
        else:
            # To create the index, we need to know which row the parent occupies inside ITS own parent
            parent: SeqEltBase = elt.parent
            if parent is None:
                index = QModelIndex()
            else:
                elt_row = parent.children.index(elt)
                index = self.createIndex(elt_row, 0, elt)
        return index

    def get_ids(self, parent_elt: SeqEltBase = None) -> list[int]:
        """ Get the ids of the existing elements"""
        ids = []
        if parent_elt is None:
            parent_elt = self.root_elt
        for child in parent_elt.children:
            ids.append(child.id)
            ids.extend(self.get_ids(child))
        return ids

    def get_new_id(self, new_id: int = None) -> int:
        if new_id is None:
            new_id = max(self.get_ids()) +1
        ids = self.get_ids()
        while new_id in ids:
            new_id = new_id + 1
        self._ind_elt = new_id
        return new_id

    def save_elements(self, file_path: Path) -> None:
        with open(file_path, 'w') as file:
            yaml.dump(
                self.root_elt.to_dict(),
                file,
                Dumper=PrettyListDumper,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )

    def load_elements(self, file_path: Path | dict | str) -> None:
        self.clear(clear_add=True)
        if isinstance(file_path, Path | str):
            with open(file_path, 'r') as file:
                root_elt: SeqEltBase = SeqEltBase.from_dict(yaml.safe_load(file))
        else:
            root_elt: SeqEltBase = SeqEltBase.from_dict(file_path)
        self.recursive_insert(None, root_elt, 0)

    def recursive_insert(self, parent_index: QModelIndex | None,
                         elt: SeqEltBase,
                         row: int = None) -> None:
        """ Insert this elt and its children at the specified row of the specified parent index

        If parent_index is not valid => parent is the root elt
        If it is None, elt is the RootElt (do not insert it, only its children)

        """
        if row is None:
            row = 0

        # 1) remove all children first
        children: list[SeqEltBase] = []
        while len(elt.children) > 0:
            children.append(elt.children.pop(0))

        # 2) insert the elt and affect the Dashboard and parent app
        if parent_index is not None:
            self.insert_data(parent_index=parent_index, row=row, new_object=elt)
            elt.dashboard = self.dashboard
            elt.parent_sequence = self.parent_sequence
            elt.parent_elt = elt

        # 3) Check if it has children and call the method on them
        if parent_index is not None:
            this_elt_index = self.index(row, 0, parent_index)
        else:
            this_elt_index = QModelIndex()
        for ind_row, child in enumerate(children):
            self.recursive_insert(this_elt_index, child, ind_row)

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    def mimeTypes(self):
        types = super().mimeTypes()
        types.append(MIME_TYPE)
        return types

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        data = QMimeData()
        if indexes[0].isValid():
            elt: SeqEltBase = indexes[0].internalPointer()
            data.setData(MIME_TYPE, ser_factory.get_apply_serializer(elt))
        return data

    def dropMimeData(self, data: QMimeData,
                     action: Qt.DropAction,
                     row: int,
                     column: int,
                     parent: QModelIndex):
        if action == Qt.DropAction.IgnoreAction:
            return True

        if not data.hasFormat(MIME_TYPE):
            return False

        if row == -1:
            row = parent.row() if parent.isValid() else self.rowCount(parent)


        elt: SeqEltBase = ser_factory.get_apply_deserializer(data.data(MIME_TYPE).data())


        if action == Qt.DropAction.CopyAction:
            new_id = self.get_new_id(self._ind_elt)
            elt.id = new_id

        self.recursive_insert(parent, elt, row)
        return True

    def get_elt_from_index(self, index: QModelIndex) -> SeqEltBase:
        return index.internalPointer() if index.isValid() else self.root_elt


class SequenceTreeView(QtWidgets.QTreeView, ActionManager):
    """
    """
    def __init__(self, parent_sequence: 'Sequence' = None, dashboard: 'Dashboard' = None, parent=None):
        QtWidgets.QTreeView.__init__(self, parent)
        ActionManager.__init__(self)

        self.setup_menu()
        self._dashboard = dashboard
        self._current_path: Path = get_set_sequencer_path()
        self.parent_sequence = parent_sequence

        self.ind_elt = 0

    @property
    def dashboard(self) -> 'Dashboard':
        return self._dashboard

    def model(self) -> SequenceTreeModel:
        return super().model()

    def setModel(self, model: SequenceTreeModel):
        super().setModel(model)
        if model:
            model.rowsInserted.connect(self._on_rows_inserted)
            self.expanded.connect(self.update_section_buttons)
            self.doItemsLayout()
            self.update_section_buttons(QModelIndex())

    def _on_rows_inserted(self, parent_index, start, end):
        """Triggered automatically whenever rows are added to the model."""
        self.update_section_buttons(parent_index)
        #self.expand(parent_index)

    def update_section_buttons(self, parent_index=QModelIndex()):
        """Loops through immediate children of parent_index and injects buttons."""
        model = self.model()
        if not model:
            return

        for row in range(model.rowCount(parent_index)):
            current_index = model.index(row, 0, parent_index)
            elt: SeqEltBase = current_index.internalPointer()

            if elt.name == AddButtonPlaceholder.elt_name:
                if self.indexWidget(current_index) is not None:
                    continue
                container = QtWidgets.QWidget(self.viewport())
                container.setStyleSheet("background-color: transparent;")
                layout = QtWidgets.QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)

                btn: MenuButton = elt.create_widget(parent=container)
                btn.setFixedHeight(30)

                depth = elt_level(parent_index) + 1

                btn.setStyleSheet(button_style(depth))
                btn.menu.setStyleSheet(menu_style(depth))
                layout.addWidget(btn)
                layout.addStretch()
                #elt._btn_reference = container
                container.show()
                btn.triggered.connect(lambda path: self.create_and_add(path , current_index.parent()))

                self.setIndexWidget(current_index, container)
                pass

    def get_new_id(self, new_id: int = None) -> int:
        return self.model().get_new_id(new_id)

    def create_and_add(self, path: Iterable[str],
                       parent_index: QtCore.QModelIndex = None,
                       row: int = -1):
        self.ind_elt += 1
        new_id = self.get_new_id(self.ind_elt)
        self.ind_elt = new_id
        element = seq_factory.get_seq_elt(path[0].lower())(new_id,
                                                           parent_sequence=self.parent_sequence)
        element.dashboard = self.dashboard

        self.model().insert_data(parent_index=parent_index,
                                 row=row,
                                 new_object=element)
        parent_elt = self.elt_from_index(parent_index)
        elt_index = self.model().index(row if row != -1 else len(parent_elt.children) - 2, 0, parent_index)
        if element.children_allowed:
            self.model().insert_data(elt_index, 0, AddButtonPlaceholder())

    def elt_from_index(self, index: QtCore.QModelIndex) -> SeqEltBase:
        return index.internalPointer() if index.isValid() else self.model().root_elt

    def edit_row(self):
        index = self.currentIndex()
        index.model().edit_data(index)

    def setup_menu(self):
        self.add_menu('add_elements', 'Add Element',
                      parent_menu=self.menu,
                      menu=IterableMenu('Add Element',
                                        [elt.capitalize() for elt in seq_factory.elements if
                                         not (elt == AddButtonPlaceholder.elt_name or
                                              elt == RootElt.elt_name)],
                                        self.add_element))
        self.menu.addSeparator()
        self.add_action('remove', 'Remove Element', menu=self.menu,
                        shortcut=Qt.Key.Key_Delete)
        self.addAction(self.get_action('remove'))
        self.connect_action('remove', self.remove)

        self.add_action('clear_children', 'Clear Children', menu=self.menu)
        self.connect_action('clear_children', self.clear_children)

        self.menu.addSeparator()

        self.add_action('load_file', 'Load Sequence File', menu=self.menu,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_O))
        self.addAction(self.get_action('load_file'))
        self.add_action('save_file', 'Save Sequence File', menu=self.menu,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_S))
        self.addAction(self.get_action('save_file'))

        self.connect_action('load_file', lambda: self.load_data())
        self.connect_action('save_file', lambda: self.save_data())

    def load_data(self, path: Path = None):
        if path is None:
            path = select_file(self._current_path,
                               filter='Sequence file (*.seq)',
                               save=False, ext='seq', force_save_extension=True)
        if path is not None and path != '':
            self._current_path = path.parent
            self.model().load_elements(path)

    def save_data(self, path: Path = None):
        if path is None:
            path = select_file(self._current_path,
                               filter='Sequence file (*.seq)',
                               save=True, ext='seq', force_save_extension=True)
        if path is not None and path != '':
            self._current_path = path.parent
            self.model().save_elements(path)

    def add_element(self, name: str, path:tuple[str] = ()):
        current_elt = self.model().get_elt_from_index(self.currentIndex())
        if current_elt.children_allowed:
            self.create_and_add(path, self.currentIndex(), row=0)
        else:
            self.create_and_add(path, self.currentIndex().parent(), self.currentIndex().row() + 1)

    def contextMenuEvent(self, event):
        if self.menu is not None:
            self.menu.exec(event.globalPos())

    def clear_children(self):
        current_elt = self.model().get_elt_from_index(self.currentIndex())
        if current_elt.children_allowed:
            self.model().clear_children(self.currentIndex())
        else:
            self.model().clear_children(self.currentIndex().parent())

    def remove(self):
        """ Remove selected elements, only one at the time otherwise will mess with indexing"""
        for index in self.selectedIndexes():
            self.model().removeRow(index.row(), parent=self.model().parent(index))

    def sizeHint(self):
        # Taille de base si le modèle est vide
        if not self.model() or self.model().rowCount() == 0:
            return QtCore.QSize(200, 50)

        total_height = 0
        count = self.model().rowCount()
        max_width = 0
        for ind in range(count):
            index = self.model().index(ind, 0)
            total_height += self.sizeHintForIndex(index).height()
            max_width = max(max_width,self.sizeHintForIndex(index).width() )

        margins = self.contentsMargins()
        frame_width = self.frameWidth() * 2

        final_height = total_height + margins.top() + margins.bottom() + frame_width
        final_width = max_width + margins.left() + margins.right() + frame_width

        return QtCore.QSize(final_width, final_height)
