from pymodaq_ontology.channels import Channel
from pymodaq_ontology.manager import OntologyManager
from pymodaq_ontology import manager as manager_module
from pymodaq_ontology.source_factory import SourceFactory
from pymodaq_ontology.term_picker import TermPicker
from pymodaq_ontology.terms import DETECTOR, OntologyTerm, TermHierarchy

NS = 'http://example.org/h#'
TERMS = [OntologyTerm(NS + 'Signal', 'Signal'),
         OntologyTerm(NS + 'Optical', 'Optical signal', broader=(NS + 'Signal',)),
         OntologyTerm(NS + 'Diode', 'Photodiode signal', broader=(NS + 'Optical',)),
         OntologyTerm(NS + 'Thermal', 'Thermal signal', broader=(NS + 'Signal',)),
         OntologyTerm(NS + 'Orphan', 'Unknown parent', broader=(NS + 'Missing',))]


def test_ancestors_descendants_and_is_a():
    h = TermHierarchy(TERMS)
    assert h.ancestors(NS + 'Diode') == [NS + 'Optical', NS + 'Signal']
    assert set(h.descendants(NS + 'Signal')) == {NS + 'Optical', NS + 'Diode', NS + 'Thermal'}
    assert h.is_a(NS + 'Diode', NS + 'Signal') and h.is_a(NS + 'Diode', NS + 'Diode')
    assert not h.is_a(NS + 'Signal', NS + 'Diode')
    assert set(h.roots()) == {NS + 'Signal', NS + 'Orphan'}  # an unknown parent is ignored


def test_a_loop_does_not_hang():
    h = TermHierarchy([OntologyTerm('a', 'A', broader=('b',)), OntologyTerm('b', 'B', broader=('a',))])
    assert h.ancestors('a') == ['b']
    assert h.is_a('a', 'b') and h.is_a('b', 'a')


def test_terms_file_reads_broader(tmp_path):
    path = tmp_path / 't.toml'
    path.write_text('[[term]]\niri = "a"\n[[term]]\niri = "b"\nbroader = ["a"]\n', encoding='utf-8')
    terms = SourceFactory.create('terms', str(path)).terms()
    assert terms[1].broader == ('a',) and terms[0].broader == ()


def test_picker_shows_the_terms_under_their_parent(qtbot):
    picker = TermPicker(TERMS)
    qtbot.addWidget(picker)
    top = {picker.tree.topLevelItem(i).text(0) for i in range(picker.tree.topLevelItemCount())}
    assert top == {'Signal', 'Unknown parent'}
    parents = {item.text(0): (parent.text(0) if parent else None) for parent, item in picker._leaves()}
    assert parents['Photodiode signal'] == 'Optical signal'
    picker.search.setText('photodiode')  # the parents of a match stay visible
    visible = {item.text(0) for _, item in picker._leaves() if not item.isHidden()}
    assert {'Signal', 'Optical signal', 'Photodiode signal'} <= visible and 'Thermal signal' not in visible


def test_channels_of_a_concept(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(manager_module, 'get_set_config_dir', lambda name, user=False: tmp_path / name)
    (tmp_path / 'ontology').mkdir()
    manager = OntologyManager()
    qtbot.addWidget(manager.mainwindow)
    manager.terms = {term.iri: term for term in TERMS}
    channels = [Channel('Det', DETECTOR, 'd', 'a'), Channel('Det', DETECTOR, 'd', 'b'),
                Channel('Det', DETECTOR, 'd', 'c')]
    manager.set_channels(channels)
    manager.assign(channels[0].key, NS + 'Diode')
    manager.assign(channels[1].key, NS + 'Thermal')
    assert manager.channels_of_concept(NS + 'Optical') == [channels[0]]
    assert manager.channels_of_concept(NS + 'Signal') == channels[:2]  # a channel without term is not in
