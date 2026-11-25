"""Extraction of the ``Authors``, ``Contributors`` and ``Instruments`` sections of a plugin README.

The README of a plugin package (reStructuredText, or Markdown for a few of them) is published on PyPI as the package
description. The plugin template asks for the following structure::

    Authors
    =======

    * First Author (email)

    Instruments
    ===========

    Actuators
    +++++++++

    * **Name**: description (tested on model X)

    Viewer2D
    ++++++++

    * **Name**: description

Instead of searching for sub-strings, the text is first split into a tree of sections following the heading levels (the
level of a reStructuredText underline style is given by the order in which the styles first appear, as docutils does).
Comment blocks (``.. if needed use this field`` in the template) are ignored. The parser has no dependency
and never raises on malformed input: it returns what it could find.

.. versionadded:: 5.3.8
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_RST_ADORNMENT = re.compile(r'^([!-/:-@\[-`{-~])\1{2,}\s*$')  # a line made of >= 3 times the same punctuation
_ATX_HEADING = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
_BULLET = re.compile(r'^(\s*)([*\-+•])\s+(.*)$')
_FENCE = re.compile(r'^\s*(```|~~~)')

#: normalisation of the sub-headings found below ``Instruments``
_KIND_PATTERNS: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r'^(daq[_ ]?move\s*)?actuators?$', re.I), 'Actuators'),
    (re.compile(r'^(daq[_ ]?viewer[_ ]?|viewers?\s*)(0d|1d|2d|nd)$', re.I), ''),  # completed in _normalize_kind
    (re.compile(r'^pid\s+models?$', re.I), 'PID Models'),
    (re.compile(r'^extensions?$', re.I), 'Extensions'),
    (re.compile(r'^(legacy|deprecated)( instruments| plugins)?$', re.I), 'Legacy'),
)
_INSTRUMENTS_TITLE = re.compile(r'^(supported\s+)?(instruments?|devices?)$', re.I)
_AUTHORS_TITLE = re.compile(r'^authors?(\(s\))?$', re.I)
_CONTRIBUTORS_TITLE = re.compile(r'^contributors?(\(s\))?$', re.I)

_NAME_WITH_MARKUP = re.compile(r'^(?P<mark>\*\*|``|__)(?P<name>.+?)(?P=mark)(?P<rest>.*)$')
_EMAIL = re.compile(r'[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+')


@dataclass
class Section:
    """A node of the section tree of a README"""
    title: str = ''
    level: int = 0
    lines: List[str] = field(default_factory=list)  # lines of the section before its first sub-section
    children: List['Section'] = field(default_factory=list)

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass
class Instrument:
    """One instrument (or extension, model...) listed in a README"""
    name: str
    description: str = ''

    def __str__(self):
        return f'{self.name}: {self.description}' if self.description else self.name


@dataclass
class ReadmeInfo:
    """What could be extracted from a plugin README"""
    authors: List[str] = field(default_factory=list)
    contributors: List[str] = field(default_factory=list)
    instruments: Dict[str, List[Instrument]] = field(default_factory=dict)

    def instruments_as_dict(self) -> Dict[str, List[str]]:
        """Instruments as ``{'Actuators': ['Name: description', ...], ...}``"""
        return {kind: [str(inst) for inst in insts] for kind, insts in self.instruments.items()}

    def instrument_names(self) -> List[str]:
        return [inst.name for insts in self.instruments.values() for inst in insts]


def _is_comment_start(line: str) -> bool:
    """reStructuredText comment, directive or hyperlink target: ``.. something``"""
    line = line.lstrip()
    return line.startswith('..') and (len(line) == 2 or line[2] in ' \t')


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _strip_comments(lines: List[str]) -> List[str]:
    """Remove the reStructuredText comment/directive blocks (a ``..`` line and what is indented below it)"""
    out = []
    block_indent = None
    for line in lines:
        if block_indent is not None:
            if not line.strip() or _indent(line) > block_indent:
                continue
            block_indent = None
        if _is_comment_start(line):
            block_indent = _indent(line)
            continue
        out.append(line)
    return out


def parse_sections(text: str) -> Section:
    """Split a reStructuredText or Markdown text into a tree of sections

    Parameters
    ----------
    text: str
        the README

    Returns
    -------
    Section
        a root section (level 0, no title) holding the sections as children
    """
    lines = _strip_comments((text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n'))
    root = Section(level=0)
    stack = [root]
    rst_styles: List[Tuple[bool, str]] = []  # (has overline, character) in order of appearance
    in_fence = False

    def add_section(title: str, level: int):
        while stack[-1].level >= level:
            stack.pop()
        section = Section(title=title.strip(), level=level)
        stack[-1].children.append(section)
        stack.append(section)

    i = 0
    while i < len(lines):
        line = lines[i]
        if _FENCE.match(line):
            in_fence = not in_fence
        if in_fence:
            stack[-1].lines.append(line)
            i += 1
            continue

        atx = _ATX_HEADING.match(line)
        if atx:
            add_section(atx.group(2), len(atx.group(1)))
            i += 1
            continue

        # rst title with underline (and possibly overline)
        if (line.strip() and line[0] not in ' \t' and i + 1 < len(lines)
                and not _RST_ADORNMENT.match(line)):
            nxt = lines[i + 1]
            if _RST_ADORNMENT.match(nxt) and len(nxt.rstrip()) >= len(line.strip()) - 2:
                style = (False, nxt[0])
                if style not in rst_styles:
                    rst_styles.append(style)
                add_section(line, 10 + rst_styles.index(style))
                i += 2
                continue
        # rst title with overline
        if (_RST_ADORNMENT.match(line) and i + 2 < len(lines) and lines[i + 1].strip()
                and lines[i + 2] == line):
            style = (True, line[0])
            if style not in rst_styles:
                rst_styles.append(style)
            add_section(lines[i + 1], 10 + rst_styles.index(style))
            i += 3
            continue

        stack[-1].lines.append(line)
        i += 1
    return root


def _clean_inline(text: str) -> str:
    """Remove the inline markup of reStructuredText/Markdown that makes no sense in a plain text list"""
    text = re.sub(r'`([^`<]+?)\s*<[^>]*>`_{1,2}', r'\1', text)  # `text <url>`__
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)  # [text](url)
    text = re.sub(r':[a-z]+:`~?([^`]+)`', r'\1', text)  # :class:`x`
    text = re.sub(r'``([^`]+)``', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def _bullets(lines: List[str]) -> List[str]:
    """Texts of the bullets of a list of lines (continuation lines and nested bullets are joined to their bullet)"""
    items: List[List[str]] = []
    base_indent: Optional[int] = None
    for line in lines:
        m = _BULLET.match(line)
        if m:
            indent = len(m.group(1))
            if base_indent is None or indent <= base_indent:
                base_indent = indent if base_indent is None else min(base_indent, indent)
                items.append([m.group(3).strip()])
            elif items:
                items[-1].append(m.group(3).strip())  # nested bullet: detail of the parent
        elif line.strip() and items and line[0] in ' \t':
            items[-1].append(line.strip())  # continuation line
        elif not line.strip():
            continue
        elif items:
            base_indent = None  # a paragraph ends the list
            items.append([])
    return [' '.join(i) for i in items if i]


def _split_name_description(text: str) -> Instrument:
    """Split ``**Name**: description``, ``**Name** description`` or ``Name: description``"""
    text = text.strip()
    m = _NAME_WITH_MARKUP.match(text)
    if m:
        name, rest = m.group('name'), m.group('rest')
        name = name.strip()
        if name.endswith(':'):
            name = name[:-1].strip()
        rest = rest.strip()
        if rest[:1] in (':', '-', '–', '—'):
            rest = rest[1:]
        return Instrument(_clean_inline(name), _clean_inline(rest))
    plain = _clean_inline(text)
    if ':' in plain:
        name, _, rest = plain.partition(':')
        if 0 < len(name.split()) <= 6 and not name.startswith('http'):
            return Instrument(name.strip(), rest.strip())
    return Instrument(plain)


def _entries(lines: List[str], bold_paragraphs: bool = True) -> List[Instrument]:
    """The instruments listed in the lines of a section: bullets, and ``**Name**: text`` paragraphs"""
    entries = [_split_name_description(b) for b in _bullets(lines)]
    if bold_paragraphs:
        for line in lines:
            if _BULLET.match(line) or line[:1] in (' ', '\t'):
                continue
            if _NAME_WITH_MARKUP.match(line.strip()) and line.strip().startswith('**'):
                entries.append(_split_name_description(line))
    return [e for e in entries if e.name]


def _normalize_kind(title: str) -> Optional[str]:
    title = _clean_inline(title)
    for pattern, kind in _KIND_PATTERNS:
        m = pattern.match(title)
        if m:
            if kind == '':
                return f'Viewer{m.group(2).upper()}'
            return kind
    return None


def _find(root: Section, pattern: re.Pattern) -> Optional[Section]:
    """The shallowest section whose title matches"""
    return _find_with_parent(root, pattern)[0]


def _find_with_parent(root: Section, pattern: re.Pattern) -> Tuple[Optional[Section], Optional[Section]]:
    best, best_parent = None, None
    stack = [(root, None)]
    while stack:
        section, parent = stack.pop(0)
        if section is not root and pattern.match(_clean_inline(section.title)):
            if best is None or section.level < best.level:
                best, best_parent = section, parent
        stack.extend((child, section) for child in section.children)
    return best, best_parent


def _people(section: Optional[Section]) -> List[str]:
    if section is None:
        return []
    people = []
    for text in _bullets(section.lines):
        text = _clean_inline(text)
        if text:
            people.append(text)
    return people


def extract_authors(text: str) -> List[str]:
    """Authors (name and possibly email, one string each) listed in the ``Authors`` section of a README"""
    return _people(_find(parse_sections(text), _AUTHORS_TITLE))


def extract_instruments(text: str) -> Dict[str, List[Instrument]]:
    """The instruments listed in the ``Instruments`` section of a README, grouped by kind

    The kinds are ``Actuators``, ``Viewer0D``, ``Viewer1D``, ``Viewer2D``, ``ViewerND``, ``PID Models``,
    ``Extensions`` and ``Legacy``. Entries found directly below ``Instruments`` (no sub-section) go to ``Other``.
    Sub-sections of ``Instruments`` with another title (installation notes, infos...) are ignored.
    """
    root = parse_sections(text)
    section, parent = _find_with_parent(root, _INSTRUMENTS_TITLE)
    instruments: Dict[str, List[Instrument]] = {}
    if section is None:
        return instruments
    direct = _entries(section.lines)
    if direct:
        instruments['Other'] = direct
    candidates = list(section.children)
    if parent is not None:
        # some READMEs write the kinds (Actuators, Viewer1D...) at the same level as ``Instruments``
        siblings = parent.children
        for sibling in siblings[siblings.index(section) + 1:]:
            if _normalize_kind(sibling.title) is None:
                break
            candidates.append(sibling)
    for child in candidates:
        kind = _normalize_kind(child.title)
        if kind is None:
            continue
        entries = []
        for sub in child.walk():  # entries may be grouped in sub-sub-sections
            entries.extend(_entries(sub.lines))
        if entries:
            instruments.setdefault(kind, []).extend(entries)
    return instruments


def parse_readme(text: str) -> ReadmeInfo:
    """Extract authors, contributors and instruments from the README (the description of a PyPI package)"""
    root = parse_sections(text)
    info = ReadmeInfo(authors=_people(_find(root, _AUTHORS_TITLE)),
                      contributors=_people(_find(root, _CONTRIBUTORS_TITLE)))
    info.instruments = extract_instruments(text)
    return info


def emails(text: str) -> List[str]:
    """Email addresses found in a string such as an author entry"""
    return _EMAIL.findall(text or '')
