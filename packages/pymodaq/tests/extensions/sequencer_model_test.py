import pytest
from qtpy.QtCore import QModelIndex, Qt

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase
from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq.extensions.sequencer.utilities.sequencer.model_view import SequenceTreeModel, row_of

seq_factory = SeqEltFactory()


@pytest.fixture
def model(qtbot) -> SequenceTreeModel:
    return SequenceTreeModel()


def add(model: SequenceTreeModel, parent: QModelIndex, name: str, id: int) -> QModelIndex:
    """ Add an element before the AddButton of parent, like the AddButton menu does"""
    elt = seq_factory.get_seq_elt(name)(id)
    model.insert_data(parent, -1, elt)
    index = model.index_from_element(elt)
    if elt.children_allowed:
        model.insert_data(index, 0, AddButtonPlaceholder())
    return index


def tree(elt: SeqEltBase) -> list:
    """ Nested (name, id, children) description of the elements below elt, checking the parent links"""
    result = []
    for child in elt.children:
        assert child.parent is elt
        result.append((child.elt_name, child.id, tree(child)))
    return result


BUTTON = ('button', -2, [])


def move(model: SequenceTreeModel, index: QModelIndex, parent: QModelIndex, row: int = -1):
    """ What the view does on a drag and drop: drop the data, then remove the dragged rows"""
    source_elt = model.get_elt_from_index(index)
    source_parent = model.parent(index)
    data = model.mimeData([index])
    assert model.dropMimeData(data, Qt.DropAction.MoveAction, row, 0, parent)
    # the view then removes the dragged row, whose number may have changed with the insertion
    model.removeRow(row_of(source_elt.parent, source_elt), source_parent)


class TestDragDrop:
    def test_move_group_to_the_end_keeps_its_children(self, model):
        group = add(model, QModelIndex(), 'repeat', 1)
        add(model, QModelIndex(), 'wait', 2)
        add(model, group, 'wait', 3)

        move(model, group, QModelIndex())

        assert tree(model.root_elt) == [
            ('wait', 2, []),
            ('repeat', 1, [('wait', 3, []), BUTTON]),
            BUTTON]

    def test_move_group_in_another_group_goes_before_its_button(self, model):
        group1 = add(model, QModelIndex(), 'repeat', 1)
        group2 = add(model, QModelIndex(), 'repeat', 2)
        add(model, group1, 'wait', 3)
        add(model, group2, 'wait', 4)
        add(model, group2, 'wait', 5)

        move(model, group1, group2)

        assert tree(model.root_elt) == [
            ('repeat', 2, [('wait', 4, []),
                           ('wait', 5, []),
                           ('repeat', 1, [('wait', 3, []), BUTTON]),
                           BUTTON]),
            BUTTON]

    def test_move_leaf_into_empty_group(self, model):
        wait = add(model, QModelIndex(), 'wait', 1)
        group = add(model, QModelIndex(), 'repeat', 2)

        move(model, wait, group)

        assert tree(model.root_elt) == [('repeat', 2, [('wait', 1, []), BUTTON]), BUTTON]

    def test_cannot_drop_a_group_in_itself_or_its_descendants(self, model):
        outer = add(model, QModelIndex(), 'repeat', 1)
        inner = add(model, outer, 'repeat', 2)
        before = tree(model.root_elt)

        for target in (outer, inner):
            data = model.mimeData([outer])
            assert not model.dropMimeData(data, Qt.DropAction.MoveAction, -1, 0, target)
            assert tree(model.root_elt) == before

    def test_copy_gets_new_ids(self, model):
        group = add(model, QModelIndex(), 'repeat', 1)
        add(model, group, 'wait', 2)

        data = model.mimeData([group])
        assert model.dropMimeData(data, Qt.DropAction.CopyAction, -1, 0, QModelIndex())

        top = model.root_elt.children
        assert [c.elt_name for c in top] == ['repeat', 'repeat', 'button']
        assert top[0].id != top[1].id
        assert tree(model.root_elt)[1][2][-1] == BUTTON


class TestIndexes:
    def test_parent_of_equal_siblings(self, model):
        """Equal elements (same id and name, as after a move) must still be located by identity"""
        group1 = add(model, QModelIndex(), 'repeat', 1)
        add(model, group1, 'wait', 1)
        group2 = seq_factory.get_seq_elt('repeat')(1)
        model.insert_data(QModelIndex(), 0, group2)
        model.insert_data(model.index_from_element(group2), 0, AddButtonPlaceholder())
        child = seq_factory.get_seq_elt('wait')(1)
        model.insert_data(model.index_from_element(group2), 0, child)

        for elt in (group2, child):
            index = model.index_from_element(elt)
            assert model.index(index.row(), 0, model.parent(index)).internalPointer() is elt


class TestYaml:
    def test_save_load_roundtrip(self, model, tmp_path):
        group = add(model, QModelIndex(), 'repeat', 1)
        add(model, group, 'wait', 2)
        add(model, QModelIndex(), 'wait', 3)
        expected = tree(model.root_elt)

        path = tmp_path / 'test.seq'
        model.save_elements(path)
        model.load_elements(path)

        assert tree(model.root_elt) == expected
