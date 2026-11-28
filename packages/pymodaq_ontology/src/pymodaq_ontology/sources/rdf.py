"""Source reading the terms from an RDF file (Turtle, RDF/XML, JSON-LD...), with rdflib"""
from pathlib import Path
from typing import Iterable, Optional

from rdflib import Graph, URIRef, Literal
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from pymodaq_ontology.source_factory import OntologySource, SourceFactory
from pymodaq_ontology.terms import ACTUATOR, DETECTOR, OntologyTerm

SOSA = 'http://www.w3.org/ns/sosa/'
ROLES_OF_TYPE = {  # the classes whose individuals describe what a detector or an actuator deals with
    URIRef(SOSA + 'ObservableProperty'): DETECTOR,
    URIRef(SOSA + 'ActuatableProperty'): ACTUATOR,
}
EXCERPT_PREDICATES = (RDF.type, RDFS.label, SKOS.prefLabel, SKOS.definition, RDFS.comment, RDFS.subClassOf,
                      OWL.equivalentClass)  # what the saved excerpt keeps of a term
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


def _roles(graph: Graph, subject: URIRef, is_class: bool) -> tuple[str, ...]:
    """The kinds of channel the term is meant for: it (or its class) is a kind of observable or actuatable property"""
    classes = [subject] if is_class else list(graph.objects(subject, RDF.type))
    ancestors = {a for c in classes for a in graph.transitive_objects(c, RDFS.subClassOf)}
    return tuple(sorted({ROLES_OF_TYPE[a] for a in ancestors if a in ROLES_OF_TYPE}))


@SourceFactory.register
class RdfSource(OntologySource):
    """An RDF file, read with rdflib (the format is guessed from the extension). The terms are

    * the classes (``owl:Class``): ``rdfs:subClassOf`` gives their parents (``broader``)
    * the named individuals (``owl:NamedIndividual``): their classes are their parents.

    A term that is (or whose class is) a kind of ``sosa:ObservableProperty`` is meant for detectors, a kind of
    ``sosa:ActuatableProperty`` for actuators. A member of an enumeration (``owl:oneOf``) is a
    value of a property, a *state* of an actuator (*Beam blocked* in the enumeration that defines *Beam block*), not a
    term for a channel.

    The label is ``rdfs:label`` (English first), the description ``skos:definition`` or ``rdfs:comment``. Only the
    things with a label are terms: the others are structure of the ontology.
    """
    source_type = 'rdf'

    def __init__(self, location: str):
        super().__init__(location)
        self.graph: Optional[Graph] = None

    def _read(self) -> Graph:
        """The graph of the file, read once and kept: the questions on the terms are asked to it"""
        if self.graph is None:
            graph = Graph()
            graph.parse(Path(self.location))
            self.graph = graph
        return self.graph

    def terms(self) -> list[OntologyTerm]:
        self.graph = None  # read the file again, it may have changed
        graph = self._read()
        subjects = [s for s in (*graph.subjects(RDF.type, OWL.Class), *graph.subjects(RDF.type, OWL.NamedIndividual))
                    if isinstance(s, URIRef)]
        states = {member for values in graph.objects(None, OWL.oneOf) for member in Collection(graph, values)}
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
            roles = _roles(graph, subject, is_class)
            terms.append(OntologyTerm(
                iri=str(subject), label=label,
                category='Classes' if is_class else 'Individuals',
                description=_text(graph, subject, (SKOS.definition, RDFS.comment)),
                roles=roles, broader=parents, is_state=subject in states))
        return sorted(terms, key=lambda term: term.label.lower())

    def excerpt(self, iris: Iterable[str]) -> tuple[str, dict[str, str]]:
        """What the file says about these terms, their more general terms and their equivalents (label, definition,
        parents, equivalences), in Turtle, with the IRI and the version of the ontology if the file gives them"""
        graph = self._read()
        wanted = {URIRef(iri) for iri in iris}
        closure = set()
        for term in wanted:
            for parent in (*graph.transitive_objects(term, RDFS.subClassOf), *graph.objects(term, RDF.type)):
                closure.update(graph.transitive_objects(parent, RDFS.subClassOf))
            closure.update(graph.transitive_objects(term, RDFS.subClassOf))
        for term in list(closure):  # the terms declared equivalent, whichever way the statement is written
            closure.update(graph.transitive_objects(term, OWL.equivalentClass))
            closure.update(graph.transitive_subjects(OWL.equivalentClass, term))
        closure = {t for t in closure if isinstance(t, URIRef)} | wanted
        out = Graph()
        for prefix, namespace in graph.namespaces():
            out.bind(prefix, namespace)
        for term in closure:
            for predicate in EXCERPT_PREDICATES:
                for obj in graph.objects(term, predicate):
                    out.add((term, predicate, obj))
        info = {}
        ontology = next(iter(graph.subjects(RDF.type, OWL.Ontology)), None)
        if isinstance(ontology, URIRef):
            info['iri'] = str(ontology)
            version = next(iter(graph.objects(ontology, OWL.versionIRI)), None) or \
                next(iter(graph.objects(ontology, OWL.versionInfo)), None)
            if version is not None:
                info['version'] = str(version)
        return out.serialize(format='turtle'), info
