"""The assignment of ontology terms to channels, and its entry file"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import toml

from pymodaq_ontology.source_factory import OntologySource, SourceFactory


@dataclass(frozen=True)
class StateAssociation:
    """A value of an actuator, as the user configured it (a custom number: 1, 0, 12.5...), standing for a state: the
    term of the ontology that says what the value means (``Beam blocked``)"""
    actuator: str
    value: float
    iri: str


class Assignment:
    """Channel key -> IRI of the term assigned to it, and the states associated with the values of the actuators"""

    def __init__(self, values: Optional[dict[str, str]] = None, states: Optional[list[StateAssociation]] = None):
        self.values: dict[str, str] = dict(values or {})
        self.states: list[StateAssociation] = list(states or [])

    def set_state(self, actuator: str, value: float, iri: str) -> None:
        """Associate the state with the value of the actuator (an empty IRI removes the association)"""
        self.states = [s for s in self.states if not (s.actuator == actuator and s.value == value)]
        if iri:
            self.states.append(StateAssociation(actuator, float(value), iri))

    def get(self, key: str) -> str:
        return self.values.get(key, '')

    def set(self, key: str, iri: str) -> None:
        if iri:
            self.values[key] = iri
        else:
            self.values.pop(key, None)


def save_entry(path: Path, assignment: Assignment, source: Optional[OntologySource] = None) -> None:
    """Write the entry file: the source the terms come from and the assignment"""
    content = assignment_content(assignment)
    if source is not None:
        content['source'] = {'type': source.source_type, 'location': source.location}
    Path(path).write_text(toml.dumps(content), encoding='utf-8')


def assignment_content(assignment: Assignment) -> dict:
    """What the entry file (and the copy of the assignment saved in the data files) holds of an assignment"""
    content: dict = {'assignments': dict(sorted(assignment.values.items()))}
    if assignment.states:
        content['states'] = [{'actuator': s.actuator, 'value': s.value, 'term': s.iri} for s in assignment.states]
    return content


def assignment_text(assignment: Assignment) -> str:
    """The assignment as TOML text, as in the entry file but without the source (its location is the business of
    the user's machine)"""
    return toml.dumps(assignment_content(assignment))


def load_entry(path: Path) -> tuple[Assignment, Optional[OntologySource]]:
    """Read an entry file. The source is None if the file does not name one or if its type is unknown"""
    content = toml.loads(Path(path).read_text(encoding='utf-8'))
    states = [StateAssociation(str(s['actuator']), float(s['value']), str(s['term']))
              for s in content.get('states', [])]
    assignment = Assignment(content.get('assignments', {}), states)
    source = None
    if 'source' in content:
        try:
            source = SourceFactory.create(content['source'].get('type', ''), content['source'].get('location', ''))
        except ValueError:
            source = None
    return assignment, source
