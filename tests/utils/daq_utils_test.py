import random

import numpy as np
import os
import pytest
import re
from pathlib import Path
import datetime

from pymodaq.utils import daq_utils as utils


def test_get_plugins():  # run on local with pytest option --import-mode=importlib
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins()]
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins('daq_move')]
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins('daq_0Dviewer')]
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins('daq_1Dviewer')]
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins('daq_2Dviewer')]

