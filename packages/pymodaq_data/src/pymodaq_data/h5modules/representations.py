"""Alternative representations (modes) of the content of a PyMoDAQ h5 file.

A *mode* turns the list of data nodes found in one or several h5 files into a tree to display.
Items of that tree that stand for a node carry its h5 path (``RepItem.path``), the others
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
HIERARCHY_MODE = 'hdf5'  # the standard hierarchy of the file, built by hierarchy_tree, not a registered mode


@dataclass
class DataInfo:
    """What a mode needs to know about one data or axis node of a file."""
    path: str                     # h5 path of the node (what the viewer loads)
    label: str                    # name of the data or of the axis
    file: str = ''                # file name, to tell apart nodes of several open files
    attrs: Dict[str, object] = field(default_factory=dict)  # all h5 attributes of the node
    kind: str = 'data'            # 'data' or 'axis'
    owner: str = ''               # axis only: label of the data stored next to it
    role: str = ''                # axis only: 'signal' or 'navigation' (a scan axis), '' if unknown


@dataclass
class RepItem:
    """A node of the displayed tree."""
    label: str
    path: Optional[str] = None    # h5 path if the item stands for a node (data or group), else None
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
    ``@SemanticsFactory.register('my_name')`` and passed to the modes (``semantics`` argument); PyMoDAQ itself
    needs no RDF library."""

    def knows(self, iri: str) -> bool:
        """True if the provider has its own information on this term (used by :class:`CompositeSemantics`)"""
        return False

    def label(self, iri: str) -> str:
        """Human readable name of a term"""
        return humanize(local_name(iri))

    def parent(self, iri: str) -> Optional[str]:
        """The more general concept of a term, None at the top (or if unknown)"""
        return None

    def canonical(self, iri: str) -> str:
        """The term standing for all the terms declared equivalent to this one (``owl:equivalentClass``), so that
        data annotated with two vocabularies are shown together. The same IRI when there is no equivalent."""
        return iri


class CompositeSemantics(SemanticsBase):
    """Several providers used together (e.g. one ontology per technique): each term is answered by the first
    provider that knows it, otherwise by the default behaviour."""

    def __init__(self, providers: Iterable[SemanticsBase]):
        self.providers = list(providers)

    def _provider_of(self, iri: str) -> Optional[SemanticsBase]:
        return next((p for p in self.providers if p.knows(iri)), None)

    def knows(self, iri: str) -> bool:
        return self._provider_of(iri) is not None

    def label(self, iri: str) -> str:
        provider = self._provider_of(iri)
        return provider.label(iri) if provider else super().label(iri)

    def parent(self, iri: str) -> Optional[str]:
        provider = self._provider_of(iri)
        return provider.parent(iri) if provider else None

    def canonical(self, iri: str) -> str:
        provider = self._provider_of(iri)
        return provider.canonical(iri) if provider else iri


class SemanticsFactory:
    """Registry of the :class:`SemanticsBase` providers, also filled by the ``pymodaq.h5_semantics``
    entry points"""
    providers: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        """Class decorator: ``@SemanticsFactory.register('my_ontology')``"""
        def inner_wrapper(provider: type) -> type:
            if name in cls.providers:
                logger.warning(f'The semantics provider "{name}" is already registered. Replacing it')
            cls.providers[name] = provider
            return provider
        return inner_wrapper

    @classmethod
    def create(cls, name: str, **kwargs) -> SemanticsBase:
        if name not in cls.providers:
            raise ValueError(f'Unknown semantics provider "{name}", registered: {list(cls.providers)}')
        return cls.providers[name](**kwargs)


class RepresentationModeFactory:
    """Registry of the representation modes: ``builder(infos, semantics) -> RepItem``, see :func:`register_mode`.
    Also filled by the ``pymodaq.h5_representations`` entry points."""
    builders: Dict[str, Callable[..., 'RepItem']] = {}
    titles: Dict[str, str] = {}


SemanticsFactory.register('default')(SemanticsBase)
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


def semantics_names() -> List[str]:
    """Names of the registered semantics providers that can be created without argument, for a selector
    (not 'default', the behaviour without ontology, nor 'rdf' that needs sources)"""
    _load_entry_points()
    return [name for name in SemanticsFactory.providers if name not in ('default', 'rdf')]


def get_semantics(name: str = 'default', **kwargs) -> SemanticsBase:
    """Instance of a registered semantics provider (also loads those declared by entry points).

    ``kwargs`` go to the provider, e.g. ``get_semantics('rdf', sources='my_ontology.ttl')``
    """
    _load_entry_points()
    if name == 'rdf' and name not in SemanticsFactory.providers:
        try:
            from pymodaq_data.h5modules import semantics_rdf  # noqa: F401  (registers the provider)
        except ImportError as e:
            raise ImportError('The "rdf" semantics provider needs rdflib: pip install rdflib') from e
    return SemanticsFactory.create(name, **kwargs)


