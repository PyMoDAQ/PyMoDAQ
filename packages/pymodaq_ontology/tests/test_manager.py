import pytest

from pymodaq_ontology import manager as manager_module
from pymodaq_ontology.channels import Channel
from pymodaq_ontology.channel_tree import KEY_ROLE
from pymodaq_ontology.manager import OntologyManager
from pymodaq_ontology.terms import ACTUATOR, DETECTOR

FIELD = 'http://example.org/moke#MagneticField'
DIODE = 'http://example.org/moke#PhotodiodeSignalA'

CHANNELS = [Channel('Balanced detector', DETECTOR, 'diodes', 'diode_A', 'V', '1.82'),
            Channel('Balanced detector', DETECTOR, 'diodes', 'diode_B', 'V', '1.79'),
            Channel('Magnet', ACTUATOR, units='mT', last_value='0')]


@pytest.fixture
def manager(qtbot, tmp_path, monkeypatch, source):
    monkeypatch.setattr(manager_module, 'get_set_config_dir', lambda name, user=False: tmp_path / name)
    (tmp_path / 'ontology').mkdir()
    manager = OntologyManager()
    qtbot.addWidget(manager.mainwindow)
    manager.set_source(source)
    manager.set_channels(CHANNELS)
    return manager


def rows(manager):
    """(group, channel, term) of each channel row of the tree"""
    found = []
    for i in range(manager.channel_tree.topLevelItemCount()):
        top = manager.channel_tree.topLevelItem(i)
        for j in range(top.childCount()):
            child = top.child(j)
            if child.data(0, KEY_ROLE) is not None:
                found.append((top.text(0), child.text(0), child.text(1)))
            for k in range(child.childCount()):
                leaf = child.child(k)
                found.append((top.text(0), f'{child.text(0)}: {leaf.text(0)}', leaf.text(1)))
    return found


def item(manager, key):
    return next(i for i in _all_items(manager.channel_tree) if i.data(0, KEY_ROLE) == key)


def _all_items(tree):
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        yield it
        stack.extend(it.child(i) for i in range(it.childCount()))


class TestTree:
    def test_actuators_then_detectors_grouped_by_module(self, manager):
        assert rows(manager) == [
            ('Actuators', 'Magnet', ''),
            ('Detectors', 'Balanced detector: diodes/diode_A', ''),
            ('Detectors', 'Balanced detector: diodes/diode_B', '')]

    def test_assign_shows_the_label_and_is_saved_in_the_entry(self, manager):
        manager.assign('Magnet', FIELD)

        assert ('Actuators', 'Magnet', 'Applied magnetic field') in rows(manager)
        assert FIELD in manager.entry_filepath.read_text()

    def test_status_led(self, manager):
        manager.assign('Magnet', FIELD)
        manager.assign('Balanced detector/diodes/diode_A', FIELD)  # a field is not meant for a detector

        assert manager.status_of('Magnet', ACTUATOR) == 'assigned'
        assert manager.status_of('Balanced detector/diodes/diode_A', DETECTOR) == 'incompatible'
        assert manager.status_of('Balanced detector/diodes/diode_B', DETECTOR) == 'none'

    def test_a_term_unknown_to_the_source_is_shown_as_its_iri(self, manager):
        manager.assign('Magnet', 'http://elsewhere/Term')
        assert ('Actuators', 'Magnet', 'http://elsewhere/Term') in rows(manager)
        assert manager.status_of('Magnet', ACTUATOR) == 'assigned'

    def test_assigned_channel_that_is_gone_is_listed_apart(self, manager):
        """A cable swap or a removed instrument: the assignment is kept and flagged"""
        manager.assign('Old detector/diodes/diode_A', DIODE)

        assert ('Not in the Dashboard', 'Old detector/diodes/diode_A', 'Photodiode signal A') in rows(manager)

    def test_clearing(self, manager):
        manager.assign('Magnet', FIELD)
        manager.assign('Magnet', '')
        assert ('Actuators', 'Magnet', '') in rows(manager)


