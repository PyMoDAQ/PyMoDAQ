import datetime
import json

import numpy as np
import pytest

from pymodaq.utils import daq_utils as utils


class TestJsonConverterSafety:
    """json2object rebuilds the stored value of an hdf5 attribute: it must never run what is stored in it"""

    @staticmethod
    def stored(type_name: str, data: str) -> str:
        return json.dumps(dict(module='builtins', type=type_name, data=data))

    @pytest.mark.parametrize('type_name, data', [
        ('str', "__import__('builtins').dir()"),
        ('int', "__import__('sys').maxsize"),
        ('list', "[__import__('sys').version]"),
        ('tuple', "(1, __import__('sys').version)"),
        ('float', "(1).__class__.__name__"),
        ('str', "'a'.__class__.__mro__"),
        ('datetime', "datetime.datetime(2020, 1, 1).__class__"),
        ('float64', "np.sys.version"),
        ('str', "open('a_file_that_should_not_be_opened')"),
    ])
    def test_expressions_are_not_evaluated(self, type_name, data):
        stored = self.stored(type_name, data)

        # what is returned for a type that is not trusted: the decoded dict, nothing is run
        assert utils.JsonConverter.json2object(stored) == json.loads(stored)

    @pytest.mark.parametrize('value', [
        10, -3, 0, 2.5, -0.25, 1e-10, 'a text', "it's \"quoted\"", 'héllo 温度', '', True, False,
        b'some bytes', (10, 5, 'yui'), [10, 5, 'yui'], [1, [2, (3, 4)], 'a'], (), [],
        datetime.datetime(2020, 5, 24, 10, 52, 55), datetime.datetime(2020, 5, 24, 10, 52, 55, 123),
        datetime.datetime(2020, 5, 24, 10, 52, 55, tzinfo=datetime.timezone.utc),
        datetime.date(2020, 5, 24), datetime.time(10, 52, 55), np.float64(2.5),
    ])
    def test_values_round_trip(self, value):
        result = utils.JsonConverter.json2object(utils.JsonConverter.object2json(value))

        assert result == value
        assert type(result) is type(value)

    def test_special_floats_round_trip(self):
        import math
        for value in (float('inf'), float('-inf')):
            assert utils.JsonConverter.json2object(utils.JsonConverter.object2json(value)) == value
        assert math.isnan(utils.JsonConverter.json2object(utils.JsonConverter.object2json(float('nan'))))

    @pytest.mark.parametrize('stored, expected', [
        # as written by older versions, numpy < 2 wrote float64 as a plain float
        ('{"module": "numpy", "type": "float64", "data": "2.5"}', 2.5),
        ('{"module": "builtins", "type": "tuple", "data": "(1, \'a\')"}', (1, 'a')),
        ('{"module": "builtins", "type": "str", "data": "\'text\'"}', 'text'),
        ('{"module": "datetime", "type": "date", "data": "datetime.date(2020, 5, 24)"}',
         datetime.date(2020, 5, 24)),
    ])
    def test_values_written_by_older_versions(self, stored, expected):
        assert utils.JsonConverter.json2object(stored) == expected
