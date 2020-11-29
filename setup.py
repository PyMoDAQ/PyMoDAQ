from setuptools import setup
from pathlib import Path
with open(str(Path(__file__).parent.joinpath('src/pymodaq/ressources/VERSION')), 'r') as fvers:
    version = fvers.read().strip()
setup(version=version)
