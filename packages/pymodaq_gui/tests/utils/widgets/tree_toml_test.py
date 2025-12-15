import pytest
from typing import Dict
from pathlib import Path

from joblib.testing import fixture
from pyqtgraph.parametertree import Parameter
from qtpy import QtWidgets, QtCore
from pymodaq_utils.config import BaseConfig, _delete_config_files
from pymodaq_gui.utils.widgets.tree_toml import TreeFromToml
import toml

class Config(BaseConfig):
    config_name = 'custom_config_tested'
    config_template_path = Path(__file__).parent.parent.parent.joinpath('data/config_template.toml')


BASE_CONFIG_DICT = toml.load(Config.config_template_path)

def parameter_tree_dict_equals(param : Parameter, config : Dict):
    parameter_tree = TreeFromToml.param_to_dict(param)
    # This entry is added in the parameter tree but is not present in the config!
    del parameter_tree['config_path']

    return parameter_tree == config

@fixture
def config():
    config = Config()
    _delete_config_files(config)
    config.load()
    return config

class TestTreeFromToml:

    def test_contains_config(self, qtbot, config):
        tree_from_toml = TreeFromToml(config)

        assert parameter_tree_dict_equals(tree_from_toml.settings, config.to_dict())

    @pytest.mark.parametrize(
        "changes, equals_to_config", [
            # list of changes in the form ((path, to, param), value)
            # here it depends on the default value of darkstyle!
            ([], True),
            ([(('style', 'darkstyle'), False)], False),
            ([(('style', 'darkstyle'), False), (('style', 'darkstyle'), True)], True)
        ]
    )
    def test_reject_config(self, qtbot, config, changes, equals_to_config):

        tree_from_toml = TreeFromToml(config)

        def dialog_action():
            # wait for dialog to exist
            qtbot.waitUntil(lambda : tree_from_toml.dialog is not None)
            qtbot.addWidget(tree_from_toml.dialog)
            qtbot.waitExposed(tree_from_toml.dialog)

            for path, value in changes:
                with qtbot.waitSignal(tree_from_toml.settings.sigTreeStateChanged, raising=False):
                    tree_from_toml.settings.param(*path).setValue(value)
                    qtbot.wait(0)
            qtbot.wait(0)

            reject_button = tree_from_toml.dialog.findChild(QtWidgets.QPushButton, "cancel")
            qtbot.mouseClick(reject_button, QtCore.Qt.MouseButton.LeftButton)

        QtCore.QTimer.singleShot(0, dialog_action)

        # rejected
        saved = tree_from_toml.show_dialog()
        assert not saved

        # Parameter tree is modified only if changes are made
        assert parameter_tree_dict_equals(tree_from_toml.settings, config.to_dict()) == equals_to_config

        # In all cases, config object is not changed
        assert config.to_dict() == BASE_CONFIG_DICT


    @pytest.mark.parametrize(
        "changes, config_was_modified", [
            # list of changes in the form ((path, to, param), value)
            # here it depends on the default value of darkstyle!
            ([], False),
            ([(('style', 'darkstyle'), False)], True),
            ([(('style', 'darkstyle'), False), (('style', 'darkstyle'), True)], False)
        ]
    )

    @pytest.mark.order(after="test_reject_config")
    def test_accept_config(self, qtbot, config, changes, config_was_modified):
        """ beware test order is important, it uses pytest-order to make sure tests are done
        in the right order top to bottom, see dev dependencies"""
        tree_from_toml = TreeFromToml(config)

        def dialog_action():
            # wait for dialog to exist
            qtbot.waitUntil(lambda : tree_from_toml.dialog is not None)
            qtbot.addWidget(tree_from_toml.dialog)
            qtbot.waitExposed(tree_from_toml.dialog)

            for path, value in changes:
                with qtbot.waitSignal(tree_from_toml.settings.sigTreeStateChanged, raising=False):
                    tree_from_toml.settings.param(*path).setValue(value)
                    qtbot.wait(0)
            qtbot.wait(0)

            accept_button = tree_from_toml.dialog.findChild(QtWidgets.QPushButton, "save")
            qtbot.mouseClick(accept_button, QtCore.Qt.MouseButton.LeftButton)

        QtCore.QTimer.singleShot(0, dialog_action)

        # accepted
        saved = tree_from_toml.show_dialog()
        assert saved

        # Config is synchronized with parameter tree
        assert parameter_tree_dict_equals(tree_from_toml.settings, config.to_dict())

        # And may or not be different (depending on the changes)
        assert (config.to_dict() != BASE_CONFIG_DICT) == config_was_modified


    @pytest.mark.parametrize(
        "start_path, change, exists", [
            #Path to start the tree, the change to make, and if it should succeed or not
            # (entry exist in the sub config)
            (('optimizer', 'bounds'), (('style', 'darkstyle'), False), False),
            (('optimizer', 'bounds'), (('actuator_min',), 0), True)
        ]
    )
    @pytest.mark.order(after="test_accept_config")
    def test_subtree(self, qtbot, config, start_path, change, exists):
        tree_from_toml = TreeFromToml(config, start_path=start_path)

        def dialog_action():
            # wait for dialog to exist
            qtbot.waitUntil(lambda: tree_from_toml.dialog is not None)
            qtbot.addWidget(tree_from_toml.dialog)
            qtbot.waitExposed(tree_from_toml.dialog)

            path, value = change
            with (qtbot.waitSignal(tree_from_toml.settings.sigTreeStateChanged, raising=False, timeout=100)):
                try:
                    tree_from_toml.settings.param(*path).setValue(value)
                except KeyError:
                    assert not exists
                qtbot.wait(0)
            qtbot.wait(0)

            reject_button = tree_from_toml.dialog.findChild(QtWidgets.QPushButton, "save")
            qtbot.mouseClick(reject_button, QtCore.Qt.MouseButton.LeftButton)

        QtCore.QTimer.singleShot(0, dialog_action)

        # accepted
        saved = tree_from_toml.show_dialog()
        assert saved

        # Config is synchronized with parameter tree
        assert parameter_tree_dict_equals(tree_from_toml.settings, config(*start_path))

        # And may or not be different (depending on the changes)
        assert (config.to_dict() != BASE_CONFIG_DICT) == exists



