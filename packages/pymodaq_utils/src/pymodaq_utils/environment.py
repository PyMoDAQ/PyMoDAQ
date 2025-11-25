import os
import sys
import glob
import logging
import subprocess

from pathlib import Path
from datetime import datetime

from pymodaq_utils import config as configmod
from pymodaq_utils.config import get_set_local_dir
from pymodaq_utils.logger import set_logger, get_module_name


logger = set_logger(get_module_name(__file__))

config = configmod.Config()


def guess_virtual_environment() -> str:
    '''
        Try to guess the current python environment used.

        Returns
        -------
        str: the guessed environment name or the string "unknown"
    '''
    def _venv_name_or_path():
        #Try to guess from system environment
        for var in ['VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 'PYENV_VERSION', 'TOX_ENV_NAME']:
            value = os.environ.get(var)
            if value:
                return value
        #if true, probably running in a venv
        if sys.prefix != sys.base_prefix:
            return sys.prefix
        return 'unknown'
    return Path(_venv_name_or_path()).name


class EnvironmentBackupManager:
    '''
        A class to manage rotating backups of python environments, controlled by entries in 
        [backup] section of the configuration.

    '''
    def __init__(self):
        # Path is: <local_config_path>/<backup_path(default=environments)>/<venv_name>/
        self._path = get_set_local_dir(user=True) / config['backup']['folder'] / guess_virtual_environment()
        self._path.mkdir(parents=True, exist_ok=True)
        
        self._backups = self._load()
        self._newest = PythonEnvironment.from_freeze()

    def _load(self):
        '''
            Loads and returns all environment backups stored in `self._path` into PythonEnvironment
            objects, then sort them by date.

            Returns
            ----------
            [PythonEnvironment]: 
                A sorted list of PythonEnvironment objects (from oldest to newest)
        '''
        environments = []
        filenames = list(self._path.glob('*.txt'))

        logger.info(f'Found {len(filenames)} environment backup files: {filenames}')

        for name in filenames:
            environments.append(PythonEnvironment.from_file(name))
        return sorted(environments, key=PythonEnvironment.date)


    def _should_save(self):
        # current backup should be saved if there's no backup or if it's different from the oldest
        return len(self._backups) == 0 or self._newest != self._backups[-1]

    def _remove_oldest(self):
        # remove from the list and from disk
        env = self._backups.pop(0)
        env.remove()

    def _save_newest(self):
        # save to disk and the list
        self._newest.save()
        self._backups.append(self._newest)

    def save_backup(self):
        '''
            Save the current environment if there is no backup or if it's different
            from the oldest one.

            Also, remove the oldest one(s) if there's more than the limit defined in configuration.
        '''
        if self._should_save():
            logger.info(f'Current environment is different than the last one. Keeping backup.')
            self._save_newest()

        while len(self._backups) != 0 and len(self._backups) > config['backup']['limit']:
            logger.info(f'Too many backups, deleting the oldest one.')
            self._remove_oldest()


class PythonEnvironment:
    '''
        A class to represent a python environment and creates/delete backups.

        Preferably, it is instanciated using one the following static method:
         - `from_freeze`: to perform a pip freeze and allowing to save it
         - `from_file`: to read a file and allowing to delete it
    '''
    DATE_FORMAT = "%Y%m%d%H%M%S"

    def __init__(self, filename=None):
        # set comparison is easy, order does not matter
        self._packages = set()
        storage_path = get_set_local_dir(user=True) / config['backup']['folder'] / guess_virtual_environment()
        self._path = Path(filename) if filename else storage_path / f'{datetime.now().strftime(PythonEnvironment.DATE_FORMAT)}_environment.txt'
        
        # Shouldn't be necessary, but ensure it exists  
        storage_path.mkdir(parents=True, exist_ok=True)
    
    def __eq__(self, other):
        # Two environements are the same if they share the same packages
        if isinstance(other, PythonEnvironment):
            return self._packages == other._packages
        return False

    def date(self):
        '''
            Gets the date at which this environment was created from its filename.
            If not possible it fallbacks to its creation/modification date (depending on the OS)
            If still not possible it fallbacks to now.

            It allows to sort them by date, without having to declare comparison 
            operators that aren't consistant with __eq__.

            Returns
            ----------
            datetime: 
                The date associated with this environment
        '''
        try:
            date_in_filename = self._path.name.split('_')[0]
            return datetime.strptime(date_in_filename, PythonEnvironment.DATE_FORMAT)
        except ValueError:
            logging.warning(f'Date is not defined in filename for: {self._path.name}. Guessing from file date.')

        if self._path.is_file():
            try:
                return datetime.fromtimestamp(self._path.stat().st_ctime)
            except:
                pass
        logging.warning(f'{self._path.name} does not exists or has no metadata. Defaulting to now().')
        return datetime.now()
    
    def extend(self, packages):
        '''
            Add packages to the environment. (This does not install them)

            Parameters
            ----------
            packages: [str]
                an iterable containing the different packages, preferably in a "<name>==<version>" format 
        '''
        self._packages = self._packages.union(packages)

    def remove(self):
        '''
            Remove the backup file associated with this environment, if it exists. 
        '''
        if not self._path.is_file():
            logger.error('Trying to remove a PythonEnvironment that has no filename/is not saved.')
        else:
            os.remove(self._path)

    def save(self):
        '''
            Save the backup file associated with this environment, if it does not exists. 
        '''
        if self._path.is_file():
            logger.error('Trying to save a PythonEnvironment that was already saved. They should not be modified.')
        else:
            with open(self._path, 'w') as f:
                header = [f'# executable: {sys.executable}', f'# version: {sys.version}', '']
                f.writelines(map(lambda p : p + '\n', header + list(self._packages)))
    
    @staticmethod
    def _from_stream(stream, filename=None):
        env = PythonEnvironment(filename=filename)
        with stream as s:
            lines = map(lambda l : l.decode().strip(), s.readlines())
            packages = filter(lambda l : l and l != '' and not l.startswith('#'), lines)
            env.extend(packages)
        return env

    @staticmethod
    def from_file(filename):
        '''
            Loads a PythonEnvironment from a text file in a pip recognized format 

            Parameters
            ----------
            filename: str
                A Path to the file to load

            Returns
            -------
            PythonEnvironment: 
                the PythonEnvironment representation of the file 
                represented by `filename`
        '''
        return PythonEnvironment._from_stream(open(filename, 'rb'), filename=filename)

    @staticmethod
    def from_freeze():
        '''
            Loads a PythonEnvironment by performing a pip freeze 

            Returns
            -------
            PythonEnvironment: 
                the PythonEnvironment representation of all installed
                packages in the current environment
        '''
        pip = subprocess.Popen([sys.executable, '-m', 'pip', 'freeze'], stdout=subprocess.PIPE)
        return PythonEnvironment._from_stream(pip.stdout)

