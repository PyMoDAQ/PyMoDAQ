from pymodaq_utils.plugin_tools import checks as plugin_checks, contract as plugin_contract, rules as plugin_rules


def test_checks_and_rules_read_the_contract():
    for kind, attr in (('move', 'MANDATORY_MOVE_METHODS'), ('viewer', 'MANDATORY_VIEWER_METHODS')):
        assert getattr(plugin_rules, attr) == plugin_contract.mandatory_methods(kind)
        assert getattr(plugin_checks, attr) == plugin_contract.mandatory_methods(kind)


def test_mandatory_methods():
    assert plugin_contract.mandatory_methods('move') == ('ini_stage', 'get_actuator_value', 'close')
    assert plugin_contract.mandatory_methods('viewer') == ('ini_detector', 'grab_data', 'stop', 'close')


def test_rst_table_lists_every_method():
    rst = plugin_contract.contract_as_rst()
    for method in plugin_contract.PLUGIN_METHODS:
        assert f'``{method.name}``' in rst


def test_docs_table_is_up_to_date():
    from pathlib import Path
    table = Path(plugin_contract.__file__).parents[5] / 'docs' / 'src' / 'developer_folder' / 'plugin_contract_table.inc'
    if not table.is_file():
        import pytest
        pytest.skip('docs not available (installed package)')
    assert table.read_text() == plugin_contract.contract_as_rst() + '\n', \
        'regenerate with: python -c "from pymodaq_utils.plugin_tools.contract import contract_as_rst; ' \
        f'open(\'{table}\', \'w\').write(contract_as_rst() + chr(10))"'


def test_old_module_paths_are_aliases():
    import importlib
    from pymodaq_utils.plugin_tools import checks, rules, scaffold
    for old, new in (('plugin_checks', checks), ('plugin_rules', rules), ('plugin_scaffold', scaffold)):
        assert importlib.import_module(f'pymodaq_utils.{old}') is new
