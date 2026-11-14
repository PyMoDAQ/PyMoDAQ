"""Alternative representations (modes) of the content of a PyMoDAQ h5 file.

A *mode* turns the list of data nodes found in one or several h5 files into a tree to display.
Items of that tree that stand for a data node carry its h5 path (``RepItem.path``), the others
(a concept, a unit...) have ``path=None`` and are only grouping labels. A viewer therefore only has
to display the tree and, on double-click of an item having a path, show the same node as in the
standard hierarchical view: the data loading and display stay unchanged.

This module has no Qt and no RDF dependency: the grouping is read from the attributes already
saved on each data node (``semantic_iri``, ``quantity_kind``, ``unit_iri``, ``units``, see
``DataWithAxes.add_extra_attribute``).
"""
import html
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, Iterator, List, Optional

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import get_entrypoints

logger = set_logger(get_module_name(__file__))

SEMANTIC_IRI = 'semantic_iri'
QUANTITY_KIND = 'quantity_kind'
UNIT_IRI = 'unit_iri'
UNANNOTATED = 'Not annotated'


@dataclass
class DataInfo:
    """What a mode needs to know about one data node of a file."""
    path: str                     # h5 path of the node (what the viewer loads)
    label: str                    # name of the data
    file: str = ''                # file name, to tell apart nodes of several open files
    attrs: Dict[str, object] = field(default_factory=dict)  # all h5 attributes of the node


@dataclass
class RepItem:
    """A node of the displayed tree."""
    label: str
    path: Optional[str] = None    # h5 path if the item stands for a data node, else None
    tooltip: str = ''
    children: List['RepItem'] = field(default_factory=list)

    def walk(self) -> Iterator['RepItem']:
        yield self
        for child in self.children:
            yield from child.walk()

    def find(self, label: str) -> Optional['RepItem']:
        return next((c for c in self.children if c.label == label), None)

    def to_text(self, indent: int = 0) -> str:
        lines = ['  ' * indent + self.label + (f'  -> {self.path}' if self.path else '')]
        lines += [c.to_text(indent + 1) for c in self.children]
        return '\n'.join(lines)

    def to_html(self) -> str:
        """Collapsible HTML tree (``<details>``), data items show their h5 path"""
        label = html.escape(self.label)
        if not self.children:
            path = f' <code>{html.escape(self.path)}</code>' if self.path else ''
            return f'<div style="margin-left:1.2em">{label}{path}</div>'
        inner = ''.join(c.to_html() for c in self.children)
        return (f'<details open style="margin-left:1.2em"><summary><b>{label}</b></summary>'
                f'{inner}</details>')

    def __str__(self) -> str:
        return self.to_text()

    def _repr_html_(self) -> str:  # displayed by Jupyter when the item is the last expression of a cell
        return self.to_html()


def local_name(iri: str) -> str:
    """Last part of an IRI: ``https://x/spectro#DarkSpectrum`` -> ``DarkSpectrum``;
    ``unit:NUM`` -> ``NUM``."""
    return re.split(r'[#/:]', str(iri).rstrip('/#'))[-1]


def humanize(name: str) -> str:
    """``DarkSpectrum`` -> ``Dark spectrum``."""
    words = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', name)
    return words[:1].upper() + words[1:].lower() if words else words


class SemanticsBase:
    """What the modes need to know about the terms (IRIs) found in the files. The default one only reads the
    name of the IRI. A richer one (labels, class hierarchy from an ontology) can be registered with
    ``@SemanticsFactory.register('my_name')`` and selected with :func:`set_semantics`; PyMoDAQ itself needs
    no RDF library."""

    def label(self, iri: str) -> str:
        """Human readable name of a term"""
        return humanize(local_name(iri))

    def parent(self, iri: str) -> Optional[str]:
        """The more general concept of a term, None at the top (or if unknown)"""
        return None


class SemanticsFactory:
    """Registry of the :class:`SemanticsBase` providers, also filled by the ``pymodaq.h5_semantics``
    entry points"""
    providers: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        """Class decorator: ``@SemanticsFactory.register('my_ontology')``"""
        def inner_wrapper(provider: type) -> type:
            cls.providers[name] = provider
            return provider
        return inner_wrapper

    @classmethod
    def create(cls, name: str) -> SemanticsBase:
        if name not in cls.providers:
            raise ValueError(f'Unknown semantics provider "{name}", registered: {list(cls.providers)}')
        return cls.providers[name]()


class RepresentationModeFactory:
    """Registry of the representation modes: ``builder(infos) -> RepItem``, see :func:`register_mode`.
    Also filled by the ``pymodaq.h5_representations`` entry points."""
    builders: Dict[str, Callable[[List['DataInfo']], 'RepItem']] = {}
    titles: Dict[str, str] = {}


SemanticsFactory.register('default')(SemanticsBase)
_active_semantics = {'name': 'default', 'object': None}
_entry_points_loaded = False


def _load_entry_points():
    """Import the plugins registering modes or semantics providers (once)"""
    global _entry_points_loaded
    if not _entry_points_loaded:
        _entry_points_loaded = True
        for group in ('pymodaq.h5_representations', 'pymodaq.h5_semantics'):
            for entry_point in get_entrypoints(group):
                try:
                    entry_point.load()
                except Exception as e:  # a broken plugin must not break the browser
                    logger.warning(f'Could not load {entry_point.name} from {group}: {e}')


def set_semantics(name: str = 'default') -> None:
    """Select the registered provider used by the modes to label and order terms"""
    _load_entry_points()
    _active_semantics.update(name=name, object=SemanticsFactory.create(name))


def semantics() -> SemanticsBase:
    if _active_semantics['object'] is None:
        set_semantics(_active_semantics['name'])
    return _active_semantics['object']


