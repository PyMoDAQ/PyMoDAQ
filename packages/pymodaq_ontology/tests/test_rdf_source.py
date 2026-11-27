import pytest

from pymodaq_ontology.source_factory import SourceFactory
from pymodaq_ontology.terms import ACTUATOR, DETECTOR, TermHierarchy

TURTLE = '''
@prefix ex: <http://example.org/o#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .

ex:Sensor a owl:Class ; rdfs:label "sensor"@en , "capteur"@fr ; skos:definition "Measures something."@en .
ex:Photodiode a owl:Class ; rdfs:subClassOf ex:Sensor , sosa:Sensor ; rdfs:label "photodiode"@en ;
    rdfs:comment "A diode sensitive to light." .
ex:NoLabel a owl:Class .
ex:KerrRotation a owl:NamedIndividual , sosa:ObservableProperty ; rdfs:label "Kerr rotation" .
ex:MagneticField a owl:NamedIndividual , sosa:ActuatableProperty ; rdfs:label "applied field" .
'''


@pytest.fixture
def terms(tmp_path):
    path = tmp_path / 'onto.ttl'
    path.write_text(TURTLE, encoding='utf-8')
    return {t.iri: t for t in SourceFactory.create('rdf', str(path)).terms()}


def test_classes_and_individuals_with_a_label_are_terms(terms):
    ns = 'http://example.org/o#'
    assert set(terms) == {ns + n for n in ('Sensor', 'Photodiode', 'KerrRotation', 'MagneticField')}
    assert terms[ns + 'Sensor'].label == 'sensor'  # the English label
    assert terms[ns + 'Sensor'].description == 'Measures something.'
    assert terms[ns + 'Photodiode'].description == 'A diode sensitive to light.'


def test_subclass_gives_broader_and_the_hierarchy_works(terms):
    ns = 'http://example.org/o#'
    assert ns + 'Sensor' in terms[ns + 'Photodiode'].broader
    h = TermHierarchy(terms.values())
    assert h.is_a(ns + 'Photodiode', ns + 'Sensor')  # the parent outside the file is ignored by the hierarchy


def test_roles_of_the_individuals(terms):
    ns = 'http://example.org/o#'
    assert terms[ns + 'KerrRotation'].roles == (DETECTOR,)
    assert terms[ns + 'MagneticField'].roles == (ACTUATOR,)
    assert terms[ns + 'Sensor'].roles == ()
