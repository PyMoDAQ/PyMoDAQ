#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path


# Order is important!
PYMODAQ_PACKAGES = [
        "pymodaq_utils",
        "pymodaq_data",
        "pymodaq_gui",
        "pymodaq_scripting",
        "pymodaq",
    ]

# Optional add-ons, installed after (and needing) the packages above, on request: option -> package
OPTIONAL_PACKAGES = {
        "ontology": "pymodaq_ontology",
    }

def parse_args():
    parser = argparse.ArgumentParser(
        description="Install the PyMoDAQ packages in the right order (by default in editable mode).",
    )

    parser.add_argument(
        "-d", "--dev",
        action="store_true",
        help="Also install dev requirements",
    )

    parser.add_argument(
        "-n", "--non-editable",
        action="store_true",
        help="Install packages in non-editable (normal) mode.",
    )

    parser.add_argument(
        "-u", "--up-to",
        type=lambda value: value.lower(),
        choices=PYMODAQ_PACKAGES,
        default='pymodaq',
        help="Select up to which package to install. (e.g. '-u pymodaq_data' will install utils and data packages but not gui and PyMoDAQ itself)",
    )

    parser.add_argument(
        "-qt", "--qt_backend",
        type=lambda value: value.lower(),
        choices=['pyside6', 'pyqt6'],
        default='pyside6',
        help="Select the qt backend to install (e.g. '-qt pyside6' will install the pyside6 backend",
    )

    for option, package in OPTIONAL_PACKAGES.items():
        parser.add_argument(
            f"--{option}",
            action="store_true",
            help=f"Also install {package} (an optional add-on, needs all the packages up to pymodaq)",
        )

    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Also install all the optional add-ons ({', '.join(OPTIONAL_PACKAGES.values())})",
    )

    args = parser.parse_args()
    wanted = [package for option, package in OPTIONAL_PACKAGES.items() if args.all or getattr(args, option)]
    if wanted and args.up_to != 'pymodaq':
        parser.error(f"{', '.join(wanted)} needs all the packages up to pymodaq: do not use -u/--up-to")
    args.optional_packages = wanted
    return args

def slice_up_to(ordered_list, element):
    return ordered_list[0:ordered_list.index(element)+1]

def main():
    args = parse_args()
    current_dir = Path(__file__).resolve().parent

    packages = slice_up_to(PYMODAQ_PACKAGES, args.up_to) + args.optional_packages

    for package in map(lambda package : current_dir / "packages" / package, packages):
        option = ""
        cmd = [sys.executable, "-m", "pip", "install"]
        if not args.non_editable:
            cmd.append("-e")
        cmd.append(str(package))
        if args.dev:
            option = '[dev]'
        if (args.qt_backend and package.name in PYMODAQ_PACKAGES
                and not ('pymodaq_utils' in str(package) or 'pymodaq_data' in str(package))):
            # no qt installation for pymodaq_utils and data
            if args.dev:
                option = f'[dev, {args.qt_backend}]'
            else:
                option = f'[{args.qt_backend}]'
        cmd[-1] += option
        subprocess.run(cmd, check=True)
        
if __name__ == "__main__":
    main()
