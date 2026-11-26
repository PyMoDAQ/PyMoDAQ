"""Assign ontology terms to the channels of the instruments of the PyMoDAQ Dashboard"""
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version('pymodaq_ontology')
except PackageNotFoundError:  # not installed
    __version__ = '0.0.0'
