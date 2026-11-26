import pytest

from pymodaq_ontology.sources import SourceFactory

TERMS_FILE = '''
[[term]]
iri = "http://example.org/moke#PhotodiodeSignalA"
label = "Photodiode signal A"
category = "Detection"
description = "Voltage of the first diode."
roles = ["detector"]

[[term]]
iri = "http://example.org/moke#MagneticField"
label = "Applied magnetic field"
category = "Control"
description = "Field applied to the sample."
roles = ["actuator"]

[[term]]
iri = "http://example.org/moke#SampleTemperature"
label = "Sample temperature"
category = "Environment"
'''


@pytest.fixture
def terms_path(tmp_path):
    path = tmp_path / 'moke.toml'
    path.write_text(TERMS_FILE, encoding='utf-8')
    return path


@pytest.fixture
def source(terms_path):
    return SourceFactory.create('terms', str(terms_path))
