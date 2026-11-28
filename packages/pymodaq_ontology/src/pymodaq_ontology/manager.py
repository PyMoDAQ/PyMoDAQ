"""The OntologyManager: assign the terms of an ontology to the channels of the instruments of the Dashboard"""
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from qtpy import QtWidgets

from pymodaq_utils.config import get_set_config_dir
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq_gui.messenger import messagebox

from pymodaq.control_modules.enums import ActionIconNames
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
        self.states_table = QtWidgets.QTableWidget(0, 3)
        self.states_table.setHorizontalHeaderLabels(['Actuator', 'Value', 'State'])
        self.states_table.horizontalHeader().setStretchLastSection(True)
        self.states_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.states_table.setToolTip('The value of an actuator, as configured, that stands for a state of the ontology')
        add_state = QtWidgets.QPushButton('Add state...')
        add_state.clicked.connect(self.add_state_dialog)
        remove_state = QtWidgets.QPushButton('Remove state')
        remove_state.clicked.connect(self.remove_selected_state)
        states_row = QtWidgets.QHBoxLayout()
        for widget in (QtWidgets.QLabel('States of the actuators:'), add_state, remove_state):
            states_row.addWidget(widget)
        states_row.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self.main_widget)
        layout.addLayout(source_row)
        layout.addLayout(buttons_row)
        layout.addWidget(self.channel_tree)
        layout.addLayout(states_row)
        layout.addWidget(self.states_table)
        layout.addWidget(self.status_label)

    def setup_actions(self) -> None:
        self.add_action('update_channels', 'Update channels', 'refresh', toolbar='management', auto_menu=True,
                        tip='Update the channels from the control modules of the Dashboard')
        self.add_action('recap', 'Recap', 'grid_on', toolbar='management', auto_menu=True,
                        tip='Show the table of the terms assigned to the channels')
        self.add_action('probe', 'Probe detectors', ActionIconNames.SNAP, toolbar='management', auto_menu=True,
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
        self._refresh_states()

    def _on_double_clicked(self, item: QtWidgets.QTreeWidgetItem, _column: int = 0) -> None:
        key = self.channel_tree.key_of(item)
        if key is None or not self.terms:
            return
        kind = self.channel_tree.kind_of(item)
        picker = TermPicker(list(self.terms.values()), self.mainwindow, self.assignment.get(key), kind,
                            title=f'Term for {key}')
        if picker.exec():
            self.assign(key, picker.selected_iri)

    # ---- the states of the actuators: a value of the actuator, as the user configured it, stands for a term
    def assign_state(self, actuator: str, value: float, iri: str) -> None:
        """Associate the state (term) with the value of the actuator and keep it in the current entry"""
        self.assignment.set_state(actuator, value, iri)
        self.save_current_entry()
        self._refresh_states()

    def remove_state(self, actuator: str, value: float) -> None:
        self.assign_state(actuator, value, '')

    def moves_for_states(self, wanted: list[str]) -> tuple[list[tuple[str, float]], list[str]]:
        """The moves to reach these states: (actuator, value) for each, and the states with no association

        The association of a state, or of a kind of it, is used: a value associated with ``Beam blocked`` serves
        for the state ``Beam blocked`` and for a more general state it is a kind of. This is how the extensions
        ask for what they need, in terms of the ontology, without knowing the values.
        """
        moves, missing = [], []
        for state in wanted:
            found = next((s for s in self.assignment.states if self.hierarchy.is_a(s.iri, state)), None)
            if found is None:
                missing.append(state)
            else:
                moves.append((found.actuator, found.value))
        return moves, missing

    def state_choices(self, actuator: str) -> list[OntologyTerm]:
        """The terms that can be the state of an actuator: the kinds of its term (all the terms with a role of
        actuator if it has none, or if nothing is a kind of it)"""
        iri = self.assignment.get(actuator)
        kinds = [self.terms[i] for i in self.hierarchy.descendants(iri) if i in self.terms] if iri else []
        return kinds or [term for term in self.terms.values() if term.fits(ACTUATOR)]

    def add_state_dialog(self) -> None:
        """One popup: the actuator (those with a term), its value and the state the value stands for"""
        actuators = [c for c in self.channels if c.kind == ACTUATOR and self.assignment.get(c.module)]
        if not actuators:
            self.status_label.setText('Assign a term to an actuator first')
            return
        dialog = QtWidgets.QDialog(self.mainwindow)
        dialog.setWindowTitle('State of an actuator')
        actuator_combo = QtWidgets.QComboBox()
        actuator_combo.addItems([c.module for c in actuators])
        value_spin = QtWidgets.QDoubleSpinBox()
        value_spin.setDecimals(6)
        value_spin.setRange(-1e12, 1e12)
        state_combo = QtWidgets.QComboBox()

        def actuator_changed() -> None:
            name = actuator_combo.currentText()
            state_combo.clear()
            for term in self.state_choices(name):
                state_combo.addItem(term.label, term.iri)
            last = next((c.last_value for c in actuators if c.module == name), '')
            try:
                value_spin.setValue(float(last))  # the current value of the actuator is the likely one
            except ValueError:
                pass

        actuator_combo.currentTextChanged.connect(lambda _: actuator_changed())
        actuator_changed()
        form = QtWidgets.QFormLayout(dialog)
        form.addRow('Actuator:', actuator_combo)
        form.addRow('Value:', value_spin)
        form.addRow('State:', state_combo)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                             QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() and state_combo.currentData():
            self.assign_state(actuator_combo.currentText(), value_spin.value(), state_combo.currentData())

    def remove_selected_state(self) -> None:
        row = self.states_table.currentRow()
        if 0 <= row < len(self.assignment.states):
            state = self.assignment.states[row]
            self.remove_state(state.actuator, state.value)

    def _refresh_states(self) -> None:
        table = self.states_table
        table.setRowCount(len(self.assignment.states))
        for row, state in enumerate(self.assignment.states):
            term = self.terms.get(state.iri)
            for column, text in enumerate((state.actuator, f'{state.value:g}', term.label if term else state.iri)):
                table.setItem(row, column, QtWidgets.QTableWidgetItem(text))

    def assign(self, channel_key: str, iri: str) -> None:
        """Assign the term to the channel and keep the assignment in the current entry"""
        self.assignment.set(channel_key, iri)
        self.save_current_entry()
        self._refresh_tree()
