import pytest

from pymodaq_utils.help import get_help_text

from pymodaq.dashboard import DashBoard
from pymodaq.extensions.adaptive_optim.adaptive_optimization import AdaptiveOptimisation
from pymodaq.extensions.bayesian.bayesian_optimization import BayesianOptimization
from pymodaq.extensions.console import Console
from pymodaq.extensions.daq_logger.daq_logger import DAQLogger
from pymodaq.extensions.data_mixer.data_mixer import DataMixer
from pymodaq.extensions.pid.pid_controller import DAQ_PID
from pymodaq.extensions.ramping.ramping import RampExtension
from pymodaq.extensions.scan.daq_scan import DAQScan
from pymodaq.extensions.sequencer.sequencer import Sequencer
from pymodaq_gui.h5modules.h5browser import H5Browser


@pytest.mark.parametrize('module, title', [
    (DashBoard, 'DashBoard'),
    (DAQScan, 'DAQ_Scan'),
    (DAQLogger, 'DAQ_Logger'),
    (Sequencer, 'Sequencer'),
    (RampExtension, 'Ramping'),
    (DAQ_PID, 'PID'),
    (DataMixer, 'DataMixer'),
    (BayesianOptimization, 'Bayesian Optimisation'),
    (AdaptiveOptimisation, 'Adaptive Scanning'),
    (Console, 'Console'),
    (H5Browser, 'H5Browser'),
])
def test_help_of_the_modules(module, title):
    text = get_help_text(module)
    assert text is not None, f'no help file found for {module}'
    assert text.startswith(f'# {title}\n')
    intro = text.split('<!-- end of intro -->')[0]
    assert '<!-- end of intro -->' in text
    assert '## Typical workflow' in intro and '## Good to know' in intro
    assert '## Full documentation' in text.split('<!-- end of intro -->')[1]


def test_single_file_modules_have_their_own_help():
    # the Dashboard, the Console and the H5Browser share their folder with other modules
    assert get_help_text(DashBoard) != get_help_text(Console)
