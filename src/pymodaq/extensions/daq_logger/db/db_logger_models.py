import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY as Array


Base = declarative_base()


class Configuration(Base):
    __tablename__ = 'configurations'
    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, nullable=False, index=True)
    settings_xml = Column(String)

    def __repr__(self):
        return f"<Config(date='{datetime.datetime.fromtimestamp(self.timestamp).isoformat()}', settings_xml='{self.settings_xml[0:20]}')>"

# class Actuator(Base):
#     __tablename__ = 'actuators'
#     id = Column(Integer, primary_key=True)
#     name = Column(String(128))
#     settings_xml = Column(String)
#     datas0D = relationship("Data0D", backref='actuators')
#
#
# class Detector(Base):
#     __tablename__ = 'detectors'
#     id = Column(Integer, primary_key=True)
#     name = Column(String(128))
#     settings_xml = Column(String)
#     datas0D = relationship("Data0D", backref='detectors')
#     datas1D = relationship("Data1D", backref='detectors')
#     datas2D = relationship("Data2D", backref='detectors')
#
#     def __repr__(self):
#         return f"<Detector(name='{self.name}', settings_xml='{self.settings_xml[0:20]}')>"


class ControlModule(Base):
    __tablename__ = 'control_modules'
    id = Column(Integer, primary_key=True)
    name = Column(String(128))
    module_type = Column(String(128))
    settings_xml = Column(String)
    datas0D = relationship("Data0D", backref='control_modules')
    datas1D = relationship("Data1D", backref='control_modules')
    datas2D = relationship("Data2D", backref='control_modules')

    def __repr__(self):
        return f"<Control Module {self.type} (name='{self.name}', settings_xml='{self.settings_xml[0:20]}')>"


class LogInfo(Base):
    __tablename__ = 'loginfo'
    id = Column(Integer, primary_key=True)
    value = Column(String)

    def __repr__(self):
        return f"<Loginfo(timestamp='{self.timestamp}', value='{self.value}')>"


class Data0D(Base):
    __tablename__ = 'datas0D'

    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, nullable=False, index=True)
    control_module_id = Column(Integer, ForeignKey('control_modules.id'), index=True)
    channel = Column(String(128))
    value = Column(Float)

    def __repr__(self):
        return f"<Data0D(channel='{self.channel}', timestamp='{self.timestamp}', value='{self.value}')>"


class Data1D(Base):
    __tablename__ = 'datas1D'

    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, nullable=False, index=True)
    control_module_id = Column(Integer, ForeignKey('control_modules.id'), index=True)
    channel = Column(String(128))
    value = Column(Array(Float, dimensions=1))

    def __repr__(self):
        return f"<Data1D(channel='{self.channel}', timestamp='{self.timestamp}', value='{self.value}')>"


class Data2D(Base):
    __tablename__ = 'datas2D'

    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, nullable=False, index=True)
    control_module_id = Column(Integer, ForeignKey('control_modules.id'), index=True)
    channel = Column(String(128))
    value = Column(Array(Float, dimensions=2))

    def __repr__(self):
        return f"<Data2D(channel='{self.channel}', timestamp='{self.timestamp}', value='{self.value}')>"
