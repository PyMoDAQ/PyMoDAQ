# -*- coding: utf-8 -*-
"""
Tests for text_pattern parameter type

@author: PyMoDAQ Contributors
"""

import pytest
from qtpy import QtWidgets
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.parameter.pymodaq_ptypes.text_pattern import (
    PatternParameter,
    PatternParameterItem,
)


@pytest.fixture
def parameter_tree(qtbot):
    """Create a ParameterTree widget for testing"""
    form = QtWidgets.QWidget()
    tree = ParameterTree(form)
    form.show()
    qtbot.addWidget(form)
    yield tree
    form.close()


class TestPatternParameter:
    """Test PatternParameter class"""

    def test_create_basic_parameter(self):
        """Test creating a basic text_pattern parameter"""
        param = Parameter.create(
            name='test_pattern',
            type='text_pattern',
            value='Hello world',
            patterns={'@': ['alice', 'bob']},
            completer_config={'min_width': 200},
        )

        assert param.name() == 'test_pattern'
        assert param.type() == 'text_pattern'
        assert param.value() == 'Hello world'
        assert param.opts['patterns'] == {'@': ['alice', 'bob']}
        assert param.opts['completer_config'] == {'min_width': 200}

    def test_default_empty_patterns(self):
        """Test that patterns default to empty dict"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
        )

        assert param.opts['patterns'] == {}
        assert param.opts['completer_config'] == {}

    def test_add_pattern_method(self):
        """Test add_pattern convenience method"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice']},
        )

        param.add_pattern('#', ['python', 'java'])

        assert '@' in param.opts['patterns']
        assert '#' in param.opts['patterns']
        assert param.opts['patterns']['#'] == ['python', 'java']

    def test_update_completions_method(self):
        """Test update_completions convenience method"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice', 'bob']},
        )

        param.update_completions('@', ['alice', 'bob', 'charlie'])

        assert param.opts['patterns']['@'] == ['alice', 'bob', 'charlie']

    def test_remove_pattern_method(self):
        """Test remove_pattern convenience method"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice'], '#': ['python']},
        )

        param.remove_pattern('#')

        assert '@' in param.opts['patterns']
        assert '#' not in param.opts['patterns']

    def test_set_completer_config_method(self):
        """Test set_completer_config convenience method"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            completer_config={'min_width': 150},
        )

        param.set_completer_config(min_width=300, max_width=600)

        assert param.opts['completer_config']['min_width'] == 300
        assert param.opts['completer_config']['max_width'] == 600

    def test_setOpts_patterns(self):
        """Test updating patterns using setOpts"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice']},
        )

        new_patterns = {'@': ['alice', 'bob'], '#': ['python']}
        param.setOpts(patterns=new_patterns)

        assert param.opts['patterns'] == new_patterns

    def test_setOpts_completer_config(self):
        """Test updating completer_config using setOpts"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            completer_config={'min_width': 150},
        )

        new_config = {'min_width': 300, 'case_sensitive': True}
        param.setOpts(completer_config=new_config)

        assert param.opts['completer_config'] == new_config


class TestPatternParameterItem:
    """Test PatternParameterItem (widget integration)"""

    def test_create_widget(self, parameter_tree):
        """Test that parameter item creates the correct widget"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='Hello',
            patterns={'@': ['alice', 'bob'], '#': ['python', 'java']},
            completer_config={'min_width': 200, 'max_width': 400},
        )

        parameter_tree.setParameters(param, showTop=False)
        items = parameter_tree.listAllItems()

        assert len(items) > 0
        param_item = items[0]
        assert isinstance(param_item, PatternParameterItem)
        assert hasattr(param_item, 'widget')

    def test_widget_has_completers(self, parameter_tree):
        """Test that widget has completers configured"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice', 'bob'], '#': ['python']},
        )

        parameter_tree.setParameters(param, showTop=False)
        items = parameter_tree.listAllItems()
        widget = items[0].widget

        # Widget should have completers attribute
        assert hasattr(widget, 'completers')
        assert '@' in widget.completers
        assert '#' in widget.completers

    def test_widget_completions_match_parameter(self, parameter_tree):
        """Test that widget completions match parameter options"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice', 'bob', 'charlie']},
        )

        parameter_tree.setParameters(param, showTop=False)
        items = parameter_tree.listAllItems()
        widget = items[0].widget

        completions = widget.completers['@']['completions']
        assert completions == ['alice', 'bob', 'charlie']

    def test_value_changes_propagate(self, parameter_tree, qtbot):
        """Test that value changes in widget propagate to parameter"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='Initial',
        )

        parameter_tree.setParameters(param, showTop=False)
        items = parameter_tree.listAllItems()
        widget = items[0].widget

        # Change text in widget
        widget.setPlainText('Modified text')
        qtbot.wait(50)

        # Value should update in parameter
        assert param.value() == 'Modified text'

    def test_optsChanged_updates_patterns(self, parameter_tree, qtbot):
        """Test that changing patterns via setOpts updates the widget"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice']},
        )

        parameter_tree.setParameters(param, showTop=False)
        items = parameter_tree.listAllItems()
        widget = items[0].widget

        # Initially should have @ pattern
        assert '@' in widget.completers
        assert '#' not in widget.completers

        # Add new pattern via setOpts
        new_patterns = {'@': ['alice', 'bob'], '#': ['python']}
        param.setOpts(patterns=new_patterns)
        qtbot.wait(50)

        # Widget should update
        assert '@' in widget.completers
        assert '#' in widget.completers
        assert widget.completers['@']['completions'] == ['alice', 'bob']

    def test_optsChanged_removes_patterns(self, parameter_tree, qtbot):
        """Test that removing patterns via setOpts updates the widget"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice'], '#': ['python']},
        )

        parameter_tree.setParameters(param, showTop=False)
        items = parameter_tree.listAllItems()
        widget = items[0].widget

        # Both patterns should exist
        assert '@' in widget.completers
        assert '#' in widget.completers

        # Remove # pattern
        param.setOpts(patterns={'@': ['alice']})
        qtbot.wait(50)

        # # pattern should be removed
        assert '@' in widget.completers
        assert '#' not in widget.completers

    def test_optsChanged_updates_config(self, parameter_tree, qtbot):
        """Test that changing completer_config via setOpts updates the widget"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            completer_config={'min_width': 150},
        )

        parameter_tree.setParameters(param, showTop=False)

        # Update config
        param.setOpts(completer_config={'min_width': 300, 'max_width': 600})
        qtbot.wait(50)

        # Config should be updated (checking via parameter opts)
        assert param.opts['completer_config']['min_width'] == 300
        assert param.opts['completer_config']['max_width'] == 600


