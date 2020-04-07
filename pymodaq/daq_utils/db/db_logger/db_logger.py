import os
import numpy as np
from contextlib import contextmanager
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY as Array
from sqlalchemy_utils import database_exists, create_database
from .db_logger_models import Base, Data0D, Data1D, Data2D, LogInfo, Detector

from pymodaq.daq_utils.daq_utils import get_set_local_dir

if __name__ == '__main__':
    import logging
    import datetime
    now = datetime.datetime.now()
    local_path = get_set_local_dir()
    log_path = os.path.join(local_path, 'logging')
    if not os.path.isdir(log_path):
        os.makedirs(log_path)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(filename=os.path.join(log_path, 'db_logger_{}.log'.format(now.strftime('%Y%m%d_%H_%M_%S'))),
                        level=logging.DEBUG)





class DbLogger:
    user = 'pymodaq_user'
    user_pwd = 'pymodaq'

    def __init__(self, database_name, ip_address='localhost', port=5432, save2D=False, logging=None):
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
        self._save2D

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

            session.rollback()
        finally:
            session.close()

    def connect_db(self):
        engine = create_engine(f"postgresql://{self.user}:{self.user_pwd}@{self.ip_address}:"
                               f"{self.port}/{self.database_name}")
        if not database_exists(engine.url):
            create_database(engine.url)

        assert database_exists(engine.url)
        self.create_table()
        self.Session = sessionmaker(bind=engine)

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

    def add_detectors(self, session, detectors):
        """
        add detectors in the detectors table
        Parameters
        ----------
        session: (Session) SQLAlchemy session instance for db transactions
        detectors: (list) list of dict with keys: name and settings_xml
        """
        if not isinstance(detectors, list):
            detectors = [detectors]
        for det in detectors:
            session.add(Detector(name=det['name'], settings_xml=det['settings_xml']))

    def add_datas(self, datas):
        with self.session_scope() as session:
            time_stamp = datas['acq_time_s']
            detector_name = datas['name']
            if session.query(Detector).filter_by(name=detector_name).count() == 0:
                #security detector adding in case it hasn't been done previously (and properly)
                self.add_detectors(session, dict(name=detector_name))

            det_id = session.query(Detector).filter_by(name=detector_name).one().id  #detector names should/are unique

            if 'data0D' in datas:
                for channel in datas['data0D']:
                    session.add(Data0D(time_stamp=time_stamp, detector_id=det_id, channel=channel,
                                       value=datas['data0D'][channel]['data'][0]))

            if 'data1D' in datas:
                for channel in datas['data1D']:
                    session.add(Data1D(time_stamp=time_stamp, detector_id=det_id, channel=channel,
                                       value=datas['data1D'][channel]['data'].tolist()))

            if 'data2D' in datas and self.save2D:
                for channel in datas['data2D']:
                    session.add(Data2D(time_stamp=time_stamp, detector_id=det_id, channel=channel,
                                       value=datas['data1D'][channel]['data'].tolist()))

            #not yet dataND as db should not be where to save these datas


