"""The OntologyManager: assign the terms of an ontology to the channels of the instruments of the Dashboard"""
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_utils.config import get_set_config_dir
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq_gui.messenger import messagebox

from pymodaq.utils.dashboard_mixin import DashboardMixin
from pymodaq.utils.managers.modules.modules_manager import ModulesManager

from pymodaq_ontology.assignment import Assignment, save_entry, load_entry
from pymodaq_ontology.channels import Channel, actuator_channels, detector_channels
from pymodaq_ontology.sources import OntologySource, SourceFactory
from pymodaq_ontology.term_picker import TermPicker
from pymodaq_ontology.terms import ACTUATOR, DETECTOR, OntologyTerm

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard

logger = set_logger(get_module_name(__file__))

GROUP_TITLES = {ACTUATOR: 'Actuators', DETECTOR: 'Detectors'}
MISSING = 'Not in the Dashboard'
COLUMNS = ['Channel', 'Term', 'Last value', '']
COLORS = {'assigned': '#2e9d4f', 'incompatible': '#d9822b', 'none': '#9a9a9a', 'missing': '#c0392b'}
KEY_ROLE = QtCore.Qt.ItemDataRole.UserRole
KIND_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1


class OntologyManager(DashboardMixin, ManagerBase):
    """Assigns ontology terms to the channels of the actuators and detectors of the Dashboard

    One entry file is kept for each experiment, holding the source of the terms and the assignment. Double click on
    the term of a channel to choose it in a popup. The assignment is saved in the current entry each time it changes.
    """
    own_modules_manager = False  # only looks modules up: the ones of the dashboard

    entry_type = 'ontology'
    entry_extension = '.ontology'
    icon_name = 'hub'

    def __init__(self, dashboard: Optional['DashBoard'] = None, **kwargs):
        self.assignment = Assignment()
        self.source: Optional[OntologySource] = None
        self.terms: dict[str, OntologyTerm] = {}
        self.channels: list[Channel] = []
        super().__init__(dashboard=dashboard, **kwargs)

    # ---- the manager machinery
    def can_execute_entry(self) -> bool:
        return True

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        experiment = self.experiment_manager.entry if self.experiment_manager is not None else 'default'
        folder = get_set_config_dir('ontology').joinpath(experiment or 'default')
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def save_entries(self, entry_path: Path = None) -> None:
        save_entry(entry_path, self.assignment, self.source)

    def _update_entry(self, entry_path: Path) -> None:
        self.load_entry(entry_path)

    def _execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        self.load_entry(entry_path)
        return True

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: Optional[bool] = None) -> None:
        super().do_things_after_experiment_set(experiment_name, show_dashboard)
        if experiment_name not in self.entries:
            self.create_entry(experiment_name, bypass_dialog=True)
        self.update_entry(experiment_name)
        self.update_channels_from_dashboard()

    # ---- the user interface
    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None) -> None:
        self.add_toolbar('management', 'Management', parent=self.mainwindow, add_break=True, before=self.toolbar)

    def setup_docks_and_widgets(self) -> None:
        self.source_type = QtWidgets.QComboBox()
        self.source_type.addItems(SourceFactory.types())
        self.source_location = QtWidgets.QLineEdit(placeholderText='Location of the ontology (file, address...)')
        browse = QtWidgets.QPushButton('Browse...')
        browse.clicked.connect(self._browse_source)
        load = QtWidgets.QPushButton('Load')
        load.clicked.connect(self._load_source_from_widgets)
        source_row = QtWidgets.QHBoxLayout()
        for widget in (QtWidgets.QLabel('Ontology:'), self.source_type, self.source_location, browse, load):
            source_row.addWidget(widget)
        source_row.setStretch(2, 1)

        self.channel_tree = QtWidgets.QTreeWidget()
        self.channel_tree.setColumnCount(len(COLUMNS))
        self.channel_tree.setHeaderLabels(COLUMNS)
        self.channel_tree.setExpandsOnDoubleClick(False)  # a double click chooses the term, it does not fold the group
        self.channel_tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.channel_tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.channel_tree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.channel_tree.header().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.channel_tree.itemDoubleClicked.connect(self._on_double_clicked)
        self.status_label = QtWidgets.QLabel('Double click the term of a channel to choose it.')

        layout = QtWidgets.QVBoxLayout(self.main_widget)
        layout.addLayout(source_row)
        layout.addWidget(self.channel_tree)
        layout.addWidget(self.status_label)

    def setup_actions(self) -> None:
        self.add_action('update_channels', 'Update channels', 'refresh', toolbar='management', auto_menu=True,
                        tip='Update the channels from the control modules of the Dashboard')
        self.add_action('probe', 'Probe detectors', 'search', toolbar='management', auto_menu=True,
                        tip='Do a snap of the detectors to find the channels they emit')

    def connect_things(self) -> None:
        self.connect_action('update_channels', self.update_channels_from_dashboard)
        self.connect_action('probe', self.probe)

    # ---- the ontology
    def set_source(self, source: Optional[OntologySource]) -> bool:
        """Read the terms of the source. Returns False (and keeps the previous ones) if it cannot be read"""
        if source is None:
            self.source, self.terms = None, {}
            self._refresh_tree()
            return True
        try:
            terms = source.terms()
        except Exception as e:
            logger.exception(f'Could not read the ontology {source.identifier}: {e}')
            self.status_label.setText(f'Could not read the ontology {source.identifier}: {e}')
            return False
        self.source, self.terms = source, {term.iri: term for term in terms}
        self.source_type.setCurrentText(source.source_type)
        self.source_location.setText(source.location)
        self.status_label.setText(f'{len(self.terms)} terms read from {source.identifier}')
        self._refresh_tree()
        return True

    def _browse_source(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self.mainwindow, 'Ontology file')
        if path:
            self.source_location.setText(path)
            self._load_source_from_widgets()

    def _load_source_from_widgets(self) -> None:
        source = SourceFactory.create(self.source_type.currentText(), self.source_location.text())
        if self.set_source(source):
            self.save_current_entry()

    # ---- the channels
    def set_channels(self, channels: list[Channel]) -> None:
        self.channels = list(channels)
        self._refresh_tree()

    def update_channels_from_dashboard(self) -> None:
        """Take the actuators of the Dashboard, and keep the detector channels already found by a probe"""
        if self.dashboard is None:
            return
        detectors = [channel for channel in self.channels if channel.kind == DETECTOR]
        self.set_channels(actuator_channels(self.dashboard.modules_manager.actuators_all) + detectors)

    def probe(self) -> None:
        """Snap the detectors of the Dashboard to find the channels they emit"""
        detectors = self.dashboard.modules_manager.detectors_all if self.dashboard is not None else []
        if not detectors:
            self.status_label.setText('There is no detector to probe')
            return
        # a manager of its own: the selection of the one of the Dashboard is not changed
        manager = ModulesManager(detectors=detectors, selected_detectors=detectors, actuators=[],
                                 parent_name=self.__class__.__name__)
        try:
            data = manager.probe_detectors()
        except Exception as e:
            logger.exception(f'The probe of the detectors failed: {e}')
            messagebox(text=f'The probe of the detectors failed: {e}')
            return
        actuators = [channel for channel in self.channels if channel.kind == ACTUATOR]
        self.set_channels(actuators + detector_channels(data.data))
        self.status_label.setText(f'{len(self.channels) - len(actuators)} detector channels found')

    # ---- the assignment
    def load_entry(self, entry_path: Path) -> None:
        self.assignment, source = load_entry(entry_path)
        if source is not None and (self.source is None or source.identifier != self.source.identifier):
            self.set_source(source)
        self._refresh_tree()

    def save_current_entry(self) -> None:
        if self.entry and self.entry_filepath.parent.is_dir():
            self.save_entries(self.entry_filepath)

    def status_of(self, channel_key: str, kind: str) -> str:
        """``none`` (no term), ``assigned``, ``incompatible`` (the term is not meant for this kind of channel)"""
        iri = self.assignment.get(channel_key)
        if not iri:
            return 'none'
        term = self.terms.get(iri)
        return 'incompatible' if term is not None and not term.fits(kind) else 'assigned'

    def _term_label(self, channel_key: str) -> str:
        iri = self.assignment.get(channel_key)
        if not iri:
            return ''
        term = self.terms.get(iri)
        return term.label if term is not None else iri  # an IRI the source does not know is shown as is

    def _refresh_tree(self) -> None:
        self.channel_tree.clear()
        groups: dict[tuple[str, str], QtWidgets.QTreeWidgetItem] = {}
        known = set()

        def parent_of(kind: str, module: str) -> QtWidgets.QTreeWidgetItem:
            top = groups.get((kind, ''))
            if top is None:
                title = MISSING if kind == '' else GROUP_TITLES[kind]
                top = groups[(kind, '')] = self._group_item(self.channel_tree, title)
            if kind == ACTUATOR:
                return top  # an actuator is its own channel: no level for its module
            if (kind, module) not in groups:
                groups[(kind, module)] = self._group_item(top, module)
            return groups[(kind, module)]

        for channel in sorted(self.channels, key=lambda c: (c.kind != ACTUATOR, c.module)):
            known.add(channel.key)
            item = QtWidgets.QTreeWidgetItem(parent_of(channel.kind, channel.module),
                                             [channel.name, self._term_label(channel.key),
                                              f'{channel.last_value} {channel.units}'.strip(), '●'])
            item.setData(0, KEY_ROLE, channel.key)
            item.setData(0, KIND_ROLE, channel.kind)
            self._paint(item, self.status_of(channel.key, channel.kind))
        for key in sorted(set(self.assignment.values) - known):  # assigned, but no such channel now
            item = QtWidgets.QTreeWidgetItem(parent_of('', ''), [key, self._term_label(key), '', '●'])
            item.setData(0, KEY_ROLE, key)
            item.setData(0, KIND_ROLE, '')
            self._paint(item, 'missing')
        self.channel_tree.expandAll()

    @staticmethod
    def _group_item(parent, title: str) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        return item

    @staticmethod
    def _paint(item: QtWidgets.QTreeWidgetItem, status: str) -> None:
        item.setForeground(3, QtGui.QBrush(QtGui.QColor(COLORS[status])))
        item.setData(3, QtCore.Qt.ItemDataRole.ToolTipRole, {
            'assigned': 'The term fits the channel', 'none': 'No term assigned',
            'incompatible': 'The term is not meant for this kind of channel',
            'missing': 'No such channel in the Dashboard: check the cabling and the assignment'}[status])

    def _on_double_clicked(self, item: QtWidgets.QTreeWidgetItem, _column: int = 0) -> None:
        key = item.data(0, KEY_ROLE)
        if key is None or not self.terms:
            return
        kind = item.data(0, KIND_ROLE) or None
        picker = TermPicker(list(self.terms.values()), self.mainwindow, self.assignment.get(key), kind,
                            title=f'Term for {key}')
        if picker.exec():
            self.assign(key, picker.selected_iri)

    def assign(self, channel_key: str, iri: str) -> None:
        """Assign the term to the channel and keep the assignment in the current entry"""
        self.assignment.set(channel_key, iri)
        self.save_current_entry()
        self._refresh_tree()
