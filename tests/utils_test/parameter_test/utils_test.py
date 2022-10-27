from pymodaq.utils.parameter import utils
from unittest import mock


def test_get_param_path():
    item1 = mock.Mock()
    item1.name.return_value = 'first'
    item1.parent.return_value = None
    item2 = mock.Mock()
    item2.name.return_value = 'second'
    item2.parent.return_value = item1
    item3 = mock.Mock()
    item3.name.return_value = 'third'
    item3.parent.return_value = item2
    item4 = mock.Mock()
    item4.name.return_value = 'fourth'
    item4.parent.return_value = item3

    path = utils.get_param_path(item4)

    assert path == ['first', 'second', 'third', 'fourth']


def test_iter_children():
    child = mock.Mock()
    child.name.side_effect = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh']
    child.type.side_effect = [[], [], [], ['group'], [], [], []]
    child.children.side_effect = [[child, child, child]]
    param = mock.Mock()
    param.children.return_value = [child, child, child, child]

    childlist = utils.iter_children(param)

    assert childlist == ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh']


def test_iter_children_params():
    child = mock.Mock()
    child.type.side_effect = [[], [], [], ['group'], [], [], []]
    child.children.side_effect = [[child, child, child]]
    param = mock.Mock()
    param.children.return_value = [child, child, child, child]

    childlist = utils.iter_children_params(param)

    assert len(childlist) == 7


def test_get_param_from_name():
    child = mock.Mock()
    child.name.side_effect = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh']
    child.type.side_effect = [[], [], [], ['group'], [], [], []]
    child.children.side_effect = [[child, child, child]]
    param = mock.Mock()
    param.children.return_value = [child, child, child, child]

    child = utils.get_param_from_name(param, 'sixth')

    assert child.name() == 'seventh'


def test_is_name_in_dict():
    dict = {'name': 'test', 'parameter': 'gaussian', 'value': 5}
    assert utils.is_name_in_dict(dict, 'test')
    assert not utils.is_name_in_dict(dict, 'error')


def test_get_param_dict_from_name():
    parent_list = []
    for ind in range(5):
        parent_dict = {'name': ind, 'value': ind*5}
        parent_list.append(parent_dict)

    children = []
    for ind in range(5):
        parent_dict = {'name': ind*5, 'value': ind*10}
        children.append(parent_dict)

    parent_dict = {'name': 'test', 'children': children}
    parent_list.append(parent_dict)

    result = utils.get_param_dict_from_name(parent_list, 4)

    assert result['value'] == 20

    result = utils.get_param_dict_from_name(parent_list, 20, pop=True)

    assert result['value'] == 40
