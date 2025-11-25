# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import logging
import warnings
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from pymodaq_utils.config import get_set_config_dir, Config

config = Config()


def set_logger(logger_name, add_handler=False, base_logger=False, add_to_console=False, log_level=None,
               logger_base_name='pymodaq') -> logging.Logger:
    """defines a logger of a given name and eventually add an handler to it

    Parameters
    ----------
    logger_name: (str) the name of the logger (usually it is the module name as returned by get_module_name
    add_handler (bool) if True adds a TimedRotatingFileHandler to the logger instance (should be True if logger set from
                main app
    base_logger: (bool) specify if this is the parent logger (usually where one defines the handler)

    Returns
    -------
    logger: (logging.Logger) logger instance
    See Also
    --------
    get_module_name, logging.handlers.TimedRotatingFileHandler
    """
    if not base_logger:
        logger_name = f'{logger_base_name}.{logger_name}'

    logger = logging.getLogger(logger_name)

    if log_level is None:
        log_level = config('general', 'debug_level')
    logger.setLevel(log_level)
    if add_handler:
        try:
            log_path = get_set_config_dir('log', user=True)
            log_file_path = log_path.joinpath(f'{logger_base_name}.log')
            if not (log_file_path.exists() and log_file_path.is_file()):
                log_file_path.touch(mode=0o777)
            handler = TimedRotatingFileHandler(log_file_path, when='midnight')
        except Exception as e:
            print(e)
            print(f"Could not set up logger at {log_file_path}. Probably because of missing rights.")
            print("Falling back to console logging.")
            handler = logging.StreamHandler()

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logging.captureWarnings(True)
        # only catch DeprecationWarning in DEBUG level
        if log_level == 'DEBUG':
            warnings.filterwarnings('default', category=DeprecationWarning)
        else:
            warnings.filterwarnings('ignore', category=DeprecationWarning)
        warnings_logger = logging.getLogger("py.warnings")
        warnings_logger.addHandler(handler)

    if add_to_console:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger


def get_base_logger(logger: logging.Logger) -> logging.Logger:
    while logger.name != 'pymodaq':
        logger = logger.parent
    return logger


def get_module_name(module__file__path):
    """from the full path of a module extract its name"""
    path = Path(module__file__path)
    return path.stem

