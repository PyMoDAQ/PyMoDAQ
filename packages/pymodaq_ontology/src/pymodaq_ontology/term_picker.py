"""The popup where the user picks the term of a channel"""
from typing import Optional

from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_ontology.terms import OntologyTerm, TermHierarchy

IRI_ROLE = QtCore.Qt.ItemDataRole.UserRole


class TermPicker(QtWidgets.QDialog):
    """Search field and tree of terms with the description of the selected term

    The terms are grouped by category or, when they have parents (``broader``), under what they are a kind of.

    Typing in the field filters the terms and selects the first one left, ``Enter`` (or a double click, or OK)
    validates. When a kind of channel is given, only the terms that fit it are listed, unless *Show all terms*
    is checked. The states (*Beam blocked*) are shown in italics in the hierarchy but cannot be selected.
    """

    def __init__(self, terms: list[OntologyTerm], parent=None, current_iri: str = '', kind: Optional[str] = None,
                 title: str = 'Choose an ontology term'):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(460, 460)
        self.terms = {term.iri: term for term in terms}
        self.kind = kind
        self.current_iri = current_iri
        self.selected_iri = ''

        self.search = QtWidgets.QLineEdit(placeholderText='Search...', clearButtonEnabled=True)
        self.show_all = QtWidgets.QCheckBox(f'Show all terms (not only those for {kind}s)')
        self.show_all.setVisible(bool(kind))
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.legend = QtWidgets.QLabel(
            '<i>Italic grey</i>: a state, set from a value of an actuator (not for a channel)')
        self.legend.setWordWrap(True)
        self.description = QtWidgets.QLabel('Select a term to read its description.')
        self.description.setWordWrap(True)
        self.description.setMinimumHeight(70)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok
                                             | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        for widget in (self.search, self.show_all, self.tree, self.legend, self.description, buttons):
            layout.addWidget(widget)

        self.search.textChanged.connect(self._filter)
        self.show_all.toggled.connect(self._rebuild)
        self.tree.currentItemChanged.connect(self._show_description)
        self.tree.itemDoubleClicked.connect(lambda *_: self._accept())
        self._rebuild()
        self.search.setFocus()

    def _rebuild(self) -> None:
        self.tree.clear()
        kind = None if self.show_all.isChecked() else self.kind
        shown = {iri: term for iri, term in self.terms.items() if not (kind and not term.fits(kind))}
        self.legend.setVisible(any(term.is_state for term in shown.values()))
        hierarchy = TermHierarchy(shown.values())
        if hierarchy.has_relations:
            self._build_hierarchy(hierarchy)
        else:
            self._build_categories(shown)
        self._filter(self.search.text())

    def _new_item(self, parent, term: OntologyTerm) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem(parent, [term.label])
        item.setData(0, IRI_ROLE, term.iri)
        item.setToolTip(0, term.description)
        if term.is_state:  # shown for the hierarchy, but a state is not the term of a channel
            font = item.font(0)
            font.setItalic(True)
            item.setFont(0, font)
            item.setForeground(0, self.palette().color(QtGui.QPalette.ColorGroup.Disabled,
                                                       QtGui.QPalette.ColorRole.Text))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
            item.setToolTip(0, f'State, not a channel: set it from a value of an actuator.\n{term.description}')
            return item
        if term.iri == self.current_iri:
            self.tree.setCurrentItem(item)
        return item

    def _build_categories(self, shown: dict[str, OntologyTerm]) -> None:
        """No relation between the terms: they are grouped by category"""
        categories: dict[str, QtWidgets.QTreeWidgetItem] = {}
        for term in shown.values():
            if term.category not in categories:
                group = QtWidgets.QTreeWidgetItem(self.tree, [term.category or 'Terms'])
                group.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                group.setExpanded(True)
                categories[term.category] = group
            self._new_item(categories[term.category], term)

    def _build_hierarchy(self, hierarchy: TermHierarchy) -> None:
        """The terms are shown under the term they are a kind of (under the first one if there are several)"""
        placed: set[str] = set()

        def add(parent, iri: str) -> None:
            placed.add(iri)
            item = self._new_item(parent, hierarchy.terms[iri])
            item.setExpanded(True)
            for child in hierarchy.children(iri):
                if child not in placed and hierarchy.parents(child)[0] == iri:
                    add(item, child)

        for root in hierarchy.roots():
            add(self.tree, root)
        for iri in hierarchy.terms:  # a loop has no root: do not lose its terms
            if iri not in placed:
                add(self.tree, iri)

    def _leaves(self):
        """(parent item or None, item) of each term of the tree"""
        def walk(parent, item):
            if item.data(0, IRI_ROLE) is not None:
                yield parent, item
            for i in range(item.childCount()):
                yield from walk(item, item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            yield from walk(None, self.tree.topLevelItem(i))

    def _filter(self, text: str) -> None:
        text = text.strip().lower()

        def matches(item) -> bool:
            iri = item.data(0, IRI_ROLE)
            term = self.terms.get(iri)
            return term is not None and (not text or text in f'{term.label} {term.iri} {term.description}'.lower())

        def apply(item) -> bool:
            """Show the item if it or one of its children matches, return whether it is shown"""
            visible = matches(item)
            for i in range(item.childCount()):
                visible = apply(item.child(i)) or visible
            item.setHidden(not visible)
            return visible

        for i in range(self.tree.topLevelItemCount()):
            apply(self.tree.topLevelItem(i))
        first = next((item for _, item in self._leaves()
                      if not item.isHidden() and matches(item) and self._selectable(item)), None)
        if text and first is not None:  # typing then Enter is enough
            self.tree.setCurrentItem(first)

    def _show_description(self, item, _previous=None) -> None:
        iri = item.data(0, IRI_ROLE) if item is not None else None
        if iri in self.terms:
            term = self.terms[iri]
            self.description.setText(f'<b>{term.label}</b><br>{term.description}<br><small>{term.iri}</small>')

    def _selectable(self, item) -> bool:
        term = self.terms.get(item.data(0, IRI_ROLE))
        return term is not None and not term.is_state

    def _accept(self) -> None:
        item = self.tree.currentItem()
        iri = item.data(0, IRI_ROLE) if item is not None else None
        if iri in self.terms and self._selectable(item):
            self.selected_iri = iri
            self.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            return self._accept()  # Enter validates, wherever the focus is
        if event.key() == QtCore.Qt.Key.Key_Down and self.search.hasFocus():
            self.tree.setFocus()
            return
        super().keyPressEvent(event)
