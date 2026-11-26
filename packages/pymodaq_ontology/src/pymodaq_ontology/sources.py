"""Sources of ontology terms

A source reads the terms of an ontology from somewhere (a file, a web address...) in some format. The manager only
asks it for a list of :class:`~pymodaq_ontology.terms.OntologyTerm`. A format that needs a library (RDF/Turtle for
instance) is read by a source type provided by a plugin, which registers it with :meth:`SourceFactory.register` or
through the ``pymodaq.ontology_sources`` entry point group (the value is a module that registers its sources when
imported, or a source class).
"""
from abc import ABC, abstractmethod
from pathlib import Path

import toml

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import get_entrypoints

from pymodaq_ontology.terms import OntologyTerm

logger = set_logger(get_module_name(__file__))

GROUP = 'pymodaq.ontology_sources'


class OntologySource(ABC):
    """A place where to read the terms of an ontology

    Subclasses define ``source_type`` (the name used to create them) and :meth:`terms`.
    """
    source_type: str = NotImplemented

    def __init__(self, location: str):
        self.location = str(location)

    @property
    def identifier(self) -> str:
        """What identifies the source in the entry files, for instance ``terms:/path/to/file.toml``"""
        return f'{self.source_type}:{self.location}'

    @abstractmethod
    def terms(self) -> list[OntologyTerm]:
        """Read the terms. Raises an exception if the location cannot be read"""


class SourceFactory:
    """Registry of the source types"""
    _types: dict[str, type[OntologySource]] = {}
    _discovered = False

    @classmethod
    def register(cls, source_class: type[OntologySource]) -> type[OntologySource]:
        """Register a source type, to be used as a class decorator"""
        if source_class.source_type is NotImplemented:
            raise NotImplementedError(f'{source_class} does not define source_type')
        cls._types[source_class.source_type] = source_class
        return source_class

    @classmethod
    def _discover(cls) -> None:
        if cls._discovered:
            return
        cls._discovered = True
        for entry_point in get_entrypoints(group=GROUP):
            try:
                loaded = entry_point.load()
            except Exception as e:
                logger.exception(f'Could not load the ontology source {entry_point.name}: {e}')
                continue
            if isinstance(loaded, type) and issubclass(loaded, OntologySource):
                cls.register(loaded)

    @classmethod
    def types(cls) -> list[str]:
        """The names of the source types available"""
        cls._discover()
        return list(cls._types)

    @classmethod
    def create(cls, source_type: str, location: str) -> OntologySource:
        cls._discover()
        try:
            return cls._types[source_type](location)
        except KeyError:
            raise ValueError(f'Unknown ontology source type "{source_type}", available: {cls.types()}') from None

    @classmethod
    def from_identifier(cls, identifier: str) -> OntologySource:
        """Create a source from its identifier (``type:location``)"""
        source_type, _, location = identifier.partition(':')
        return cls.create(source_type, location)


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
