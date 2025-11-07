import subprocess
import sys
from pathlib import Path


FALLBACK_VERSION = "5.1.0"

try:
    package_path = Path(sys.argv[1])
    # Get the last commit touching the package
    commit_hash = (
        subprocess.check_output(
            ["git", "rev-list", "-1", "HEAD", "--", str(package_path)],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    )

    try:
        version = subprocess.check_output(
            ["git", "describe", "--contains", "--tags", commit_hash],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except subprocess.CalledProcessError:
        version = subprocess.check_output(
            ["git", "describe", "--tags", commit_hash],
            stderr=subprocess.DEVNULL
        ).decode().strip()

    # Remove "~1" or similar suffix
    version = version.split("~")[0]
except Exception:
    version = FALLBACK_VERSION

print(version)

