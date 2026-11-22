import pytest
from pyqtgraph.parametertree import ParameterTree

from pymodaq_gui.parameter import Parameter


@pytest.fixture(params=['a', 'b'])  # the initial value is the first item, or not
def list_param(qtbot, request):
    param = Parameter.create(name='choice', type='list', limits=['a', 'b'], value=request.param)
    tree = ParameterTree()
    tree.setParameters(param, showTop=False)
    qtbot.addWidget(tree)
    yield param  # the tree lives as long as the test


def test_changing_the_limits_does_not_change_the_value(list_param):
    initial = list_param.value()
    """The widget is rebuilt with the new limits: it must not tell the parameter that its value changed."""
    changes = []
    list_param.sigValueChanged.connect(lambda p, v: changes.append(v))
    list_param.setLimits(['a', 'b', 'c'])
    assert changes == []
    assert list_param.value() == initial