class TestPatternParameterIntegration:
    """Integration tests for text_pattern parameter"""

    def test_full_example_from_parameter_ex(self, parameter_tree):
        """Test the example from parameter_ex.py"""
        text_params = {
            "name": "text_with_pattern",
            "title": "Text Editing with pattern completion",
            "type": "text_pattern",
            "value": "",
            "patterns": {
                "@": ["alice", "bob", "charlie"],
                "#": ["python", "javascript", "cpp"],
            },
            "completer_config": {
                "min_width": 200,
                "max_width": 400,
                "case_sensitive": False,
                "visual_indicator": True,
            },
        }

        param = Parameter.create(**text_params)
        parameter_tree.setParameters(param, showTop=False)

        assert param.value() == ""
        assert '@' in param.opts['patterns']
        assert '#' in param.opts['patterns']
        assert param.opts['completer_config']['min_width'] == 200

    def test_parameter_in_group(self, parameter_tree):
        """Test text_pattern parameter as child in a group"""
        params = [
            {
                'title': 'Text Group',
                'name': 'text_group',
                'type': 'group',
                'children': [
                    {
                        'name': 'text_pattern_child',
                        'type': 'text_pattern',
                        'value': 'Test',
                        'patterns': {'@': ['alice']},
                    },
                ],
            },
        ]

        root = Parameter.create(name='root', type='group', children=params)
        parameter_tree.setParameters(root, showTop=False)

        text_param = root.child('text_group', 'text_pattern_child')
        assert text_param.type() == 'text_pattern'
        assert text_param.value() == 'Test'

    def test_dynamic_pattern_updates(self, parameter_tree, qtbot):
        """Test dynamically updating patterns after creation"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={'@': ['alice', 'bob']},
        )

        parameter_tree.setParameters(param, showTop=False)

        # Add more users dynamically
        param.update_completions('@', ['alice', 'bob', 'charlie', 'david'])
        qtbot.wait(50)

        assert param.opts['patterns']['@'] == ['alice', 'bob', 'charlie', 'david']

        param.setOpts(patterns={"@": ["alice"]})

        assert param.opts["patterns"]["@"] == ["alice"]
        # Add new pattern
        param.add_pattern('#', ['python', 'java'])
        qtbot.wait(50)

        assert '#' in param.opts['patterns']

    def test_empty_patterns_allowed(self, parameter_tree):
        """Test that empty patterns are allowed"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='Just plain text',
            patterns={},
        )

        parameter_tree.setParameters(param, showTop=False)
        assert param.value() == 'Just plain text'
        assert param.opts['patterns'] == {}

    def test_pattern_with_special_characters(self, parameter_tree):
        """Test patterns with special characters"""
        param = Parameter.create(
            name='test',
            type='text_pattern',
            value='',
            patterns={
                '::': ['function', 'method'],  # Double colon
                '->': ['pointer', 'arrow'],     # Arrow
                '$': ['dollar', 'variable'],      # Dollar sign
            },
        )

        parameter_tree.setParameters(param, showTop=False)
        items = parameter_tree.listAllItems()
        widget = items[0].widget

        assert '::' in widget.completers
        assert '->' in widget.completers
        assert '$' in widget.completers
