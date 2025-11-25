from pymodaq_utils.enums import StrEnum


class OptimizerToRunner(StrEnum):
    """ Allowed Generic commands sent from an Optimizer to its thread running class

    """
    START = 'start'
    RUN = 'run'
    PAUSE = 'pause'
    STOP = 'stop'
    STOPPING = 'stopping'
    BOUNDS = 'bounds'
    RESTART = 'restart'
    PREDICTION = 'prediction'


class OptimizerThreadStatus(StrEnum):

    ADD_DATA = "add_data"
    TRADE_OFF = "tradeoff"

