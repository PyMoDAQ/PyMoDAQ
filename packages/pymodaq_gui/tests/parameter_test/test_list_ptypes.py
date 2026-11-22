import pytest
from pyqtgraph.parametertree import ParameterTree

from pymodaq_gui.parameter import Parameter


@pytest.fixture
def list_param(qtbot):
    param = Parameter.create(name='choice', type='list', limits=['a', 'b'], value='a')
    tree = ParameterTree()
    tree.setParameters(param, showTop=False)
    qtbot.addWidget(tree)
    yield param  # the tree lives as long as the test


def test_changing_the_limits_does_not_change_the_value(list_param):
    """The widget is rebuilt with the new limits: it must not tell the parameter that its value changed."""
    changes = []
    list_param.sigValueChanged.connect(lambda p, v: changes.append(v))
    list_param.setLimits(['a', 'b', 'c'])
    assert changes == []
    assert list_param.value() == 'a'
