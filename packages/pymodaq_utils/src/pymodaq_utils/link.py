import shutil
import subprocess


from pathlib import Path
from subprocess import CalledProcessError
from typing import Union





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