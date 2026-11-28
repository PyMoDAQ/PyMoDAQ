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


STATES = '''
@prefix : <http://example.org/s#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix pq: <https://pymodaq.cnrs.fr/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
:Block a owl:Class ; rdfs:subClassOf sosa:ActuatableProperty ; rdfs:label "Beam block" .
:Blocked a owl:NamedIndividual , :Block ; rdfs:label "Beam blocked" .
:Open a owl:NamedIndividual , :Block ; rdfs:label "Beam open" .
:Block owl:equivalentClass [ a owl:Class ; owl:oneOf ( :Blocked :Open ) ] .
:Dark a owl:Class ; rdfs:label "Dark" ; pq:requiresState :Blocked .
'''
S = 'http://example.org/s#'


@pytest.fixture
def state_manager(manager, tmp_path):
    from pymodaq_ontology.source_factory import SourceFactory
    path = tmp_path / 'states.ttl'
    path.write_text(STATES, encoding='utf-8')
    manager.set_source(SourceFactory.create('rdf', str(path)))
    return manager


def test_a_value_of_an_actuator_stands_for_a_state(state_manager):
    """The values are whatever the user configured: the ontology only knows the states"""
    state_manager.assign_state('Magnet', 12.5, S + 'Blocked')
    state_manager.assign_state('Magnet', 3., S + 'Open')
    assert state_manager.moves_for_states([S + 'Blocked']) == ([('Magnet', 12.5)], [])
    assert state_manager.moves_for_states([S + 'Open', S + 'Blocked']) == ([('Magnet', 3.), ('Magnet', 12.5)], [])


def test_the_state_without_association_is_reported(state_manager):
    state_manager.assign_state('Magnet', 1., S + 'Open')
    assert state_manager.moves_for_states([S + 'Blocked']) == ([], [S + 'Blocked'])


def test_a_kind_of_the_state_serves_for_the_state(state_manager):
    state_manager.assign_state('Magnet', 1., S + 'Blocked')
    assert state_manager.moves_for_states([S + 'Block']) == ([('Magnet', 1.)], [])  # a blocked beam is a block state


def test_the_states_are_kept_in_the_entry_and_can_be_replaced(state_manager, tmp_path):
    from pymodaq_ontology.assignment import load_entry, save_entry
    state_manager.assign_state('Magnet', 1., S + 'Open')
    state_manager.assign_state('Magnet', 1., S + 'Blocked')  # same value: replaced
    assert [(s.value, s.iri) for s in state_manager.assignment.states] == [(1., S + 'Blocked')]
    path = tmp_path / 'e.ontology'
    save_entry(path, state_manager.assignment, state_manager.source)
    assignment, _ = load_entry(path)
    assert assignment.states == state_manager.assignment.states
    state_manager.remove_state('Magnet', 1.)
    assert state_manager.assignment.states == []


def test_the_states_choices_are_the_kinds_of_the_term_of_the_actuator(state_manager):
    state_manager.assign('Magnet', S + 'Block')
    assert {t.label for t in state_manager.state_choices('Magnet')} == {'Beam blocked', 'Beam open'}


def test_one_popup_sets_the_state_of_an_actuator(state_manager):
    from qtpy import QtWidgets, QtCore
    state_manager.assign('Magnet', S + 'Block')

    def fill_and_accept():
        dialog = QtWidgets.QApplication.activeModalWidget()
        combos = dialog.findChildren(QtWidgets.QComboBox)
        assert [combos[1].itemText(i) for i in range(combos[1].count())] == ['Beam blocked', 'Beam open']  # kinds only
        dialog.findChild(QtWidgets.QDoubleSpinBox).setValue(12.5)
        combos[1].setCurrentIndex(0)
        dialog.accept()

    QtCore.QTimer.singleShot(0, fill_and_accept)
    state_manager.add_state_dialog()
    assert [(s.actuator, s.value, s.iri) for s in state_manager.assignment.states] == [('Magnet', 12.5, S + 'Blocked')]


def test_a_state_needs_the_actuator_to_have_a_term(state_manager):
    state_manager.add_state_dialog()
    assert state_manager.status_label.text() == 'Assign a term to an actuator first'


def test_a_state_is_shown_in_the_picker_but_cannot_be_chosen(state_manager):
    from pymodaq_ontology.term_picker import TermPicker, IRI_ROLE
    from pymodaq_ontology.terms import ACTUATOR
    assert {t.iri: t.is_state for t in state_manager.terms.values()} == {
        S + 'Block': False, S + 'Blocked': True, S + 'Open': True, S + 'Dark': False}
    picker = TermPicker(list(state_manager.terms.values()), None, '', ACTUATOR)
    items = {item.data(0, IRI_ROLE): item for _, item in picker._leaves()}
    assert set(items) == {S + 'Block', S + 'Blocked', S + 'Open', S + 'Dark'}  # the hierarchy is complete
    assert items[S + 'Blocked'].parent() is items[S + 'Block']
    picker.tree.setCurrentItem(items[S + 'Blocked'])
    picker._accept()
    assert picker.selected_iri == ''
    picker.tree.setCurrentItem(items[S + 'Block'])
    picker._accept()
    assert picker.selected_iri == S + 'Block'


def test_the_picker_explains_the_states_only_when_it_shows_some(state_manager):
    from pymodaq_ontology.term_picker import TermPicker
    from pymodaq_ontology.terms import ACTUATOR
    with_states = TermPicker(list(state_manager.terms.values()), None, '', ACTUATOR)
    without = TermPicker([t for t in state_manager.terms.values() if not t.is_state], None, '', ACTUATOR)
    assert not with_states.legend.isHidden() and without.legend.isHidden()


def test_a_term_says_in_which_states_it_has_its_meaning(state_manager):
    assert state_manager.terms[S + 'Dark'].requires == (S + 'Blocked',)
    assert state_manager.terms[S + 'Block'].requires == ()