EMBEDDED_GROUP = 'Ontology'  # group of the root holding the excerpt of the ontology used when saving
EMBEDDED_ATTRIBUTES = ('excerpt', 'format')  # RDF text and its format (default turtle); also 'iri', 'version'


def embedded_semantics(root, on_error: Optional[Callable[[Exception], None]] = None) -> Optional[SemanticsBase]:
    """The provider built from the excerpt of ontology saved in the file (group ``Ontology`` of the root with the
    attributes ``excerpt``, the RDF text, and optionally ``format``), None if the file has none or if it cannot
    be read (damaged text...). The file then explains itself, whatever happens to the original ontology.
    ``on_error`` is called with the exception when an excerpt exists but cannot be read."""
    try:
        group = root.children().get(EMBEDDED_GROUP)
        if group is None or 'excerpt' not in group.attrs.attrs_name:
            return None
        attrs = {name: str(group.attrs[name]) for name in group.attrs.attrs_name}
        return get_semantics('rdf', text=attrs['excerpt'], format=attrs.get('format', 'turtle'))
    except Exception as e:  # the embedded ontology is a help, never an obstacle
        logger.warning(f'Could not read the ontology embedded in the file: {e}')
        if on_error is not None:
            on_error(e)
        return None


def data_infos(root, file: str = '') -> List[DataInfo]:
    """All data nodes (``data_type == 'data'``) and axis nodes (``'axis'``, ``kind='axis'``) below
    ``root``, a pymodaq_data h5 group (e.g. ``H5BrowserUtil.root()``)."""
    infos: List[DataInfo] = []

    def data_type(node) -> str:
        if node.attrs['CLASS'] != 'GROUP' and 'data_type' in node.attrs.attrs_name:
            return str(node.attrs['data_type'])
        return ''

    def info_of(node, **kwargs) -> DataInfo:
        attrs = {name: node.attrs[name] for name in node.attrs.attrs_name}
        return DataInfo(node.path, str(attrs.get('label', node.name)), file, attrs, **kwargs)

    def visit(node):
        if node.attrs['CLASS'] == 'GROUP':
            children = list(node.children().values())
            owner = next((c for c in children if data_type(c) == 'data'), None)
            for child in children:
                kind = data_type(child)
                if kind == 'data':
                    infos.append(info_of(child))
                elif kind == 'axis':
                    infos.append(info_of(child, kind='axis', **_axis_context(child, owner)))
                else:
                    visit(child)

    visit(root)
    return infos


def hierarchy_tree(root, file: str = '') -> RepItem:
    """The standard hierarchy of the file (every node, groups included) with the explicit names of the
    h5browser (see :func:`explicit_node_name`); each item keeps the h5 path of its node."""
    def visit(node, name: str) -> RepItem:
        item = RepItem(explicit_node_name(name, node), node.path, tooltip=node.path)
        if node.attrs['CLASS'] == 'GROUP':
            item.children = [visit(child, child_name) for child_name, child in node.children().items()]
        return item

    top = RepItem(file or 'file', root.path)
    top.children = [visit(child, name) for name, child in root.children().items()]
    return top


def _axis_context(axis, owner) -> dict:
    """Label of the data stored next to an axis and whether it is a signal or a navigation axis"""
    if owner is None:
        return {}
    context = {'owner': str(owner.attrs['label']) if 'label' in owner.attrs.attrs_name else owner.name}
    try:
        if 'nav_indexes' in owner.attrs.attrs_name and 'index' in axis.attrs.attrs_name:
            nav = [int(i) for i in owner.attrs['nav_indexes']]
            context['role'] = 'navigation' if int(axis.attrs['index']) in nav else 'signal'
    except Exception:
        pass
    return context


def explicit_node_name(name: str, node) -> str:
    """Name of an h5 node as shown in the standard hierarchy, completed with what the node holds:
    ``Data00`` -> ``Data00 · background [counts]``, ``Axis00`` -> ``Axis00 · Wavelength [nm]`` and a group
    holding data ``CH00`` -> ``CH00 · background``. Other nodes keep their name.

    Parameters
    ----------
    name: the name of the node
    node: a pymodaq_data h5 node (attributes are read, the data are not)
    """
    def label_unit(n) -> str:
        attrs = n.attrs
        text = str(attrs['label']) if 'label' in attrs.attrs_name else ''
        unit = str(attrs['units']) if 'units' in attrs.attrs_name else ''
        return text + (f' [{unit}]' if unit and text else '')

    try:
        attrs_name = node.attrs.attrs_name
        if node.attrs['CLASS'] == 'GROUP':
            held = [str(c.attrs['label']) for c in node.children().values()
                    if c.attrs['CLASS'] != 'GROUP' and 'data_type' in c.attrs.attrs_name
                    and c.attrs['data_type'] == 'data' and 'label' in c.attrs.attrs_name]
            return f'{name} · {", ".join(held)}' if held else name
        if 'data_type' in attrs_name and node.attrs['data_type'] in ('data', 'axis'):
            text = label_unit(node)
            return f'{name} · {text}' if text else name
    except Exception:  # an explicit name is a convenience, never a reason to fail displaying the tree
        pass
    return name


