#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Install PyMoDAQ packages (optionally in editable mode)."
    )
    parser.add_argument(
        "-e", "--editable",
        action="store_true",
        help="Install packages in editable mode."
    )

    return parser.parse_args()

def main():
    args = parse_args()

    current_dir = Path(__file__).resolve().parent
    packages = [
        current_dir / "packages" / "pymodaq_utils",
        current_dir / "packages" / "pymodaq_data",
        current_dir / "packages" / "pymodaq_gui",
        current_dir / "packages" / "pymodaq",
    ]

    for package in packages:      
        cmd = [sys.executable, "-m", "pip", "install"]
        if args.editable:
            cmd.append("-e")
        cmd.append(str(package))
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
