"""The popup where the user picks the term of a channel"""
from typing import Optional

from qtpy import QtCore, QtWidgets

from pymodaq_ontology.terms import OntologyTerm

IRI_ROLE = QtCore.Qt.ItemDataRole.UserRole


class TermPicker(QtWidgets.QDialog):
    """Search field and tree of terms, grouped by category, with the description of the selected term

    Typing in the field filters the terms and selects the first one left, ``Enter`` (or a double click, or OK)
    validates. When a kind of channel is given, only the terms that fit it are listed, unless *Show all terms*
    is checked.
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
        self.description = QtWidgets.QLabel('Select a term to read its description.')
        self.description.setWordWrap(True)
        self.description.setMinimumHeight(70)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok
                                             | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        for widget in (self.search, self.show_all, self.tree, self.description, buttons):
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
        categories: dict[str, QtWidgets.QTreeWidgetItem] = {}
        for term in self.terms.values():
            if kind and not term.fits(kind):
                continue
            if term.category not in categories:
                group = QtWidgets.QTreeWidgetItem(self.tree, [term.category or 'Terms'])
                group.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                group.setExpanded(True)
                categories[term.category] = group
            item = QtWidgets.QTreeWidgetItem(categories[term.category], [term.label])
            item.setData(0, IRI_ROLE, term.iri)
            item.setToolTip(0, term.description)
            if term.iri == self.current_iri:
                self.tree.setCurrentItem(item)
        self._filter(self.search.text())

    def _leaves(self):
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                yield group, group.child(j)

    def _filter(self, text: str) -> None:
        text = text.strip().lower()
        first = None
        shown = set()
        for group, leaf in self._leaves():
            term = self.terms[leaf.data(0, IRI_ROLE)]
            visible = not text or text in f'{term.label} {term.iri} {term.description}'.lower()
            leaf.setHidden(not visible)
            if visible:
                shown.add(id(group))
                first = first or leaf
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            group.setHidden(id(group) not in shown)
        if text and first is not None:  # typing then Enter is enough
            self.tree.setCurrentItem(first)

    def _show_description(self, item, _previous=None) -> None:
        iri = item.data(0, IRI_ROLE) if item is not None else None
        if iri in self.terms:
            term = self.terms[iri]
            self.description.setText(f'<b>{term.label}</b><br>{term.description}<br><small>{term.iri}</small>')

    def _accept(self) -> None:
        item = self.tree.currentItem()
        iri = item.data(0, IRI_ROLE) if item is not None else None
        if iri in self.terms:
            self.selected_iri = iri
            self.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            return self._accept()  # Enter validates, wherever the focus is
        if event.key() == QtCore.Qt.Key.Key_Down and self.search.hasFocus():
            self.tree.setFocus()
            return
        super().keyPressEvent(event)
