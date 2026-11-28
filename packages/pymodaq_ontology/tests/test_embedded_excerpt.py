import numpy as np
import toml
import pytest

from pymodaq_data.data import DataRaw, DataToExport
from pymodaq_data.h5modules.browsing import H5BrowserUtil
from pymodaq_data.h5modules.data_saving import DataBundle
from pymodaq_data.h5modules.saving import H5SaverLowLevel

try:  # the reader of the h5 browser comes with another change
    from pymodaq_data.h5modules import representations
except ImportError:
    representations = None

from pymodaq_ontology.annotation import save_ontology_in_file, make_ontology_saver
from pymodaq_ontology.assignment import Assignment

HIERARCHY = '''
@prefix : <http://example.org/o#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
<http://example.org/o> a owl:Ontology ; owl:versionInfo "1.2" .
:Signal a owl:Class ; rdfs:label "Signal" .
:Optical a owl:Class ; rdfs:subClassOf :Signal ; rdfs:label "Optical signal" .
:Photodiode a owl:Class ; rdfs:subClassOf :Optical ; rdfs:label "Photodiode" ;
    owl:equivalentClass <http://other.org/Diode> ; skos:definition "A diode." .
:Temperature a owl:Class ; rdfs:subClassOf :Signal ; rdfs:label "Temperature" .
'''
PHOTODIODE = 'http://example.org/o#Photodiode'


@pytest.fixture
def ontology_source(tmp_path):
    from pymodaq_ontology.source_factory import SourceFactory
    path = tmp_path / 'o.ttl'
    path.write_text(HIERARCHY, encoding='utf-8')
    return SourceFactory.create('rdf', str(path))


def test_excerpt_keeps_the_terms_their_ancestors_and_equivalents_only(ontology_source):
    text, info = ontology_source.excerpt([PHOTODIODE])
    assert 'Photodiode' in text and 'Optical signal' in text and 'Signal' in text
    assert 'Temperature' not in text  # not used, not an ancestor
    assert 'equivalentClass' in text and 'A diode.' in text
    assert info == {'iri': 'http://example.org/o', 'version': '1.2'}


def make_saver(path):
    h5 = H5SaverLowLevel()
    h5.init_file(file_name=path, new_file=True)
    return h5


def test_save_ontology_in_file_writes_a_group_with_a_string_dataset(ontology_source, tmp_path):
    path = tmp_path / 'f.h5'
    h5 = make_saver(path)
    assert save_ontology_in_file(h5, ontology_source, Assignment({'Det/x': PHOTODIODE}))
    h5.close_file()
    reader = H5BrowserUtil(backend='h5py')
    reader.init_file(file_name=path, new_file=False, mode='r')
    try:
        group = reader.root().children()['Ontology']
        assert group.attrs['format'] == 'turtle' and group.attrs['version'] == '1.2'
        assert 'assignment' in group.children()
        text = group.children()['excerpt'].read()
        assert 'Photodiode' in ''.join(t if isinstance(t, str) else bytes(t).decode() for t in text)
    finally:
        reader.close_file()


def test_nothing_saved_without_terms_or_file(ontology_source, tmp_path):
    h5 = make_saver(tmp_path / 'g.h5')
    assert not save_ontology_in_file(h5, ontology_source, Assignment())
    assert not save_ontology_in_file(None, ontology_source, Assignment({'a': PHOTODIODE}))
    assert 'Ontology' not in h5.root().children()
    h5.close_file()


def test_assignment_is_saved_even_without_a_source(tmp_path):
    path = tmp_path / 'k.h5'
    h5 = make_saver(path)
    assert save_ontology_in_file(h5, None, Assignment({'Det/x': PHOTODIODE}))
    h5.close_file()
    reader = H5BrowserUtil(backend='h5py')
    reader.init_file(file_name=path, new_file=False, mode='r')
    try:
        children = reader.root().children()['Ontology'].children()
        assert 'excerpt' not in children
        text = ''.join(t if isinstance(t, str) else bytes(t).decode() for t in children['assignment'].read())
    finally:
        reader.close_file()
    assert toml.loads(text) == {'assignments': {'Det/x': PHOTODIODE}}  # no source: its location stays private


def test_ontology_saver_acts_on_the_first_bundle_only(ontology_source, tmp_path):
    h5 = make_saver(tmp_path / 'h.h5')
    ontology_saver = make_ontology_saver(lambda: ontology_source, lambda: Assignment({'a': PHOTODIODE}), lambda: h5)
    dte = DataToExport('d', data=[DataRaw('x', data=[np.array([1.0])])])
    ontology_saver(DataBundle(dte, save_index=1))
    assert 'Ontology' not in h5.root().children()
    ontology_saver(DataBundle(dte, save_index=0))
    assert 'Ontology' in h5.root().children()
    h5.close_file()


@pytest.mark.skipif(not hasattr(representations, 'embedded_semantics'),
                    reason='needs the embedded ontology reader of the h5 browser')
def test_the_browser_provider_reads_what_the_manager_wrote(ontology_source, tmp_path):
    path = tmp_path / 'i.h5'
    h5 = make_saver(path)
    save_ontology_in_file(h5, ontology_source, Assignment({'a': PHOTODIODE}))
    h5.close_file()
    reader = H5BrowserUtil(backend='h5py')
    reader.init_file(file_name=path, new_file=False, mode='r')
    try:
        semantics = representations.embedded_semantics(reader.root())
    finally:
        reader.close_file()
    assert semantics.label(PHOTODIODE) == 'Photodiode'
    assert semantics.parent(PHOTODIODE) == 'http://example.org/o#Optical'
    assert semantics.canonical(PHOTODIODE) == semantics.canonical('http://other.org/Diode')


def test_states_of_the_actuators_are_part_of_the_saved_assignment(ontology_source, tmp_path):
    path = tmp_path / 'l.h5'
    h5 = make_saver(path)
    assignment = Assignment({'Det/x': PHOTODIODE})
    assignment.set_state('Shutter', 1.0, PHOTODIODE)
    assert save_ontology_in_file(h5, ontology_source, assignment)
    h5.close_file()
    reader = H5BrowserUtil(backend='h5py')
    reader.init_file(file_name=path, new_file=False, mode='r')
    try:
        node = reader.root().children()['Ontology'].children()['assignment']
        text = ''.join(t if isinstance(t, str) else bytes(t).decode() for t in node.read())
    finally:
        reader.close_file()
    assert toml.loads(text)['states'] == [{'actuator': 'Shutter', 'value': 1.0, 'term': PHOTODIODE}]