def main_group(path: str) -> str:
    """The main groups holding a data or axis node: what lies between the root group (RawData...) and the
    data type group (Data0D, Data1D, DataND...), e.g. ``scan_000`` or ``Spectrometer``"""
    parts = [p for p in path.split('/') if p]
    for i, part in enumerate(parts):
        if re.fullmatch(r'Data(\d+D|ND)', part):
            return '/'.join(parts[1:i])
    return '/'.join(parts[1:-2])


def _show_groups(infos: List[DataInfo]) -> bool:
    """Tell where data come from only if they do not all come from the same group"""
    return len({main_group(i.path) for i in infos}) > 1


def _leaf(info: DataInfo, multi_file: bool, with_group: bool = False) -> RepItem:
    label = info.label
    group = main_group(info.path) if with_group else ''
    if group:
        label += f' · {group}'
    if multi_file and info.file:
        label += f' [{info.file}]'
    return RepItem(label, info.path, tooltip=info.path)


def _group_by(infos: List[DataInfo], key: Callable[[DataInfo], str], label: Callable[[str], str],
              multi_file: bool, with_group: bool = False) -> List[RepItem]:
    groups: Dict[str, RepItem] = {}
    for info in infos:
        k = key(info)
        if k not in groups:
            groups[k] = RepItem(label(k) if k else UNANNOTATED, tooltip=k)
        groups[k].children.append(_leaf(info, multi_file, with_group))
    # annotated groups sorted by label, not annotated last
    return sorted(groups.values(), key=lambda g: (g.label == UNANNOTATED, g.label))


def concept_mode(infos: List[DataInfo], semantics: SemanticsBase) -> RepItem:
    """Data grouped by what they are (``semantic_iri``), under their more general concepts if the active
    semantics provider knows them."""
    infos = [i for i in infos if i.kind == 'data']
    multi = len({i.file for i in infos}) > 1
    with_group = _show_groups(infos)
    root = RepItem('By concept')
    nodes: Dict[str, RepItem] = {}

    def concept_item(iri: str) -> RepItem:
        if iri not in nodes:
            nodes[iri] = RepItem(semantics.label(iri), tooltip=iri)
            parent = semantics.parent(iri)
            (concept_item(parent) if parent and parent != iri else root).children.append(nodes[iri])
        return nodes[iri]

    unannotated = RepItem(UNANNOTATED)
    for info in infos:
        iri = str(info.attrs.get(SEMANTIC_IRI, ''))
        iri = semantics.canonical(iri) if iri else iri
        (concept_item(iri) if iri else unannotated).children.append(_leaf(info, multi, with_group))
    _sort(root)
    if unannotated.children:
        root.children.append(unannotated)
    return root


def _sort(item: RepItem) -> None:
    """Sub-concepts first, then data, each by label"""
    item.children.sort(key=lambda c: (c.path is not None, c.label))
    for child in item.children:
        _sort(child)


def _unit_of(info: DataInfo) -> str:
    return str(info.attrs.get(UNIT_IRI) or info.attrs.get('units') or '')


def _unit_label(unit: str) -> str:
    return local_name(unit) if ':' in unit or '/' in unit else unit


def _unit_text(info: DataInfo) -> str:
    """Unit as the user knows it (the ``units`` attribute, e.g. nm), else the name of its IRI"""
    return str(info.attrs.get('units') or '') or _unit_label(_unit_of(info))


def _axis_leaf(info: DataInfo, multi_file: bool, with_group: bool = False) -> RepItem:
    name = info.path.rsplit('/', 1)[-1]
    unit = _unit_text(info)
    label = f'{name} · {info.label}' + (f' [{unit}]' if unit else '')
    details = [f'of {info.owner}' if info.owner else '', f'{info.role} axis' if info.role else '']
    label += ''.join(f' · {d}' for d in details if d)
    if with_group and main_group(info.path):
        label += f' · {main_group(info.path)}'
    if multi_file and info.file:
        label += f' [{info.file}]'
    return RepItem(label, info.path, tooltip=info.path)


