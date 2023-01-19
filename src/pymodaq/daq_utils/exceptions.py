class DAQ_ScanException(Exception):
    """Raised when an error occur within the DAQ_Scan"""
    pass


class ScannerException(Exception):
    """Raised when there is an error related to the Scanner class (see pymodaq.da_utils.scanner)"""
    pass


class DetectorError(Exception):
    pass


class ActuatorError(Exception):
    pass


class ViewerError(Exception):
    pass


class DataSourceError(Exception):
    pass


class InvalidExport(Exception):
    pass


class InvalidGroupType(Exception):
    pass


class InvalidSave(Exception):
    pass


class InvalidGroupDataType(Exception):
    pass


class InvalidDataType(Exception):
    pass


class InvalidDataDimension(Exception):
    pass


class InvalidScanType(Exception):
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
