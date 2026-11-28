"""The OntologyManager: assign the terms of an ontology to the channels of the instruments of the Dashboard"""
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from qtpy import QtWidgets

from pymodaq_utils.config import get_set_config_dir
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions
from pymodaq_gui.messenger import messagebox

from pymodaq.utils.dashboard_mixin import DashboardMixin
from pymodaq.utils.managers.modules.modules_manager import ModulesManager

from pymodaq_ontology.annotation import make_ontology_saver, make_annotator
from pymodaq_ontology.assignment import Assignment, save_entry, load_entry
from pymodaq_ontology.channel_tree import ChannelRow, ChannelTree
from pymodaq_ontology.channels import Channel, actuator_channels, detector_channels
from pymodaq_ontology.source_factory import OntologySource, SourceFactory
from pymodaq_ontology.term_picker import TermPicker
from pymodaq_ontology.terms import ACTUATOR, DETECTOR, OntologyTerm, TermHierarchy

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard

logger = set_logger(get_module_name(__file__))

GROUP_TITLES = {ACTUATOR: 'Actuators', DETECTOR: 'Detectors'}
MISSING = 'Not in the Dashboard'


class OntologyManager(DashboardMixin, ManagerBase):
    """Assigns ontology terms to the channels of the actuators and detectors of the Dashboard

    One entry file is kept for each experiment, holding the source of the terms and the assignment. Double click on
    the term of a channel to choose it in a popup. The assignment is saved in the current entry each time it changes.
    """
    own_modules_manager = False  # only looks modules up: the ones of the dashboard

    entry_type = 'ontology'
    entry_extension = '.ontology'
    icon_name = 'account_tree'

    def __init__(self, dashboard: Optional['DashBoard'] = None, **kwargs):
        self.assignment = Assignment()
        self.source: Optional[OntologySource] = None
        self.terms: dict[str, OntologyTerm] = {}
        self.channels: list[Channel] = []
        self._annotator = make_annotator(lambda: self.assignment)
        self._ontology_savers: dict = {}  # worker -> function saving the excerpt of the ontology in its file
        self._workers: list = []
        super().__init__(dashboard=dashboard, **kwargs)

    # ---- the manager machinery
    def can_execute_entry(self) -> bool:
        return True

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """ All the entries together: one file per experiment, named after it """
        folder = get_set_config_dir('ontology')
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def list_managed_entries_path(self, **kwargs_to_entry_folder) -> list[Path]:
        folder = self.get_entry_folder(**kwargs_to_entry_folder)
        return sorted(path for path in folder.iterdir() if path.suffix == self.entry_extension)

    def list_managed_entries(self, **kwargs_to_entry_folder) -> list[str]:
        return [path.stem for path in self.list_managed_entries_path(**kwargs_to_entry_folder)]

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
        self.source_type.addItems(SourceFactory.names())
        self.source_location = QtWidgets.QLineEdit(placeholderText='Location of the ontology (file, address...)')
        browse = QtWidgets.QPushButton('Browse...')
        browse.clicked.connect(self._browse_source)
        load = QtWidgets.QPushButton('Load')
        load.clicked.connect(self._load_source_from_widgets)
        source_row = QtWidgets.QHBoxLayout()
        for widget in (QtWidgets.QLabel('Ontology:'), self.source_type, self.source_location, browse, load):
            source_row.addWidget(widget)
        source_row.setStretch(2, 1)

        self.channel_tree = ChannelTree()
        self.channel_tree.itemDoubleClicked.connect(self._on_double_clicked)
        self.status_label = QtWidgets.QLabel('Double click the term of a channel to choose it.')
        self.status_label.setWordWrap(True)  # a long path or error message must not widen the window
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)

        # the same actions as the toolbar, within reach of the channels they refresh
        update_button = QtWidgets.QPushButton('Update channels')
        update_button.setToolTip('Update the channels from the control modules of the Dashboard')
        update_button.clicked.connect(self.update_channels_from_dashboard)
        probe_button = QtWidgets.QPushButton('Probe detectors')
        probe_button.setToolTip('Do a snap of the detectors to find the channels they emit')
        probe_button.clicked.connect(self.probe)
        buttons_row = QtWidgets.QHBoxLayout()
        buttons_row.addWidget(update_button)
        buttons_row.addWidget(probe_button)
        buttons_row.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self.main_widget)
        layout.addLayout(source_row)
        layout.addLayout(buttons_row)
        layout.addWidget(self.channel_tree)
        layout.addWidget(self.status_label)

    def get_external_toolbar_menu(self, toolbar=None, menu=None):
        """ Only the action opening the manager: there is no entry to choose and nothing to execute """
        if toolbar is None:
            toolbar = QtWidgets.QToolBar('Ontology')
        if menu is None:
            menu = QtWidgets.QMenu('Ontology')
        self.affect_to(ManagerActions.OPEN, toolbar)
        self.affect_to(ManagerActions.OPEN, menu)
        return toolbar, menu

    def setup_actions(self) -> None:
        # one entry file per experiment, kept at each change: nothing to choose from, copy, create, delete, save,
        # reload or execute
        for action in (ManagerActions.LIST, ManagerActions.COPY, ManagerActions.NEW, ManagerActions.DELETE,
                       ManagerActions.SAVE, ManagerActions.RELOAD, ManagerActions.EXECUTE):
            self.get_action(action).setVisible(False)
        self.add_action('update_channels', 'Update channels', 'refresh', toolbar='management', auto_menu=True,
                        tip='Update the channels from the control modules of the Dashboard')
        self.add_action('recap', 'Recap', 'grid_on', toolbar='management', auto_menu=True,
                        tip='Show the table of the terms assigned to the channels')
        self.add_action('probe', 'Probe detectors', 'snap', toolbar='management', auto_menu=True,
                        tip='Do a snap of the detectors to find the channels they emit')

    def connect_things(self) -> None:
        self.connect_action('update_channels', self.update_channels_from_dashboard)
        self.connect_action('probe', self.probe)
        self.connect_action('recap', self.show_recap)

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

    # ---- the relations between the terms
    @property
    def hierarchy(self) -> TermHierarchy:
        return TermHierarchy(self.terms.values())

    def channels_of_concept(self, concept_iri: str) -> list[Channel]:
        """The channels whose assigned term is the concept or a kind of it (what the channels *mean*, not what
        they are called)"""
        hierarchy = self.hierarchy
        return [channel for channel in self.channels
                if (iri := self.assignment.get(channel.key)) and hierarchy.is_a(iri, concept_iri)]

    # ---- the annotation of the saved data
    def attach_worker(self, worker) -> None:
        """Annotate the data saved by the worker of an extension (it must have ``add_data_preparer``)"""
        worker.add_data_preparer(self._annotator)
        if worker not in self._ontology_savers:
            self._ontology_savers[worker] = make_ontology_saver(
                lambda: self.source, lambda: self.assignment,
                lambda: getattr(getattr(worker, '_app', None), 'h5saver', None))
        worker.add_data_preparer(self._ontology_savers[worker])
        if worker not in self._workers:
            self._workers.append(worker)

    def detach_worker(self, worker) -> None:
        worker.remove_data_preparer(self._annotator)
        worker.remove_data_preparer(self._ontology_savers.pop(worker, None))
        if worker in self._workers:
            self._workers.remove(worker)

    def quit_fun(self, *args, **kwargs):
        for worker in list(self._workers):
            self.detach_worker(worker)
        return super().quit_fun(*args, **kwargs)

    # ---- the recap
    def recap_rows(self) -> list[tuple[str, str, str, str]]:
        """(channel, term label, IRI, status) of each assigned channel"""
        return [(key, self._term_label(key), iri, self.status_of(key, self._kind_of_key(key)))
                for key, iri in sorted(self.assignment.values.items())]

    def _kind_of_key(self, key: str) -> str:
        for channel in self.channels:
            if channel.key == key:
                return channel.kind
        return ''

    def show_recap(self) -> None:
        rows = self.recap_rows()
        dialog = QtWidgets.QDialog(self.mainwindow)
        dialog.setWindowTitle('Assigned terms')
        table = QtWidgets.QTableWidget(len(rows), 4, dialog)
        table.setHorizontalHeaderLabels(['Channel', 'Term', 'IRI', 'Status'])
        for r, row in enumerate(rows):
            for c, text in enumerate(row):
                table.setItem(r, c, QtWidgets.QTableWidgetItem(text))
        table.horizontalHeader().setStretchLastSection(True)
        table.resizeColumnsToContents()
        QtWidgets.QVBoxLayout(dialog).addWidget(table)
        dialog.resize(800, 400)
        dialog.exec()

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
        if not Path(entry_path).is_file():  # the entry of a new experiment is only written with its first assignment
            self.assignment, source = Assignment(), None
        else:
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
        rows = [ChannelRow(key=channel.key, kind=channel.kind, name=channel.name, group=GROUP_TITLES[channel.kind],
                           module='' if channel.kind == ACTUATOR else channel.module,  # an actuator is its own channel
                           term_label=self._term_label(channel.key),
                           value_text=f'{channel.last_value} {channel.units}'.strip(),
                           status=self.status_of(channel.key, channel.kind))
                for channel in sorted(self.channels, key=lambda c: (c.kind != ACTUATOR, c.module))]
        known = {channel.key for channel in self.channels}
        rows += [ChannelRow(key=key, kind='', name=key, group=MISSING, term_label=self._term_label(key),
                            status='missing')  # assigned, but no such channel now
                 for key in sorted(set(self.assignment.values) - known)]
        self.channel_tree.set_rows(rows)

    def _on_double_clicked(self, item: QtWidgets.QTreeWidgetItem, _column: int = 0) -> None:
        key = self.channel_tree.key_of(item)
        if key is None or not self.terms:
            return
        kind = self.channel_tree.kind_of(item)
        picker = TermPicker(list(self.terms.values()), self.mainwindow, self.assignment.get(key), kind,
                            title=f'Term for {key}')
        if picker.exec():
            self.assign(key, picker.selected_iri)

    def assign(self, channel_key: str, iri: str) -> None:
        """Assign the term to the channel and keep the assignment in the current entry"""
        self.assignment.set(channel_key, iri)
        self.save_current_entry()
        self._refresh_tree()
