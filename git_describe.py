"""
Hatch version script for PyMoDAQ monorepo subpackages.

This script computes the version of a subpackage based on git history and tags.
It is intended to be called by hatch during the build process, receiving the
package path as its first argument:

    python version_script.py packages/pymodaq

Version scheme:
- On release branches (X.Y.x): bump patch + .dev<N> if unreleased commits exist
- On dev branch:               bump minor + .dev<N> if unreleased commits exist
- Pre-release tags (a, b, rc…): strip suffix, no extra bump, + .dev<N> if needed

Tags are expected to be bare semver (e.g. 5.1.9, 5.2.0a1, 5.2.0rc2).
Tags are placed on merge commits, not directly on file-changing commits.
"""

import re
import subprocess
import sys
from pathlib import Path


FALLBACK_VERSION = "5.1.0"  #Version returned when no tag can be found in the package's git history.

PRE_RANK_ORDER = {  # Pre-release order mapping
    "dev": 0,
    "a": 1,
    "alpha": 1,
    "b": 2,
    "beta": 2,
    "preview": 3,
    "rc": 4,
}


def run_git(*args, timeout: int = 30) -> str:
    """Run a git command and return its stdout as a stripped string.

        Raises subprocess.CalledProcessError on non-zero exit.
        Silences stderr to avoid noise from commands like `git describe` that
        print warnings when no tag is found.
        """
    return subprocess.check_output(
        ["git", *args], stderr=subprocess.DEVNULL, timeout=timeout
    ).decode().strip()


def is_release_branch(branch: str) -> bool:
    """Return True if the branch follows the release naming convention <X>.<Y>.x.

    Release branches use patch bumps for dev versions (5.1.11 -> 5.1.12.devN).
    The dev branch uses minor bumps (5.1.11 -> 5.2.0.devN).

    Examples:
        >>> is_release_branch("5.1.x")  # True
        >>> is_release_branch("dev")    # False
    """
    return bool(re.match(r"^\d+\.\d+\.x$", branch))


def parse_semver_tuple(tag: str) -> tuple[int, int, int, int, int] | None:
    """Parse a semver-like tag into a sortable 5-tuple.

       The tuple is (major, minor, patch, pre_rank, pre_num), where pre_rank
       encodes the pre-release type so that tuples sort in correct release order:

           dev(0) < alpha/a(1) < beta/b(2) < preview(3) < rc(4) < release(99)

       Returns None if the tag does not match a recognised semver pattern,
       effectively filtering out noise tags like 'working-preset' or 'v1.0.1'.

       Supported formats:
           5.1.11          -> (5, 1, 11, 99, 0)   # clean release
           5.2.0a2         -> (5, 2, 0,  1,  2)   # alpha
           5.2.0.a3        -> (5, 2, 0,  1,  3)   # alpha with dot separator
           5.2.0alpha      -> (5, 2, 0,  1,  0)   # alpha no number
           5.2.0b3         -> (5, 2, 0,  2,  3)   # beta
           5.2.0rc1        -> (5, 2, 0,  4,  1)   # release candidate
           5.2.0-rc2       -> (5, 2, 0,  4,  2)   # rc with dash separator
       """
    version_match = re.match(
        r"^(\d+)\.(\d+)\.(\d+)(?:[.\-]?(a(?:lpha)?|b(?:eta)?|rc|preview|dev)\.?(\d*))?$",
        tag,
        re.IGNORECASE,
    )

    #No match so return None
    if not version_match:
        return None

    major, minor, patch = int(version_match.group(1)), int(version_match.group(2)), int(version_match.group(3))

    # If there's no prerelease number, it's a full release
    if version_match.group(4) is None:
        return major, minor, patch, 99, 0

    # Otherwise, it's a prerelease and prerelease number is extracted from the established order
    pre_rank = PRE_RANK_ORDER.get(version_match.group(4).lower(), 1)
    #Then a prerelease number is extracted from the last group if existing
    return major, minor, patch, pre_rank, int(version_match.group(5)) if version_match.group(5) else 0


def is_prerelease(tag: str) -> bool:
    """Return True if the tag is a recognized pre-release (alpha, beta, rc…).

    A clean release tag like '5.1.11' returns False.
    Any tag with a pre-release suffix ('5.2.0a1', '5.2.0rc2') returns True.
    Unrecognised tags also return False (parse_semver_tuple returns None).
    """
    t = parse_semver_tuple(tag)
    return t is not None and t[3] != 99


