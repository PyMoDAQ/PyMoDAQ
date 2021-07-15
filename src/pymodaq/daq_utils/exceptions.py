class DAQ_ScanException(Exception):
    """Raised when an error occur within the DAQ_Scan"""


class ScannerException(Exception):
    """Raised when there is an error related to the Scanner class (see pymodaq.da_utils.scanner)"""


class ExpectedError(Exception):
    """Raised in the tests made for pymodaq plugins"""


class Expected_1(ExpectedError):
    """Expected error 1 for pymodaq tests"""


class Expected_2(ExpectedError):
    """Expected error 2 for pymodaq tests"""


class Expected_3(ExpectedError):
    """Expected error 3 for pymodaq tests"""
