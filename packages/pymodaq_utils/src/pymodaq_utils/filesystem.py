import logging
import os
import platform
import subprocess
import ctypes
import shutil
import time

from pathlib import Path
from subprocess import CalledProcessError
from typing import Union





logger = logging.getLogger(Path(__file__).stem)

SYSTEM = platform.system()  # "Windows", "Linux", "Darwin"

def __wait_for_path(path: str, timeout: float = 1.0) -> bool:
    """Poll until a path exists or the timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if os.path.exists(path):
            return True
        time.sleep(0.2)
    return False

def __elevate_windows(*commands: str) -> bool:
    """
    Run one or more cmd.exe commands with a single UAC elevation prompt.
    Commands are chained with '&&'.

    Attributes
    ----------
    *commands: Each command is a list of strings.

   Returns
   -------
        bool: True if elevation and commands exeution was successfull, False otherwise
    """
    cmd_chain = " && ".join(commands)
    ret = ctypes.windll.shell32.ShellExecuteW(
        None,       # parent HWND
        "runas",    # UAC
        "cmd.exe",
        f'/c {cmd_chain}',
        None,
        0           # SW_HIDE
    )
    if ret <= 32:
        logger.error(f"Windows elevation via UAC failed.")
        return False

    return True

def __elevate_unix(*commands: list[str]) -> bool:
    """
    Run one or more commands with a single elevated session on Linux/macOS,
    so the user is only prompted for a password once.
    Commands are chained with '&&' under a single sh -c call.

    On Linux:  tries pkexec (graphical) then sudo (terminal).
    On macOS:  uses osascript 'do shell script ... with administrator privileges'.

    Attributes
    ----------
    *commands: Each command is a list of strings, e.g.
        ["mkdir", "-p", "/some/path"], ["chmod", "755", "/some/path"]

   Returns
   -------
        bool: True if elevation and commands exeution was successfull, False otherwise
    """
    def quote(arg: str) -> str:
        return f'"{arg}"' if " " in arg else arg

    shell_cmd = " && ".join(
        " ".join(quote(a) for a in cmd)
        for cmd in commands
    )

    if SYSTEM == "Linux":
        wrapped = ["sh", "-c", shell_cmd]

        def try_run(prefix: list[str]) -> bool:
            return subprocess.run(prefix + wrapped, capture_output=True).returncode == 0

        if not try_run(["pkexec"]):
            logger.error("Linux elevation via pkexec failed.")
            return False
    else:
        # macOS — escape inner double-quotes for the osascript string
        escaped = shell_cmd.replace('"', '\\"')
        script = f'do shell script "{escaped}" with administrator privileges'
        result = subprocess.run(["osascript", "-e", script], capture_output=True)
        if result.returncode != 0:
            logger.error(f"macOS elevation via osascript failed: {result.stderr.decode().strip()}")
            return False
    return True

def create_folder_with_elevation(path: str | Path, mode: int = 0o755) -> bool:
    """
    Create a folder at `path` with the given permissions.
    On Unix, uses 'mkdir -m' so that mode and creation are a single atomic
    operation, avoiding a separate chmod call (and a second password prompt
    when elevation is required).

    Args:
     Attributes
    ----------
    path:
        Target directory path.
    mode:
        Unix permission bits. Default 0o755.
   Returns
   -------
        bool: True if successful, False otherwise
    """

    path = str(path)

    if SYSTEM == "Windows":
        __elevate_windows(f'mkdir "{path}"')
    else:
        octal_str = oct(mode)[2:]   # e.g. 0o755 → "755"
        __elevate_unix(["mkdir", "-m", octal_str, "-p", path])

    if not __wait_for_path(path):
        logger.error(f"Folder not found after elevation: {path}")
        return False

    logger.debug(f"Folder created (elevated): {path}")
    return True


def rename_with_elevation(old: str | Path, new: str | Path) -> bool:
    """
    Rename (move) a file or folder from `old` to `new`.

    On Unix, uses 'mv' under elevation when required.
    On Windows, uses 'move' under elevation.

    This ensures the rename is executed atomically at the OS level
    and avoids separate privilege escalation steps.

    Args:
    ----
    old_path:
        Existing file or directory path.
    new_path:
        Destination path.

    Returns
    -------
    bool
        True if rename succeeded, False otherwise.
    """

    old = str(old)
    new = str(new)

    if SYSTEM == "Windows":
        # Windows: move command handles both file and directory renames
        __elevate_windows(f'move "{old}" "{new}"')
    else:
        # Unix: mv is the standard rename/move operation
        __elevate_unix(["mv", old, new])

    if not __wait_for_path(new):
        logger.error(f"Rename failed: {old} -> {new}")
        return False

    logger.debug(f"Renamed (elevated): {old} -> {new}")
    return True

def link_or_copy(src : Union[str, Path], dst : Union[str, Path]) -> None:
    '''
    Tries to reate a symlink of src at dst. If not possible, tries to create a
    Junction (Windows/NTFS specific symlinks). Otherwise,falls back to copying src to dst.

    A symlink may not always be possible as Windows may need administrative or developer
    rights to create them. Junctions are NTFS-specific so it depends on the storage format.

    Raises NotADirectoryError if the source is not a directory.
    Raises FileExistsError if the destination already exists.
    Parameters
    ----------
    src: Union[str, Path]
        The src path to symlink or copy
    dst: Union[str, Path]
        The dst path of the symlink or copy

    Returns
    -------
    None

    '''
    src = Path(src).resolve()
    dst = Path(dst).resolve()

    if not src.is_dir():
        raise NotADirectoryError(f'Source is not an existing directory: {src}')
    if dst.exists():
        raise FileExistsError(f'Destination already exists: {dst}')
    # Symlink
    try:
        dst.symlink_to(src, target_is_directory=True)
    except (OSError,NotImplementedError) as e:
        # from pymodaq_utils import logger as logger_module
        #
        # logger = logger_module.set_logger(logger_module.get_module_name(__file__))
        # logger.info(f'Symlink not possible: {e}')
        pass
    else:
        return

    # Junction
    try:
        subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
             check=True,
             stdout=subprocess.DEVNULL,
             stderr=subprocess.DEVNULL,
        )
    except (OSError, CalledProcessError) as e:
        # from pymodaq_utils import logger as logger_module
        #
        # logger = logger_module.set_logger(logger_module.get_module_name(__file__))
        # logger.info(f'Junction not possible: {e}')
        pass
    else:
        return

    shutil.copytree(src, dst)

def unlink_or_delete(dst : Union[str, Path]) -> None:
    dst = Path(dst).absolute()
    if dst.is_symlink() or dst.is_junction():
        dst.unlink()
    else:
        shutil.rmtree(dst)