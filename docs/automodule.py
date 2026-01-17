import sys, subprocess
from pathlib import Path
import importlib.util


if __name__ == "__main__":
    doc_path = Path(__file__).parent
    installed_modules = filter(lambda s : s and s.origin, map(lambda m : importlib.util.find_spec(m), ["pymodaq_utils", "pymodaq_gui", "pymodaq_data"]))
    for module in installed_modules:
        module_path =  Path(module.origin).parent
        template_path = doc_path / "src" / "_templates" / "apidoc"
        output_path   = doc_path / "src" / "api" / module.name

        subprocess.run(["sphinx-apidoc", "-e", "-t",  template_path,  "-o", output_path, module_path], check=True)

    with open(doc_path / "src" / "api" / "pymodaq_data" / "pymodaq_data.h5modules.exporter.rst", 'a') as file:
        file.write('   :exclude-members: H5Exporter\n')
