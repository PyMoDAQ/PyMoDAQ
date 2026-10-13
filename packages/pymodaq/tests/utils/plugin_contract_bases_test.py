from pymodaq_utils import plugin_contract


def test_every_method_exists_in_the_base_classes():
    from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
    from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
    for kind, base in (('move', DAQ_Move_base), ('viewer', DAQ_Viewer_base)):
        for method in plugin_contract.methods_of(kind):
            assert hasattr(base, method.name), f'{base.__name__} has no {method.name}'
