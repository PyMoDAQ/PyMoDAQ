"""Semantics provider reading labels and the concept hierarchy from RDF files (Turtle, RDF/XML...).

Needs the optional dependency rdflib: ``pip install pymodaq_data[semantics]``. Use it with::

    from pymodaq_data.h5modules.representations import get_semantics, build_tree
    semantics = get_semantics('rdf', sources=['my_ontology.ttl', 'qudt_excerpt.ttl'])
    build_tree('file.h5', 'concept', semantics)

Sources are local files; nothing is ever downloaded unless the caller gives a URL.
"""
from pathlib import Path
from typing import Iterable, Optional, Union

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDFS, SKOS

from pymodaq_data.h5modules.representations import SemanticsBase, SemanticsFactory

LABEL_PREDICATES = (SKOS.prefLabel, RDFS.label)
LABEL_LANGUAGES = ('en', None, '')  # preferred languages, '' / None: untagged labels


@SemanticsFactory.register('rdf')
class RdfSemantics(SemanticsBase):
    """Labels (``skos:prefLabel`` then ``rdfs:label``, english or untagged) and parent concept
    (``rdfs:subClassOf``) of the terms described in the given RDF source(s)

    Parameters
    ----------
    sources: str, Path or an iterable of them
        local RDF files (the format is guessed from the extension) or URLs
    text: str
        RDF given as a string (the excerpt of an ontology embedded in an h5 file), in the given ``format``
    """

    def __init__(self, sources: Union[str, Path, Iterable[Union[str, Path]]] = (), text: str = '',
                 format: str = 'turtle'):
        super().__init__()
        self.graph = Graph()
        if isinstance(sources, (str, Path)):
            sources = [sources]
        for source in sources:
            self.graph.parse(str(source))
        if text:
            self.graph.parse(data=text, format=format)

    def knows(self, iri: str) -> bool:
        return (URIRef(iri), None, None) in self.graph

    def label(self, iri: str) -> str:
        for predicate in LABEL_PREDICATES:
            labels = [lab for lab in self.graph.objects(URIRef(iri), predicate)
                      if getattr(lab, 'language', None) in LABEL_LANGUAGES]
            if labels:
                return str(sorted(labels, key=lambda lab: (lab.language != 'en', str(lab)))[0])
        return super().label(iri)

    def parent(self, iri: str) -> Optional[str]:
        parents = sorted(str(p) for p in self.graph.objects(URIRef(iri), RDFS.subClassOf)
                         if isinstance(p, URIRef) and self.knows(str(p)))
        return parents[0] if parents else None

    def equivalents(self, iri: str) -> set:
        """The IRI and all those declared equivalent to it with ``owl:equivalentClass`` (either direction,
        transitive)"""
        found, todo = set(), [URIRef(iri)]
        while todo:
            term = todo.pop()
            if term in found:
                continue
            found.add(term)
            todo.extend(o for o in self.graph.objects(term, OWL.equivalentClass) if isinstance(o, URIRef))
            todo.extend(s for s in self.graph.subjects(OWL.equivalentClass, term) if isinstance(s, URIRef))
        return {str(t) for t in found}

    def canonical(self, iri: str) -> str:
        """The first IRI (alphabetical order) of the equivalent terms: the same whatever the term asked"""
        return min(self.equivalents(iri))
