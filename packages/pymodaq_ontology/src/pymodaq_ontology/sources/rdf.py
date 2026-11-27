"""Source reading the terms from an RDF file (Turtle, RDF/XML, JSON-LD...), with rdflib"""
from pathlib import Path

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from pymodaq_ontology.source_factory import OntologySource, SourceFactory
from pymodaq_ontology.terms import ACTUATOR, DETECTOR, OntologyTerm

SOSA = 'http://www.w3.org/ns/sosa/'
ROLES_OF_TYPE = {  # the classes whose individuals describe what a detector or an actuator deals with
    URIRef(SOSA + 'ObservableProperty'): DETECTOR,
    URIRef(SOSA + 'ActuatableProperty'): ACTUATOR,
}
LANGUAGES = ('en', '')  # the label language preferred, then a label without language


def _text(graph: Graph, subject: URIRef, predicates: tuple[URIRef, ...]) -> str:
    """The text of the first predicate that has one, in the preferred language"""
    for predicate in predicates:
        values = [o for o in graph.objects(subject, predicate) if isinstance(o, Literal)]
        for language in LANGUAGES:
            for value in values:
                if (value.language or '') == language:
                    return str(value)
        if values:
            return str(values[0])
    return ''


@SourceFactory.register
class RdfSource(OntologySource):
    """An RDF file, read with rdflib (the format is guessed from the extension). The terms are

    * the classes (``owl:Class``): ``rdfs:subClassOf`` gives their parents (``broader``)
    * the named individuals (``owl:NamedIndividual``): their classes are their parents. Those of type
      ``sosa:ObservableProperty`` are meant for detectors, those of type ``sosa:ActuatableProperty`` for actuators.

    The label is ``rdfs:label`` (English first), the description ``skos:definition`` or ``rdfs:comment``. Only the
    things with a label are terms: the others are structure of the ontology.
    """
    source_type = 'rdf'

    def terms(self) -> list[OntologyTerm]:
        graph = Graph()
        graph.parse(Path(self.location))
        subjects = [s for s in (*graph.subjects(RDF.type, OWL.Class), *graph.subjects(RDF.type, OWL.NamedIndividual))
                    if isinstance(s, URIRef)]
        terms = []
        seen = set()
        for subject in subjects:
            label = _text(graph, subject, (RDFS.label,))
            if not label or subject in seen:
                continue
            seen.add(subject)
            is_class = (subject, RDF.type, OWL.Class) in graph
            parents = graph.objects(subject, RDFS.subClassOf if is_class else RDF.type)
            parents = tuple(str(p) for p in parents if isinstance(p, URIRef) and p != OWL.NamedIndividual
                            and p != OWL.Class)
            roles = () if is_class else tuple(sorted({ROLES_OF_TYPE[t] for t in graph.objects(subject, RDF.type)
                                                      if t in ROLES_OF_TYPE}))
            terms.append(OntologyTerm(
                iri=str(subject), label=label,
                category='Classes' if is_class else 'Individuals',
                description=_text(graph, subject, (SKOS.definition, RDFS.comment)),
                roles=roles, broader=parents))
        return sorted(terms, key=lambda term: term.label.lower())
