import logging
import os
import platform
import subprocess
import ctypes
import shutil
import sys
import time

from pathlib import Path
from subprocess import CalledProcessError
from typing import Union





logger = logging.getLogger(Path(__file__).stem)

SYSTEM = platform.system()  # "Windows", "Linux" or "Darwin"

__elevation_cancelled = False #If it's canceled once, don't ever try to ask again

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
    command_chain = " && ".join(commands)
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,       # parent window
            "runas",    # UAC
            "cmd.exe",
            f'/c {command_chain}',
            None,
            0           # to not show the cmd.exe window
        )
    except Exception as e:
        logger.error(f"Windows elevation via UAC failed. ({e})")
        return False
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
        #if there
        return f'"{arg}"' if " " in arg else arg

    shell_commands = " && ".join(
        " ".join(quote(a) for a in cmd)
        for cmd in commands
    )

    if SYSTEM == "Linux":
        try:
            result = subprocess.run(["pkexec", "sh", "-c", shell_commands], capture_output=True).returncode
        except Exception as e:
            logger.error(f"Linux elevation via pkexec failed. ({e})")
            return False
        if result != 0:
            logger.error("Linux elevation via pkexec failed.")
            return False
    else:
        # macOS — escape inner double-quotes for the osascript string
        escaped = shell_commands.replace('"', '\\"')
        script = f'do shell script "{escaped}" with administrator privileges'
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True)
        except Exception as e:
            logger.error(f"macOS elevation via osascript failed: {e}")
            return False
        if result.returncode != 0:
            logger.error(f"macOS elevation via osascript failed: {result.stderr.decode().strip()}")
            return False
    return True

def warn_about_elevation_prompt(reason: str):
    """
    Warns an user about the upcoming elevation message, trying different methods. First qt, then tkinter and in the
    worst case, in the console.
    Parameters
    ----------
    reason: the reason for rights elevation.
    """
    title = "Admin rights needed"
    msg = f"PyMoDAQ needs admin rights to {reason}.\nPlease enter your password in the next prompt."

    # Try Qt first
    try:
        from qtpy.QtWidgets import QApplication, QMessageBox
        existing_app = QApplication.instance()
        app = existing_app or QApplication(sys.argv)
        QMessageBox.information(None, title, msg)
        if not existing_app:
            app.quit()
            del app
        return
    except Exception:
        pass

    # Try tkinter
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()

        dialog = tk.Toplevel(root)
        dialog.title(title)
        dialog.resizable(False, False)

        tk.Label(dialog, text=msg, wraplength=380, justify="left", padx=20, pady=20).pack(expand=True, fill="both")
        tk.Button(dialog, text="OK", width=10, command=dialog.destroy).pack(pady=(0, 15))

        dialog.update_idletasks()  # Let tkinter compute the size first
        dialog.geometry(f"450x{dialog.winfo_reqheight()}")  # Force width, let height be natural

        dialog.grab_set()
        root.wait_window(dialog)
        root.destroy()
        return
    except Exception:
        pass

    # Fallback to console
    import threading
    print(f"\n{'#' * 60}\n{msg}\n{'#' * 60}\n", file=sys.stderr, flush=True)
    print("Press Enter to continue... (auto-continues in 5s)", file=sys.stderr, flush=True)

    entered = threading.Event()
    threading.Thread(target=lambda: (input(), entered.set()), daemon=True).start()
    entered.wait(timeout=5)

def create_folder_with_elevation(path: Union[str, Path], mode: int = 0o757) -> bool:
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
        Unix permission bits. Default 0o757.
   Returns
   -------
        bool: True if successful, False otherwise
    """
    global __elevation_cancelled

    if not __elevation_cancelled:
        path = str(path)

        warn_about_elevation_prompt("create /etc/.pymodaq to store its configuration.")
        if SYSTEM == "Windows":
            __elevation_cancelled = not __elevate_windows(f'mkdir "{path}"')
        else:
            octal_str = oct(mode)[2:]   # 0o757 → "757"
            __elevation_cancelled = not __elevate_unix(["mkdir", "-m", octal_str, "-p", path])

        if not __wait_for_path(path):
            logger.error(f"Folder not found after elevation: {path}")
            return False

        logger.debug(f"Folder created (elevated): {path}")
        return True
    return False

def rename_with_elevation(old: Union[str, Path], new: Union[str, Path], recreate: bool = False) -> bool:
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
    recreate:
        If True, recreate `old` as an empty directory with the same mode
        after the move. Default is False.

    Returns
    -------
    bool
        True if rename succeeded, False otherwise.
    """

    global __elevation_cancelled
    if not __elevation_cancelled:

        old = str(old)
        new = str(new)

        warn_about_elevation_prompt("rename existing /etc/.pymodaq.")

        if SYSTEM == "Windows":
            commands  = [f'move "{old}" "{new}"']
            if recreate:
                commands.append(f'mkdir "{old}"')
            __elevation_cancelled = not __elevate_windows(*commands)
        else:
            # Get mode of the old directory before moving it, so the
            # recreated folder gets the exact same permission.
            try:
                old_mode = oct(Path(old).stat().st_mode & 0o777)[2:]
            except OSError:
                old_mode = "757"

            commands = [["mv", str(old), str(new)]]
            if recreate:
                commands.append(["mkdir", "-m", old_mode, "-p", str(old)])
            __elevation_cancelled = not __elevate_unix(*commands)

        if not __wait_for_path(new):
            logger.error(f"Rename failed: {old} -> {new}")
            return False

        if recreate and not __wait_for_path(str(old)):
            logger.error(f"Recreated folder not found after elevation: {old}")
            return False

        logger.debug(f"Renamed (elevated): {old} -> {new}")
        return True
    return False

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