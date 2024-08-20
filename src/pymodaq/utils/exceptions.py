class DAQ_ScanException(Exception):
    """Raised when an error occur within the DAQScan"""
    pass


class DetectorError(Exception):
    pass


class ActuatorError(Exception):
    pass


class PIDError(Exception):
    pass


class MasterSlaveError(Exception):
    pass


class ExpectedError(Exception):
    """Raised in the tests made for pymodaq plugins"""
    pass


class Expected_1(ExpectedError):
    """Expected error 1 for pymodaq tests"""
    pass


class Expected_2(ExpectedError):
    """Expected error 2 for pymodaq tests"""
    pass


class Expected_3(ExpectedError):
    """Expected error 3 for pymodaq tests"""