class TestEntries:
    def test_entry_round_trip_restores_assignment_and_source(self, manager, qtbot, tmp_path, monkeypatch):
        manager.assign('Magnet', FIELD)
        path = manager.entry_filepath

        other = OntologyManager()
        qtbot.addWidget(other.mainwindow)
        other.load_entry(path)

        assert other.assignment.get('Magnet') == FIELD
        assert other.source.identifier == manager.source.identifier
        assert len(other.terms) == 3

    def test_unreadable_source_keeps_the_previous_terms(self, manager):
        from pymodaq_ontology.source_factory import SourceFactory
        assert not manager.set_source(SourceFactory.create('rdf', '/no/such/file.ttl'))
        assert len(manager.terms) == 3
        assert manager.source.location != '/no/such/file.ttl'


def test_double_click_opens_the_popup_and_assigns(manager, monkeypatch):
    class FakePicker:
        selected_iri = FIELD
        asked = None

        def __init__(self, terms, parent, current, kind, title):
            FakePicker.asked = (len(terms), current, kind, title)

        def exec(self):
            return True

    monkeypatch.setattr(manager_module, 'TermPicker', FakePicker)
    manager._on_double_clicked(item(manager, 'Magnet'))

    assert FakePicker.asked == (3, '', ACTUATOR, 'Term for Magnet')
    assert manager.assignment.get('Magnet') == FIELD


def test_double_click_on_a_group_does_nothing(manager, monkeypatch):
    monkeypatch.setattr(manager_module, 'TermPicker', lambda *a, **k: pytest.fail('no popup for a group'))
    manager._on_double_clicked(manager.channel_tree.topLevelItem(0))


class FakeWorker:
    def __init__(self):
        self.preparers = []

    def add_data_preparer(self, preparer):
        self.preparers.append(preparer)

    def remove_data_preparer(self, preparer):
        self.preparers.remove(preparer)


def test_attach_and_detach_worker(manager):
    worker = FakeWorker()
    manager.attach_worker(worker)
    assert len(worker.preparers) == 2  # annotation and excerpt of the ontology
    manager.detach_worker(worker)
    assert worker.preparers == []


def test_recap_rows(manager):
    manager.assign('Magnet', FIELD)
    rows_ = manager.recap_rows()
    assert rows_ == [('Magnet', 'Applied magnetic field', FIELD, 'assigned')]


def test_probe_and_update_buttons_are_in_the_window(manager):
    from qtpy import QtWidgets
    buttons = {b.text(): b for b in manager.main_widget.findChildren(QtWidgets.QPushButton)}
    assert {'Update channels', 'Probe detectors'} <= set(buttons)
    manager.status_label.setText('')
    buttons['Probe detectors'].click()  # no Dashboard here: the probe says there is nothing to probe
    assert manager.status_label.text() == 'There is no detector to probe'


def test_applying_a_new_experiment_does_not_need_an_entry_file(manager, tmp_path):
    manager.assign('Magnet', FIELD)
    # the entry of an experiment is read when it is applied, before anything was saved
    missing = tmp_path / 'never_saved' / 'default.ontology'
    manager._update_entry(missing)  # used to raise FileNotFoundError
    assert manager.assignment.get('Magnet') == ''
    assert manager.source is not None  # the ontology already loaded is kept


def test_a_single_entry_needs_no_entry_list(manager):
    from pymodaq_gui.managers.manager_base import ManagerActions
    for action in (ManagerActions.LIST, ManagerActions.COPY, ManagerActions.NEW, ManagerActions.DELETE,
                   ManagerActions.SAVE, ManagerActions.RELOAD, ManagerActions.EXECUTE):
        assert not manager.get_action(action).isVisible()
    toolbar, menu = manager.get_external_toolbar_menu()
    assert manager.get_action(ManagerActions.OPEN) in toolbar.actions()
    assert not any(a.text() == ManagerActions.LIST_EXTERNAL for a in toolbar.actions())


def test_the_entry_file_is_named_after_the_experiment(manager, tmp_path):
    assert manager.entry_path_from_name('spectro_lab_a') == tmp_path / 'ontology' / 'spectro_lab_a.ontology'
    (tmp_path / 'ontology' / 'spectro_lab_a.ontology').write_text('')
    assert manager.entries == ['spectro_lab_a']


def test_a_long_status_does_not_widen_the_window(manager):
    manager.mainwindow.show()
    width = manager.mainwindow.width()
    manager.status_label.setText('Could not read the ontology ' + 'very/long/path/' * 40)
    assert manager.status_label.wordWrap()
    assert manager.mainwindow.minimumSizeHint().width() < 2 * width
