# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import logging
import warnings
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from pymodaq.utils.config import get_set_config_path, Config

config = Config()


def set_logger(logger_name, add_handler=False, base_logger=False, add_to_console=False, log_level=None,
               logger_base_name='pymodaq', local_dir=None):
    """defines a logger of a given name and eventually add an handler to it

    Parameters
    ----------
    logger_name: (str) the name of the logger (usually it is the module name as returned by get_module_name
    add_handler (bool) if True adds a TimedRotatingFileHandler to the logger instance (should be True if logger set from
                main app
    base_logger: (bool) specify if this is the parent logger (usually where one defines the handler)

    Returns
    -------
    logger: (logging.logger) logger instance
    See Also
    --------
    get_module_name, logging.handlers.TimedRotatingFileHandler
    """
    if not base_logger:
        logger_name = f'{logger_base_name}.{logger_name}'

    logger = logging.getLogger(logger_name)
    log_path = get_set_config_path('log', local_dir=local_dir)
    if add_handler:
        if log_level is None:
            log_level = config('general', 'debug_level')
        logger.setLevel(log_level)
        handler = TimedRotatingFileHandler(log_path.joinpath(f'{logger_base_name}.log'), when='midnight')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logging.captureWarnings(True)
        warnings.filterwarnings('default', category=DeprecationWarning)
        warnings_logger = logging.getLogger("py.warnings")
        warnings_logger.addHandler(handler)

    if add_to_console:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger


def get_module_name(module__file__path):
    """from the full path of a module extract its name"""
    path = Path(module__file__path)
    return path.stem
