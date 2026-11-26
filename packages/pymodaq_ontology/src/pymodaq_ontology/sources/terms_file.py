"""Source reading the terms from a TOML file"""
from pathlib import Path

import toml

from pymodaq_ontology.source_factory import OntologySource, SourceFactory
from pymodaq_ontology.terms import OntologyTerm


@SourceFactory.register
class TermsFileSource(OntologySource):
    """A TOML file listing the terms, one ``[[term]]`` table each::

        [[term]]
        iri = "http://example.org/moke#KerrRotation"
        label = "Kerr rotation"
        category = "Derived quantity"      # optional
        description = "..."                # optional
        roles = ["detector"]               # optional: detector, actuator or both
    """
    source_type = 'terms'

    def terms(self) -> list[OntologyTerm]:
        content = toml.loads(Path(self.location).read_text(encoding='utf-8'))
        terms = []
        for item in content.get('term', []):
            roles = item.get('roles', [])
            terms.append(OntologyTerm(
                iri=item['iri'], label=item.get('label', item['iri']),
                category=item.get('category', ''), description=item.get('description', ''),
                roles=tuple(roles) if isinstance(roles, list) else (roles,)))
        return terms
