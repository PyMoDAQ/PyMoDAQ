import pytest
from typing import Dict
from pathlib import Path


from pyqtgraph.parametertree import Parameter
from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal
from pymodaq_utils.config import BaseConfig, get_config_file
from pymodaq_utils.config import get_set_config_dir
from pymodaq_gui.utils.widgets.tree_toml import TreeFromToml

class Config(BaseConfig):
    config_name = 'custom_config_tested'
    config_template_path = Path(__file__).parent.parent.parent.joinpath('data/config_template.toml')



def delete_config(config : BaseConfig):
    get_config_file(config.config_name, user=False).unlink(missing_ok=True)
    get_config_file(config.config_name, user=True).unlink(missing_ok=True)

def parameter_tree_dict_equals(param : Parameter, config : Dict):
    parameter_tree = TreeFromToml.param_to_dict(param)
    # This entry is added in the parameter tree but is not present in the config!
    del parameter_tree['config_path']

    return parameter_tree == config


class TestTreeFromToml:

    def test_contains_config(self, qtbot):
        config = Config()
        config.load()
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
    def test_reject_config(self, qtbot, changes, equals_to_config):
        config = Config()
        config.load()
        old_config_dict = config.to_dict()

        tree_from_toml = TreeFromToml(config)

        def reject_action():
            # wait for dialog to exist
            qtbot.waitUntil(lambda : tree_from_toml.dialog is not None)
            qtbot.addWidget(tree_from_toml.dialog)
            qtbot.waitExposed(tree_from_toml.dialog)

            for path, value in changes:
                with qtbot.waitSignal(tree_from_toml.settings.sigTreeStateChanged, raising=False):
                    tree_from_toml.settings.param(*path).setValue(value)
                    qtbot.wait(0.01)
            qtbot.wait(0.01)

            reject_button = tree_from_toml.dialog.findChild(QtWidgets.QPushButton, "cancel")
            qtbot.mouseClick(reject_button, QtCore.Qt.MouseButton.LeftButton)

        QtCore.QTimer.singleShot(0, reject_action)

        # rejected
        saved = tree_from_toml.show_dialog()
        assert not saved

        # Parameter tree is modified only if changes are made
        assert parameter_tree_dict_equals(tree_from_toml.settings, config.to_dict()) == equals_to_config

        # In all cases, config object is not changed
        assert config.to_dict() == old_config_dict


    @pytest.mark.parametrize(
        "changes, config_was_modified", [
            # list of changes in the form ((path, to, param), value)
            # here it depends on the default value of darkstyle!
            ([], False),
            ([(('style', 'darkstyle'), False)], True),
            ([(('style', 'darkstyle'), False), (('style', 'darkstyle'), True)], False)
        ]
    )
    def test_accept_config(self, qtbot, changes, config_was_modified):
        config = Config()
        config.load()
        old_config_dict = config.to_dict()

        tree_from_toml = TreeFromToml(config)

        def accept_action():
            # wait for dialog to exist
            qtbot.waitUntil(lambda : tree_from_toml.dialog is not None)
            qtbot.addWidget(tree_from_toml.dialog)
            qtbot.waitExposed(tree_from_toml.dialog)

            for path, value in changes:
                with qtbot.waitSignal(tree_from_toml.settings.sigTreeStateChanged, raising=False):
                    tree_from_toml.settings.param(*path).setValue(value)
                    qtbot.wait(0.01)
            qtbot.wait(0.01)

            reject_button = tree_from_toml.dialog.findChild(QtWidgets.QPushButton, "save")
            qtbot.mouseClick(reject_button, QtCore.Qt.MouseButton.LeftButton)
            qtbot.wait(1)

        QtCore.QTimer.singleShot(0, accept_action)

        # accepted
        saved = tree_from_toml.show_dialog()
        assert saved

        # Config is synchronized with parameter tree
        assert parameter_tree_dict_equals(tree_from_toml.settings, config.to_dict())

        # And may or not be different (depending on the changes)
        assert (config.to_dict() != old_config_dict) == config_was_modified
        delete_config(config)



