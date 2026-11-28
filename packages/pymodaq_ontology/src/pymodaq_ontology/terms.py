"""The terms of an ontology as the manager sees them: a flat list, with no dependency on any ontology library"""
from dataclasses import dataclass
from typing import Iterable

DETECTOR = 'detector'
ACTUATOR = 'actuator'
KINDS = (DETECTOR, ACTUATOR)


@dataclass(frozen=True)
class OntologyTerm:
    """A term of an ontology that can be assigned to a channel

    Attributes
    ----------
    iri: str
        The identifier of the term
    label: str
        What is shown to the user
    category: str
        Used to group the terms (for instance the class of the term)
    description: str
        Shown when the term is selected
    roles: tuple of str
        The kinds of channel the term is meant for (``'detector'``, ``'actuator'``). Empty when not known:
        the term then fits any channel.
    broader: tuple of str
        The IRIs of the terms this one is a kind of (its parents). Empty for a term without parent.
    is_state: bool
        The term is a state of a channel (like *Beam blocked*), not a channel: it can be associated with a value of
        an actuator but not assigned to a channel.
    """
    iri: str
    label: str
    category: str = ''
    description: str = ''
    roles: tuple[str, ...] = ()
    broader: tuple[str, ...] = ()
    is_state: bool = False

    def fits(self, kind: str) -> bool:
        """Whether the term can describe a channel of this kind (detector or actuator)"""
        return not self.roles or kind in self.roles


class TermHierarchy:
    """The *is a kind of* relation between terms (``broader``), to ask for what a term stands for

    Parents unknown to the ontology and loops are ignored.
    """

    def __init__(self, terms: Iterable[OntologyTerm]):
        self.terms: dict[str, OntologyTerm] = {term.iri: term for term in terms}
        self._children: dict[str, list[str]] = {iri: [] for iri in self.terms}
        for term in self.terms.values():
            for parent in term.broader:
                if parent in self.terms and parent != term.iri:
                    self._children[parent].append(term.iri)

    @property
    def has_relations(self) -> bool:
        return any(self._children.values())

    def parents(self, iri: str) -> list[str]:
        term = self.terms.get(iri)
        return [parent for parent in term.broader if parent in self.terms and parent != iri] if term else []

    def children(self, iri: str) -> list[str]:
        return list(self._children.get(iri, []))

    def roots(self) -> list[str]:
        """The terms without a (known) parent"""
        return [iri for iri in self.terms if not self.parents(iri)]

    def ancestors(self, iri: str) -> list[str]:
        """All the terms *iri* is a kind of, the closest first"""
        return self._walk(iri, self.parents)

    def descendants(self, iri: str) -> list[str]:
        """All the terms that are a kind of *iri*, the closest first"""
        return self._walk(iri, self.children)

    def is_a(self, iri: str, other: str) -> bool:
        """Whether *iri* is *other* or a kind of it"""
        return iri == other or other in self.ancestors(iri)

    @staticmethod
    def _walk(start: str, step) -> list[str]:
        found: list[str] = []
        queue = list(step(start))
        while queue:
            iri = queue.pop(0)
            if iri not in found and iri != start:
                found.append(iri)
                queue.extend(step(iri))
        return found
