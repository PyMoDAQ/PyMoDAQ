import site
from os import system

pymodaq_module_list = ["pymodaq_utils", "pymodaq_gui", "pymodaq_data"]

if __name__ == "__main__":

    module_path = [path for path in site.getsitepackages() if path.endswith("site-packages")][0]

    for module in pymodaq_module_list:
        system(f"sphinx-apidoc -e -t ./docs/src/_templates/apidoc -o ./docs/src/api/{module} {module_path}/{module}")

    with open('./docs/src/api/pymodaq_data/pymodaq_data.h5modules.exporter.rst', 'a') as file:
        file.write('   :exclude-members: H5Exporter\n')
