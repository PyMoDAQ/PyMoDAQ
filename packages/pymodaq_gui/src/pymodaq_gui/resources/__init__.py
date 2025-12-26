from pathlib import Path
from importlib import import_module
from importlib.util import spec_from_file_location, module_from_spec

here = Path(__file__).parent

for module in here.joinpath('material_icons', 'resources').iterdir():
    import_module(f'pymodaq_gui.resources.material_icons.resources.{module.stem}')
