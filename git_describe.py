import re
import subprocess
import sys
from pathlib import Path


FALLBACK_VERSION = "5.1.0"


def run_git(*args) -> str:
    return subprocess.check_output(
        ["git", *args],
        stderr=subprocess.DEVNULL,
    ).decode().strip()


def get_current_branch() -> str:
    try:
        return run_git("rev-parse", "--abbrev-ref", "HEAD")
    except subprocess.CalledProcessError:
        return "unknown"


def is_release_branch(branch: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.x$", branch))


def is_clean_semver(tag: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+$", tag))


def get_last_commit_for_package(package_path: Path) -> str | None:
    try:
        result = run_git("rev-list", "-1", "HEAD", "--", str(package_path))
        return result if result else None
    except subprocess.CalledProcessError:
        return None


def get_nearest_tag_containing(commit_hash: str) -> str | None:
    """
    Lowest clean semver tag that contains commit_hash
    (i.e. the first release tag applied after this commit).
    """
    try:
        raw = run_git("tag", "--contains", commit_hash, "--sort=version:refname")
        for tag in raw.splitlines():
            tag = tag.strip()
            if is_clean_semver(tag):
                return tag
        return None
    except subprocess.CalledProcessError:
        return None


def get_latest_reachable_tag() -> str | None:
    """Highest clean semver tag reachable from HEAD."""
    try:
        raw = run_git("tag", "--merged", "HEAD", "--sort=-version:refname")
        for tag in raw.splitlines():
            tag = tag.strip()
            if is_clean_semver(tag):
                return tag
        return None
    except subprocess.CalledProcessError:
        return None


def get_distance_from_tag(tag: str, package_path: Path) -> int:
    """Count commits touching package_path between tag and HEAD."""
    try:
        result = run_git("rev-list", "--count", f"{tag}..HEAD", "--", str(package_path))
        return int(result) if result else 0
    except subprocess.CalledProcessError:
        return 0


def bump_patch(version: str) -> str:
    """'5.1.11' -> '5.1.12'"""
    parts = version.split(".")
    parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def bump_minor(version: str) -> str:
    """'5.1.11' -> '5.2.0'"""
    parts = version.split(".")
    parts[1] = str(int(parts[1]) + 1)
    parts[2] = "0"
    return ".".join(parts)


def compute_version(package_path: Path) -> str:
    commit_hash = get_last_commit_for_package(package_path)
    if not commit_hash:
        return FALLBACK_VERSION

    containing_tag = get_nearest_tag_containing(commit_hash)
    bump = bump_patch if is_release_branch(get_current_branch()) else bump_minor

    if containing_tag:
        # Last package commit is covered by a release tag — check if
        # there are further unreleased commits on top of it
        distance = get_distance_from_tag(containing_tag, package_path)
        if distance == 0:
            return containing_tag
        else:
            return f"{bump(containing_tag)}.dev{distance}"
    else:
        # No tag contains this commit at all — use latest reachable tag
        base = get_latest_reachable_tag() or FALLBACK_VERSION
        distance = get_distance_from_tag(base, package_path)
        return f"{bump(base)}.dev{distance}" if distance else base


if __name__ == "__main__":
    try:
        package_path = Path(sys.argv[1])
        print(compute_version(package_path))
    except Exception:
        print(FALLBACK_VERSION)