def _by_quantity_and_unit(infos: List[DataInfo], semantics: SemanticsBase, leaf: Callable) -> List[RepItem]:
    by_qk: Dict[str, List[DataInfo]] = {}
    for info in infos:
        qk = str(info.attrs.get(QUANTITY_KIND, ''))
        by_qk.setdefault(semantics.canonical(qk) if qk else qk, []).append(info)
    items = []
    for qk in sorted(by_qk, key=lambda k: (k == '', semantics.label(k))):
        item = RepItem(semantics.label(qk) if qk else UNANNOTATED, tooltip=qk)
        by_unit: Dict[str, RepItem] = {}
        for info in by_qk[qk]:
            unit = _unit_of(info)
            if unit not in by_unit:
                by_unit[unit] = RepItem(_unit_text(info) if unit else UNANNOTATED, tooltip=unit)
            by_unit[unit].children.append(leaf(info))
        item.children = sorted(by_unit.values(), key=lambda g: (g.label == UNANNOTATED, g.label))
        items.append(item)
    return items


def quantity_mode(infos: List[DataInfo], semantics: SemanticsBase) -> RepItem:
    """Data grouped by quantity kind, then by unit; the axes are in a separate 'Axes' branch grouped the
    same way, each telling which data it belongs to and whether it is a signal or a navigation axis."""
    multi = len({i.file for i in infos}) > 1
    with_group = _show_groups(infos)
    root = RepItem('By quantity and unit')
    root.children = _by_quantity_and_unit([i for i in infos if i.kind == 'data'], semantics,
                                          lambda i: _leaf(i, multi, with_group))
    axes = [i for i in infos if i.kind == 'axis']
    if axes:
        axes_item = RepItem('Axes')
        axes_item.children = _by_quantity_and_unit(axes, semantics, lambda i: _axis_leaf(i, multi, with_group))
        root.children.append(axes_item)
    return root


def build_tree(files, mode: str = 'concept', semantics: SemanticsBase = None) -> RepItem:
    """Tree of one or several PyMoDAQ h5 files in the given mode (see ``mode_names()``), for scripts and
    notebooks. In a notebook, ending a cell with the returned item displays it as a collapsible tree.

    Parameters
    ----------
    files: str, Path or an iterable of them
    mode: name of a registered mode, or 'hdf5' for the standard hierarchy of the h5browser (every node,
        one subtree per file if there are several)
    semantics: provider of labels and concept hierarchy, the default one if None
    """
    from pathlib import Path
    from pymodaq_data.h5modules.browsing import H5BrowserUtil
    if isinstance(files, (str, Path)):
        files = [files]
    infos: List[DataInfo] = []
    hierarchies: List[RepItem] = []
    for file in files:
        h5 = H5BrowserUtil(backend='h5py')
        h5.init_file(file_name=Path(file), new_file=False, mode='r')
        try:
            if mode == HIERARCHY_MODE:
                hierarchies.append(hierarchy_tree(h5.root(), Path(file).stem))
            else:
                infos += data_infos(h5.root(), Path(file).stem)
        finally:
            h5.close_file()
    if mode == HIERARCHY_MODE:
        if len(hierarchies) == 1:
            return hierarchies[0]
        return RepItem('Files', children=hierarchies)
    return build_mode(mode, infos, semantics)


def register_mode(name: str, title: str):
    """Decorator registering a representation mode. The decorated function maps the data nodes of the
    open file(s) to a tree: ``builder(infos: List[DataInfo], semantics: SemanticsBase) -> RepItem``.

    ``infos`` holds the data nodes (``kind == 'data'``) and the axis nodes (``kind == 'axis'``): a mode
    only interested in the data filters on ``kind``.

    Examples
    --------
    ::

        @register_mode('flat', 'All data')
        def flat(infos, semantics):
            return RepItem('All', children=[RepItem(i.label, i.path) for i in infos if i.kind == 'data'])
    """
    def inner_wrapper(builder: Callable[[List[DataInfo]], RepItem]):
        if name in RepresentationModeFactory.builders:
            logger.warning(f'The representation mode "{name}" is already registered. Replacing it')
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


def build_mode(name: str, infos: List[DataInfo], semantics: SemanticsBase = None) -> RepItem:
    _load_entry_points()
    if name not in RepresentationModeFactory.builders:
        raise ValueError(f'Unknown representation mode "{name}", registered: {mode_names()}')
    return RepresentationModeFactory.builders[name](infos, semantics or SemanticsBase())


register_mode('concept', 'By concept')(concept_mode)
register_mode('quantity', 'By quantity and unit')(quantity_mode)
