from importlib import import_module
from pathlib import Path
from .utils import register_scanners


register_scanners()

from .scanner import Scanner  # import this one after the scanners because they have to first be registered
