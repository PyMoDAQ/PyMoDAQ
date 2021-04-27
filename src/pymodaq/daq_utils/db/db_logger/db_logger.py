import logging
import datetime
from PyQt5 import QtCore
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
from .db_logger_models import Base, Data0D, Data1D, Data2D, LogInfo, Detector, Configuration
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.gui_utils import dashboard_submodules_params
from pyqtgraph.parametertree import Parameter, ParameterTree

logger = utils.set_logger(utils.get_module_name(__file__))
config = utils.load_config()


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
    user = config['network']['logging']['user']['username']
    user_pwd = config['network']['logging']['user']['pwd']

    def __init__(self, database_name, ip_address=config['network']['logging']['sql']['ip'],
                 port=config['network']['logging']['sql']['port'], save2D=False):
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
        self.engine = create_engine(f"postgresql://{self.user}:{self.user_pwd}@{self.ip_address}:"
                                    f"{self.port}/{self.database_name}")
        try:
            if not database_exists(self.engine.url):
                create_database(self.engine.url)
            assert database_exists(self.engine.url)
        except Exception as e:
            logger.critical(f'Impossible to connect to the DB: {str(e)}')
            return False

        self.create_table()
        self.Session = sessionmaker(bind=self.engine)
        return True

    def close(self):
        if self.engine is not None:
            self.engine.dispose()

    def create_table(self):
        # create tables if not existing
        if self.engine is not None:
            Base.metadata.create_all(self.engine)

    def get_detectors(self, session):
        """Returns the list of detectors name

        Parameters
        ----------
        session: (Session) SQLAlchemy session instance for db transactions

        Returns
        -------
        list of str
        """
        return [res[0] for res in session.query(Detector.name)]

    def add_detectors(self, detectors):
        """
        add detectors in the detectors table
        Parameters
        ----------
        session: (Session) SQLAlchemy session instance for db transactions
        detectors: (list) list of dict with keys: name and settings_xml
        """
        if not isinstance(detectors, list):
            detectors = [detectors]
        with self.session_scope() as session:
            existing_detectors = [d.name for d in session.query(Detector)]
            for det in detectors:
                if det['name'] not in existing_detectors:
                    session.add(Detector(name=det['name'], settings_xml=det['xml_settings']))

    def add_config(self, config_settings):
        with self.session_scope() as session:
            session.add(Configuration(timestamp=datetime.datetime.now().timestamp(), settings_xml=config_settings))

    def add_log(self, log):
        with self.session_scope() as session:
            session.add(LogInfo(log))

    def add_datas(self, datas):
        with self.session_scope() as session:
            time_stamp = datas['acq_time_s']
            detector_name = datas['name']
            if session.query(Detector).filter_by(name=detector_name).count() == 0:
                # security detector adding in case it hasn't been done previously (and properly)
                self.add_detectors(session, dict(name=detector_name))

            det_id = session.query(Detector).filter_by(name=detector_name).one().id  # detector names should/are unique

            if 'data0D' in datas:
                for channel in datas['data0D']:
                    session.add(Data0D(timestamp=time_stamp, detector_id=det_id,
                                       channel=f"{datas['data0D'][channel]['name']}:{channel}",
                                       value=datas['data0D'][channel]['data']))

            if 'data1D' in datas:
                for channel in datas['data1D']:
                    session.add(Data1D(timestamp=time_stamp, detector_id=det_id,
                                       channel=f"{datas['data1D'][channel]['name']}:{channel}",
                                       value=datas['data1D'][channel]['data'].tolist()))

            if 'data2D' in datas and self.save2D:
                for channel in datas['data2D']:
                    session.add(Data2D(timestamp=time_stamp, detector_id=det_id,
                                       channel=f"{datas['data2D'][channel]['name']}:{channel}",
                                       value=datas['data2D'][channel]['data'].tolist()))

            # not yet dataND as db should not know where to save these datas


class DbLoggerGUI(DbLogger, QtCore.QObject):
    params = [
        {'title': 'Database:', 'name': 'database_type', 'type': 'list', 'value': 'PostgreSQL',
            'values': ['PostgreSQL', ]},
        {'title': 'Server IP:', 'name': 'server_ip', 'type': 'str',
            'value': config['network']['logging']['sql']['ip']},
        {'title': 'Server port:', 'name': 'server_port', 'type': 'int',
            'value': config['network']['logging']['sql']['port']},
        {'title': 'Connect:', 'name': 'connect_db', 'type': 'bool_push', 'value': False},
        {'title': 'Connected:', 'name': 'connected_db', 'type': 'led', 'value': False, 'readonly': True},
    ] + dashboard_submodules_params

    def __init__(self, database_name):
        DbLogger.__init__(self, database_name, ip_address=config['network']['logging']['sql']['ip'],
                          port=config['network']['logging']['sql']['port'], save2D=False)
        QtCore.QObject.__init__(self)

        self.settings = Parameter.create(title='DB settings', name='db_settings', type='group',
                                         children=self.params)
        self.settings.child(('do_save')).hide()
        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumHeight(310)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    def parameter_tree_changed(self, param, changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, update the DAQscan_settings tree consequently.

            =============== ============================================ ==============================
            **Parameters**    **Type**                                     **Description**
            *param*           instance of pyqtgraph parameter              the parameter to be checked
            *changes*         (parameter,change,information) tuple list    the current changes state
            =============== ============================================ ==============================
        """
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'server_ip':
                    self.ip_address = param.value()

                elif param.name() == 'server_port':
                    self.port = param.value()

                elif param.name() == 'connect_db':
                    status = self.connect_db()
                    self.settings.child(('connected_db')).setValue(status)

                elif param.name() == 'save_2D':
                    self.save2D = param.value()

            elif change == 'parent':
                pass
