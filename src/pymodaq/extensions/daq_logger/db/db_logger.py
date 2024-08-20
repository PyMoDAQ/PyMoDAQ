from contextlib import contextmanager
import logging
import datetime
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import Config

from pymodaq_gui.h5modules.saving import dashboard_submodules_params
from pymodaq_gui.messenger import messagebox
from pymodaq_gui.managers.parameter_manager import ParameterManager

from pymodaq_data.data import DataToExport


from .db_logger_models import (Base, Data0D, Data1D, Data2D, LogInfo,
                               Configuration, ControlModule)
from ..abstract import AbstractLogger


logger = set_logger(get_module_name(__file__))
config = Config()


class DBLogHandler(logging.StreamHandler):
    def __init__(self, dblogger):
        super().__init__()
        self.dblogger = dblogger
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        self.dblogger.add_log(msg)


class DbLogger:
    user = config('network', 'logging', 'user', 'username')
    user_pwd = config('network', 'logging', 'user', 'pwd')

    def __init__(self, database_name, ip_address=config('network', 'logging', 'sql', 'ip'),
                 port=config('network', 'logging', 'sql', 'port'), save2D=False):
        """

        Parameters
        ----------
        models_base
        ip_address
        port
        database_name
        """

        self.ip_address = ip_address
        self.port = port
        self.database_name = database_name

        self.engine = None
        self.Session = None
        self._save2D = save2D

    @property
    def save2D(self):
        return self._save2D

    @save2D.setter
    def save2D(self, value):
        self._save2D = value

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(str(e))
            session.rollback()
        finally:
            session.close()

    def connect_db(self):
        url = f"postgresql://{self.user}:{self.user_pwd}@{self.ip_address}:"\
              f"{self.port}/{self.database_name}"
        logger.debug(f'Connecting database using: {url}')
        try:
            self.engine = create_engine(f"postgresql://{self.user}:{self.user_pwd}@{self.ip_address}:"
                                        f"{self.port}/{self.database_name}")
        except ModuleNotFoundError as e:
            messagebox('warning', 'ModuleError',
                       f'The postgresql backend *psycopg2* has not been installed.\n'
                       f'Could not connect to your database')
            logger.warning(str(e))
            return False

        try:
            if not database_exists(self.engine.url):
                create_database(self.engine.url)
            assert database_exists(self.engine.url)
        except Exception as e:
            logger.critical(f'Impossible to connect to the DB: {str(e)}')
            return False

        self.create_table()
        self.Session = sessionmaker(bind=self.engine)
        logger.debug(f'Database Connected')
        return True

    def close(self):
        if self.engine is not None:
            self.engine.dispose()

    def create_table(self):
        # create tables if not existing
        if self.engine is not None:
            Base.metadata.create_all(self.engine)

    def get_detectors(self, session) -> List[str]:
        """Returns the list of detectors name

        Parameters
        ----------
        session: (Session) SQLAlchemy session instance for db transactions

        Returns
        -------
        the list of all created detectors
        """
        return [res[0] for res in session.query(ControlModule.name)]

    def get_actuators(self, session) -> List[str]:
        """Returns the list of actuators name

        Parameters
        ----------
        session: (Session) SQLAlchemy session instance for db transactions

        Returns
        -------
        the list of all created actuators
        """
        return [res[0] for res in session.query(ControlModule.name)]

    def add_detectors(self, detectors):
        """
        add detectors in the detectors table
        Parameters
        ----------
        detectors: (list) list of dict with keys: name and settings_xml
        """
        self.add_control_modules(detectors, 'DAQ_Viewer')

    def add_actuators(self, actuators):
        """
        add actuators in the actuators table
        Parameters
        ----------
        actuators: list
            list of dict with keys: name and settings_xml
        """
        self.add_control_modules(actuators, 'DAQ_Move')

    def add_control_modules(self, modules, module_type='DAQ_Viewer'):
        if not isinstance(modules, list):
            modules = [modules]
        with self.session_scope() as session:
            existing_modules = [d.name for d in session.query(ControlModule)]
            for mod in modules:
                if mod['name'] not in existing_modules:
                    session.add(ControlModule(name=mod['name'], module_type=module_type,
                                              settings_xml=mod['xml_settings']))

    def add_config(self, config_settings):
        with self.session_scope() as session:
            session.add(Configuration(timestamp=datetime.datetime.now().timestamp(), settings_xml=config_settings))

    def add_log(self, log):
        with self.session_scope() as session:
            session.add(LogInfo(log))

    def add_data(self, data: DataToExport):
        with self.session_scope() as session:
            time_stamp = data.timestamp
            module_name = data.name

            if session.query(ControlModule).filter_by(name=module_name).count() == 0:
                self.add_control_modules(session, dict(name=module_name), data.control_module)

            module_id = session.query(ControlModule).filter_by(name=module_name).one().id  # detector/actuator names should/are unique

            for dwa in data.get_data_from_dim('Data0D'):
                for ind, data_array in enumerate(dwa):
                    session.add(Data0D(timestamp=dwa.timestamp, control_module_id=module_id, channel=dwa.labels[ind],
                                       value=float(data_array[0])))

            for dwa in data.get_data_from_dim('Data1D'):
                for ind, data_array in enumerate(dwa):
                    session.add(Data1D(timestamp=dwa.timestamp, control_module_id=module_id,
                                       channel=dwa.labels[ind],
                                       value=data_array.tolist()))
            if self.save2D:
                for dwa in data.get_data_from_dim('Data2D'):
                    for ind, data_array in enumerate(dwa):
                        session.add(Data2D(timestamp=dwa.timestamp, control_module_id=module_id,
                                           channel=dwa.labels[ind],
                                           value=data_array.tolist()))

            # not yet dataND as db should not know where to save these datas


