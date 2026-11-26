"""The assignment of ontology terms to channels, and its entry file"""
from pathlib import Path
from typing import Optional

import toml

from pymodaq_ontology.source_factory import OntologySource, SourceFactory


class Assignment:
    """Channel key -> IRI of the term assigned to it"""

    def __init__(self, values: Optional[dict[str, str]] = None):
        self.values: dict[str, str] = dict(values or {})

    def get(self, key: str) -> str:
        return self.values.get(key, '')

    def set(self, key: str, iri: str) -> None:
        if iri:
            self.values[key] = iri
        else:
            self.values.pop(key, None)


def save_entry(path: Path, assignment: Assignment, source: Optional[OntologySource] = None) -> None:
    """Write the entry file: the source the terms come from and the assignment"""
    content: dict = {'assignments': dict(sorted(assignment.values.items()))}
    if source is not None:
        content['source'] = {'type': source.source_type, 'location': source.location}
    Path(path).write_text(toml.dumps(content), encoding='utf-8')


def load_entry(path: Path) -> tuple[Assignment, Optional[OntologySource]]:
    """Read an entry file. The source is None if the file does not name one or if its type is unknown"""
    content = toml.loads(Path(path).read_text(encoding='utf-8'))
    assignment = Assignment(content.get('assignments', {}))
    source = None
    if 'source' in content:
        try:
            source = SourceFactory.create(content['source'].get('type', ''), content['source'].get('location', ''))
        except ValueError:
            source = None
    return assignment, source