def strip_prerelease(tag: str) -> str:
    """Strip the pre-release suffix from a tag, returning the base version.

       Examples:
           '5.2.0a2'    -> '5.2.0'
           '5.2.0.b3'   -> '5.2.0'
           '5.2.0-rc1'  -> '5.2.0'
           '5.2.0alpha' -> '5.2.0'
       """
    return re.sub(r"[.\-]?(?:a(?:lpha)?|b(?:eta)?|rc|preview|dev)\.?\d*$", "", tag, flags=re.IGNORECASE)


def bump_patch(v: str) -> str:
    """Increment the patch component: '5.1.11' -> '5.1.12'."""
    p = v.split(".")
    p[2] = str(int(p[2]) + 1)
    return ".".join(p)


def bump_minor(v: str) -> str:
    """Increment the minor component and reset patch: '5.1.11' -> '5.2.0'."""
    p = v.split(".")
    p[1] = str(int(p[1]) + 1)
    p[2] = "0"
    return ".".join(p)


def dev_base(tag: str, branch: str) -> str:
    """Compute the base version string to prepend to a .dev<N> suffix.

       Rules:
       - Pre-release tag (e.g. '5.2.0a2'): strip suffix -> '5.2.0'
         The tag already encodes the next minor, so no further bump is needed.
       - Clean tag on a release branch (e.g. '5.1.11' on '5.1.x'): bump patch -> '5.1.12'
       - Clean tag on dev branch (e.g. '5.1.11' on 'dev'): bump minor -> '5.2.0'
       """
    if is_prerelease(tag):
        return strip_prerelease(tag)
    if is_release_branch(branch):
        return bump_patch(tag)
    return bump_minor(tag)


def get_tag_containing(commit_hash: str) -> str | None:
    """Find the earliest release that included a given commit.

    Because tags in this repo are placed on merge commits (not directly on
    file-changing commits), a single file-changing commit may be reachable
    from several tags (e.g. 5.1.9, 5.1.10, 5.1.11 all 'contain' the same
    underlying commit). We want the *lowest* (earliest) such tag — the first
    release that actually shipped that commit.

    We also intersect with '--merged HEAD' to exclude tags that exist in the
    repo but are not yet reachable from the current branch (e.g. a future tag
    created on a different branch that happens to share ancestor commits).

    Returns None if no valid semver tag contains this commit on this branch.
    """
    try:
        # Tags whose ancestry includes commit_hash (commit is reachable from tag)
        containing = set(run_git("tag", "--contains", commit_hash).splitlines())
        # Tags that are ancestors of HEAD (already released on this branch)
        merged = set(run_git("tag", "--merged", "HEAD").splitlines())

        #Candidates are valid tags that are both contained and merged.
        candidates = [
            (parse_semver_tuple(t), t)
            for t in (containing & merged)
            if parse_semver_tuple(t.strip()) is not None
        ]

        #Take the smallest candidates of the form ((x.y.z.pre.n), "x.y.z.pre.n")
        #by comparing the first part and returning the second
        return min(candidates, key=lambda x: x[0])[1] if candidates else None
    except subprocess.CalledProcessError:
        return None


def compute_version(package_path: Path) -> str:
    """Compute the version string for a subpackage.

      Algorithm:
      1. Get the current branch name.
      2. Retrieve the commits that touched package_path (newest first).
      3. Walk those commits until we find one that is contained by a tag on this
         branch — that tag is the last released version of this package.
      4. Count how many commits have touched this package since that tag.
      5. If distance is 0, the package is exactly at the tagged version.
         Otherwise, append a .dev<N> suffix with the appropriate version bump.

      The commit-walking approach (step 3) is necessary because tags sit on merge
      commits, not on the file-changing commits returned by rev-list. Walking back
      through the package's own commit history ensures we find the correct
      per-package tag regardless of unrelated commits on the branch.
      """
    branch = run_git("rev-parse", "--abbrev-ref", "HEAD")

    # Collect the commits that touched this package, newest first.
    commits = run_git("rev-list", "HEAD", "--", str(package_path)).splitlines()
    if not commits:
        return FALLBACK_VERSION

    # Walk commits newest-to-oldest, stop at the first one covered by a tag.
    # This is the most recent release that included a change to this package.
    base_tag = FALLBACK_VERSION
    for c in commits:
        tag = get_tag_containing(c.strip())
        if tag:
            base_tag = tag
            break
    # Count commits touching this package that came after the base tag.
    # This is the .dev<N> distance and determines whether we're on a clean release.
    distance = int(run_git("rev-list", "--count", f"{base_tag}..HEAD", "--", str(package_path)) or 0)

    return base_tag if distance == 0 else f"{dev_base(base_tag, branch)}.dev{distance}"


if __name__ == "__main__":
    try:
        print(compute_version(Path(sys.argv[1])))
    except Exception:
        print(FALLBACK_VERSION)