def iri_label(iri: str) -> str:
    return semantics().label(iri)


def data_infos(root, file: str = '') -> List[DataInfo]:
    """All data nodes (``data_type == 'data'``) below ``root``, a pymodaq_data h5 group
    (e.g. ``H5BrowserUtil.root()``)."""
    infos: List[DataInfo] = []

    def visit(node):
        attrs_name = node.attrs.attrs_name
        if node.attrs['CLASS'] == 'GROUP':
            for child in node.children().values():
                visit(child)
        elif 'data_type' in attrs_name and node.attrs['data_type'] == 'data':
            attrs = {name: node.attrs[name] for name in attrs_name}
            infos.append(DataInfo(node.path, str(attrs.get('label', node.name)), file, attrs))

    visit(root)
    return infos


def _leaf(info: DataInfo, multi_file: bool) -> RepItem:
    label = f'{info.label} [{info.file}]' if multi_file and info.file else info.label
    return RepItem(label, info.path, tooltip=info.path)


def _group_by(infos: List[DataInfo], key: Callable[[DataInfo], str], label: Callable[[str], str],
              multi_file: bool) -> List[RepItem]:
    groups: Dict[str, RepItem] = {}
    for info in infos:
        k = key(info)
        if k not in groups:
            groups[k] = RepItem(label(k) if k else UNANNOTATED, tooltip=k)
        groups[k].children.append(_leaf(info, multi_file))
    # annotated groups sorted by label, not annotated last
    return sorted(groups.values(), key=lambda g: (g.label == UNANNOTATED, g.label))


def concept_mode(infos: List[DataInfo]) -> RepItem:
    """Data grouped by what they are (``semantic_iri``), under their more general concepts if the active
    semantics provider knows them."""
    multi = len({i.file for i in infos}) > 1
    root = RepItem('By concept')
    nodes: Dict[str, RepItem] = {}

    def concept_item(iri: str) -> RepItem:
        if iri not in nodes:
            nodes[iri] = RepItem(iri_label(iri), tooltip=iri)
            parent = semantics().parent(iri)
            (concept_item(parent) if parent and parent != iri else root).children.append(nodes[iri])
        return nodes[iri]

    unannotated = RepItem(UNANNOTATED)
    for info in infos:
        iri = str(info.attrs.get(SEMANTIC_IRI, ''))
        (concept_item(iri) if iri else unannotated).children.append(_leaf(info, multi))
    _sort(root)
    if unannotated.children:
        root.children.append(unannotated)
    return root


def _sort(item: RepItem) -> None:
    """Sub-concepts first, then data, each by label"""
    item.children.sort(key=lambda c: (c.path is not None, c.label))
    for child in item.children:
        _sort(child)


def quantity_mode(infos: List[DataInfo]) -> RepItem:
    """Data grouped by quantity kind, then by unit."""
    multi = len({i.file for i in infos}) > 1
    root = RepItem('By quantity and unit')
    by_qk: Dict[str, List[DataInfo]] = {}
    for info in infos:
        by_qk.setdefault(str(info.attrs.get(QUANTITY_KIND, '')), []).append(info)
    for qk in sorted(by_qk, key=lambda k: (k == '', iri_label(k))):
        item = RepItem(iri_label(qk) if qk else UNANNOTATED, tooltip=qk)

        def unit_of(i: DataInfo) -> str:
            return str(i.attrs.get(UNIT_IRI) or i.attrs.get('units') or '')

        item.children = _group_by(by_qk[qk], unit_of,
                                  lambda u: local_name(u) if ':' in u or '/' in u else u, multi)
        root.children.append(item)
    return root


def build_tree(files, mode: str = 'concept') -> RepItem:
    """Tree of one or several PyMoDAQ h5 files in the given mode (see ``mode_names()``), for scripts and
    notebooks. In a notebook, ending a cell with the returned item displays it as a collapsible tree.

    Parameters
    ----------
    files: str, Path or an iterable of them
    mode: name of a registered mode
    """
    from pathlib import Path
    from pymodaq_data.h5modules.browsing import H5BrowserUtil
    if isinstance(files, (str, Path)):
        files = [files]
    infos: List[DataInfo] = []
    for file in files:
        h5 = H5BrowserUtil(backend='h5py')
        h5.init_file(file_name=Path(file), new_file=False, mode='r')
        try:
            infos += data_infos(h5.root(), Path(file).stem)
        finally:
            h5.close_file()
    return build_mode(mode, infos)


def register_mode(name: str, title: str):
    """Decorator registering a representation mode. The decorated function maps the data nodes of the
    open file(s) to a tree: ``builder(infos: List[DataInfo]) -> RepItem``.

    Examples
    --------
    ::

        @register_mode('flat', 'All data')
        def flat(infos):
            return RepItem('All', children=[RepItem(i.label, i.path) for i in infos])
    """
    def inner_wrapper(builder: Callable[[List[DataInfo]], RepItem]):
        RepresentationModeFactory.builders[name] = builder
        RepresentationModeFactory.titles[name] = title
        return builder
    return inner_wrapper


def mode_names() -> List[str]:
    """Names of the registered modes (also loads those declared by entry points)"""
    _load_entry_points()
    return list(RepresentationModeFactory.builders)


def mode_title(name: str) -> str:
    return RepresentationModeFactory.titles.get(name, name)


def build_mode(name: str, infos: List[DataInfo]) -> RepItem:
    _load_entry_points()
    if name not in RepresentationModeFactory.builders:
        raise ValueError(f'Unknown representation mode "{name}", registered: {mode_names()}')
    return RepresentationModeFactory.builders[name](infos)


register_mode('concept', 'By concept')(concept_mode)
register_mode('quantity', 'By quantity and unit')(quantity_mode)
