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
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, Iterator, List, Optional

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


def local_name(iri: str) -> str:
    """Last part of an IRI: ``https://x/spectro#DarkSpectrum`` -> ``DarkSpectrum``;
    ``unit:NUM`` -> ``NUM``."""
    return re.split(r'[#/:]', str(iri).rstrip('/#'))[-1]


def humanize(name: str) -> str:
    """``DarkSpectrum`` -> ``Dark spectrum``."""
    words = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', name)
    return words[:1].upper() + words[1:].lower() if words else words


def iri_label(iri: str) -> str:
    return humanize(local_name(iri))


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
    """Data grouped by what they are (``semantic_iri``)."""
    multi = len({i.file for i in infos}) > 1
    root = RepItem('By concept')
    root.children = _group_by(infos, lambda i: str(i.attrs.get(SEMANTIC_IRI, '')), iri_label, multi)
    return root


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


@dataclass
class Mode:
    name: str                     # identifier
    title: str                    # what the user sees in a selector
    build: Callable[[List[DataInfo]], RepItem]


MODES: Dict[str, Mode] = {}


def register_mode(name: str, title: str, build: Callable[[List[DataInfo]], RepItem]) -> Mode:
    """Add a representation mode. ``build`` maps the data nodes of the open file(s) to a tree."""
    MODES[name] = Mode(name, title, build)
    return MODES[name]


register_mode('concept', 'By concept', concept_mode)
register_mode('quantity', 'By quantity and unit', quantity_mode)
