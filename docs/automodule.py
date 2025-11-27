import sys, subprocess
from pathlib import Path
import importlib.util


if __name__ == "__main__":

    installed_modules = filter(lambda s : s and s.origin, map(lambda m : importlib.util.find_spec(m), ["pymodaq_utils", "pymodaq_gui", "pymodaq_data"]))
    for module in installed_modules:
        module_path =  Path(module.origin).parent
        subprocess.run(["sphinx-apidoc", "-e", "-t",  "./src/_templates/apidoc",  "-o", f"./src/api/{module.name}", f"{module_path}"], check=True)

    with open('./src/api/pymodaq_data/pymodaq_data.h5modules.exporter.rst', 'a') as file:
        file.write('   :exclude-members: H5Exporter\n')
