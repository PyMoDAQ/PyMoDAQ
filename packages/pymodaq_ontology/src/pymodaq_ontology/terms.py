"""The terms of an ontology as the manager sees them: a flat list, with no dependency on any ontology library"""
from dataclasses import dataclass

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
    """
    iri: str
    label: str
    category: str = ''
    description: str = ''
    roles: tuple[str, ...] = ()

    def fits(self, kind: str) -> bool:
        """Whether the term can describe a channel of this kind (detector or actuator)"""
        return not self.roles or kind in self.roles
