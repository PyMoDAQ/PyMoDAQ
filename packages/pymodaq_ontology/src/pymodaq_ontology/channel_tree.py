"""The tree listing the channels with their term and status"""
from dataclasses import dataclass
from typing import Iterable, Optional

from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_gui.utils.status_palette import Status, StatusPalette

KEY_ROLE = QtCore.Qt.ItemDataRole.UserRole
KIND_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1

# status of a channel -> (status of the palette of PyMoDAQ, what the led means)
STATUSES = {
    'assigned': (Status.IDLE, 'The term fits the channel'),
    'none': (Status.OFF, 'No term assigned'),
    'incompatible': (Status.WARNING, 'The term is not meant for this kind of channel'),
    'missing': (Status.ERROR, 'No such channel in the Dashboard: check the cabling and the assignment'),
}


@dataclass(frozen=True)
class ChannelRow:
    """What the tree shows for a channel: under the top level ``group``, then under ``module`` if not empty"""
    key: str
    kind: str
    name: str
    group: str
    module: str = ''
    term_label: str = ''
    value_text: str = ''
    status: str = 'none'  # a key of STATUSES


class ChannelTree(QtWidgets.QTreeWidget):
    """Channels grouped by kind of instrument (and by module), with the term assigned, the last value and a led

    The key and kind of the channel of an item are given by :meth:`key_of` and :meth:`kind_of`
    (``None`` for the items of a group).
    """
    COLUMNS = ['Channel', 'Term', 'Last value', '']

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setColumnCount(len(self.COLUMNS))
        self.setHeaderLabels(self.COLUMNS)
        self.setExpandsOnDoubleClick(False)  # a double click chooses the term, it does not fold the group
        modes = QtWidgets.QHeaderView.ResizeMode
        for column, mode in enumerate((modes.ResizeToContents, modes.Stretch, modes.ResizeToContents,
                                       modes.ResizeToContents)):
            self.header().setSectionResizeMode(column, mode)

    def set_rows(self, rows: Iterable[ChannelRow]) -> None:
        """Show the rows, in the order given (the groups appear in the order of their first row)"""
        self.clear()
        groups: dict[tuple[str, str], QtWidgets.QTreeWidgetItem] = {}
        for row in rows:
            parent = groups.get((row.group, ''))
            if parent is None:
                parent = groups[(row.group, '')] = self._group_item(self, row.group)
            if row.module:
                if (row.group, row.module) not in groups:
                    groups[(row.group, row.module)] = self._group_item(parent, row.module)
                parent = groups[(row.group, row.module)]
            item = QtWidgets.QTreeWidgetItem(parent, [row.name, row.term_label, row.value_text, '●'])
            item.setData(0, KEY_ROLE, row.key)
            item.setData(0, KIND_ROLE, row.kind)
            palette_status, tip = STATUSES[row.status]
            item.setForeground(3, QtGui.QBrush(StatusPalette.color(palette_status)))
            item.setToolTip(3, tip)
        self.expandAll()

    @staticmethod
    def key_of(item: QtWidgets.QTreeWidgetItem) -> Optional[str]:
        return item.data(0, KEY_ROLE)

    @staticmethod
    def kind_of(item: QtWidgets.QTreeWidgetItem) -> Optional[str]:
        return item.data(0, KIND_ROLE) or None

    @staticmethod
    def _group_item(parent, title: str) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        return item