class DbLoggerGUI(DbLogger, ParameterManager):
    params = [
        {'title': 'Database:', 'name': 'database_type', 'type': 'list', 'value': 'PostgreSQL',
            'limits': ['PostgreSQL', ]},
        {'title': 'Server IP:', 'name': 'server_ip', 'type': 'str',
            'value': config('network', 'logging', 'sql', 'ip'),
         'tip':'Either localhost if the database server is on the same computer or the IP address of the server'},
        {'title': 'Server port:', 'name': 'server_port', 'type': 'int',
            'value': config('network', 'logging', 'sql', 'port')},
        {'title': 'Connect:', 'name': 'connect_db', 'type': 'bool_push', 'value': False},
        {'title': 'Connected:', 'name': 'connected_db', 'type': 'led', 'value': False},
    ] + dashboard_submodules_params

    def __init__(self, database_name):
        DbLogger.__init__(self, database_name, ip_address=config('network', 'logging', 'sql', 'ip'),
                          port=config('network', 'logging', 'sql', 'port'), save2D=False)
        ParameterManager.__init__(self)

        self.settings.child('do_save').hide()

    def value_changed(self, param):
        if param.name() == 'server_ip':
            self.ip_address = param.value()

        elif param.name() == 'server_port':
            self.port = param.value()

        elif param.name() == 'connect_db':
            if param.value():
                status = self.connect_db()
                self.settings.child('connected_db').setValue(status)
            else:
                self.close()
                self.settings.child('connected_db').setValue(False)

        elif param.name() == 'save_2D':
            self.save2D = param.value()


class DataBaseLogger(AbstractLogger):
    def __init__(self, database_name):
        self.dblogger = DbLoggerGUI(database_name)

    @property
    def settings_tree(self):
        return self.dblogger.settings_tree

    @property
    def settings(self):
        return self.dblogger.settings

    def init_logger(self, settings):
        if not self.settings.child('connected_db').value():
            status = self.dblogger.connect_db()
            if not status:
                logger.critical('the Database is not and cannot be connnect')
                return False

        self.dblogger.add_config(settings)
        return True

    def get_handler(self):
        return DBLogHandler(self.dblogger)

    def add_detector(self, det_name, settings):
        self.dblogger.add_detectors([dict(name=det_name, xml_settings=settings)])

    def add_actuator(self, act_name, settings):
        self.dblogger.add_actuators([dict(name=act_name, xml_settings=settings)])

    def add_data(self, data):
        self.dblogger.add_data(data)
        self.settings.child('N_saved').setValue(
            self.settings.child('N_saved').value() + 1)

    def stop_logger(self):
        pass

    def close(self):
        pass


if __name__ == '__main__':
    db = DbLogger('preset_default')
    db.connect_db()
    pass