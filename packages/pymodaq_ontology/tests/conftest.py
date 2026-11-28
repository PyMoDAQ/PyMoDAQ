import pytest

from pymodaq_ontology.source_factory import SourceFactory

TERMS_FILE = '''
@prefix moke: <http://example.org/moke#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .

moke:PhotodiodeSignalA a owl:NamedIndividual , sosa:ObservableProperty ;
    rdfs:label "Photodiode signal A" ; rdfs:comment "Voltage of the first diode." .
moke:MagneticField a owl:NamedIndividual , sosa:ActuatableProperty ;
    rdfs:label "Applied magnetic field" ; rdfs:comment "Field applied to the sample." .
moke:SampleTemperature a owl:NamedIndividual ;
    rdfs:label "Sample temperature" .
'''


@pytest.fixture
def terms_path(tmp_path):
    path = tmp_path / 'moke.ttl'
    path.write_text(TERMS_FILE, encoding='utf-8')
    return path


@pytest.fixture
def source(terms_path):
    return SourceFactory.create('rdf', str(terms_path))
