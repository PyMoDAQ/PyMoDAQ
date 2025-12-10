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
        "pymodaq",
    ]

def parse_args():
    parser = argparse.ArgumentParser(
        description="Install all four PyMoDAQ packages in the right order (by default in editable mode)."
    )

    parser.add_argument(
        "-d", "--dev",
        action="store_true",
        help="Also install dev requirements"
    )

    parser.add_argument(
        "-n", "--non-editable",
        action="store_true",
        help="Install packages in non-editable (normal) mode."
    )

    parser.add_argument(
        "-u", "--up-to",
        type=lambda value: value.lower(),
        choices=PYMODAQ_PACKAGES,
        default='pymodaq',
        help="Select up to which package to install. (e.g. '-o pymodaq_data' will install utils and data packages but not gui and PyMoDAQ itself)"
    )

    return parser.parse_args()

def slice_up_to(ordered_list, element):
    return ordered_list[0:ordered_list.index(element)+1]

def main():
    args = parse_args()
    current_dir = Path(__file__).resolve().parent

    packages = slice_up_to(PYMODAQ_PACKAGES, args.up_to)

    for package in map(lambda package : current_dir / "packages" / package, packages):
        cmd = [sys.executable, "-m", "pip", "install"]
        if not args.non_editable:
            cmd.append("-e")
        cmd.append(str(package))
        if args.dev:
            cmd[-1] += '[dev]'
        subprocess.run(cmd, check=True)
        
if __name__ == "__main__":
    main()
