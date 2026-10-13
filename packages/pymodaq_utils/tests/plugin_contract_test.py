from pymodaq_utils import plugin_checks, plugin_contract, plugin_rules


def test_checks_and_rules_read_the_contract():
    for kind, attr in (('move', 'MANDATORY_MOVE_METHODS'), ('viewer', 'MANDATORY_VIEWER_METHODS')):
        assert getattr(plugin_rules, attr) == plugin_contract.mandatory_methods(kind)
        assert getattr(plugin_checks, attr) == plugin_contract.mandatory_methods(kind)


def test_mandatory_methods():
    assert plugin_contract.mandatory_methods('move') == ('ini_stage', 'get_actuator_value', 'close')
    assert plugin_contract.mandatory_methods('viewer') == ('ini_detector', 'grab_data', 'stop', 'close')


def test_every_method_exists_in_the_base_classes():
    from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
    from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
    for kind, base in (('move', DAQ_Move_base), ('viewer', DAQ_Viewer_base)):
        for method in plugin_contract.methods_of(kind):
            assert hasattr(base, method.name), f'{base.__name__} has no {method.name}'


def test_rst_table_lists_every_method():
    rst = plugin_contract.contract_as_rst()
    for method in plugin_contract.PLUGIN_METHODS:
        assert f'``{method.name}``' in rst


def test_docs_table_is_up_to_date():
    from pathlib import Path
    table = Path(plugin_contract.__file__).parents[4] / 'docs' / 'src' / 'developer_folder' / 'plugin_contract_table.inc'
    if not table.is_file():
        import pytest
        pytest.skip('docs not available (installed package)')
    assert table.read_text() == plugin_contract.contract_as_rst() + '\n', \
        'regenerate with: python -c "from pymodaq_utils.plugin_contract import contract_as_rst; ' \
        f'open(\'{table}\', \'w\').write(contract_as_rst() + chr(10))"'
