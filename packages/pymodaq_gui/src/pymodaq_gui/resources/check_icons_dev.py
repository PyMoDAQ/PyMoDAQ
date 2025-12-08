"""
This script is meant for developers. Run it FROM the command line using:

```
 python -m pymodaq_gui.resources.check_icons_dev
```

to make sure the list of icons specified in the icons.toml file are
present in the resource folder of qt_material_icons module
"""
import sys

from pathlib import Path
import toml
import importlib
extract = importlib.import_module('qt_material_icons.extract')



resource_folder = Path(__file__).parent
icon_config = toml.load(resource_folder.joinpath('icons.toml'))

styles = icon_config['icons']['style']
sizes = icon_config['icons']['size']
names = icon_config['icons']['names']

# qtmaterialicons -o 'path/to/resources' --styles outlined rounded  --sizes 40 --names home computer search favorite toggle_off toggle_on

styles = tuple(extract.MaterialIcon.Style(s) for s in styles)

extract.extract_package(output=str(resource_folder))
extract.extract_icons(
    names=names,
    styles=styles,
    fill=False,
    sizes=sizes,
    output=str(resource_folder),
)
