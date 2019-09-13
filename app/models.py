from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, SmallInteger, String, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

ROLE_USER = 0
ROLE_ADMIN = 1

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key = True)
    username = Column(String(50), unique = True)
    password = Column(String(255))
    role = Column(SmallInteger, default = ROLE_ADMIN)
    email = Column(String(190), unique = True)

    def __repr__(self):
        return '<User (id=%r, username=%s)>' % (self.id, self.username)

class Rc(Base):
    __tablename__ = 'rc'

    id = Column(Integer, primary_key = True)
    name = Column(String(50))
    public = Column(Boolean)
    order = Column(Integer)
    icon = Column(String(200))
    timestamp = Column(DateTime)
    buttons = relationship('Button', backref = 'rc', lazy = 'dynamic')

    def __repr__(self):
        return '<Rc (id=%r, name=%s)>' % (self.id, self.name)

class Button(Base):
    __tablename__ = 'button'

    id = Column(Integer, primary_key = True)
    rc_id = Column(Integer, ForeignKey('rc.id'))
    radio_id = Column(Integer)
    name = Column(String(50))
    order_hor = Column(Integer)
    order_ver = Column(Integer)
    color = Column(String(10))
    # radio / mqtt
    type = Column(String(20))
    message = Column(Text)
    timestamp = Column(DateTime)

    def __repr__(self):
        return '<Button (id=%r, name=%s)>' % (self.id, self.name)

class Node(Base):
    __tablename__ = 'node'

    id = Column(Integer, primary_key = True)
    name = Column(String(50))
    host_name = Column(String(100))
    order = Column(Integer)
    timestamp = Column(DateTime)
    arduinos = relationship('Arduino', backref = 'node', lazy = 'dynamic')

    def __repr__(self):
        return '<Node (id=%r, name=%s)>' % (self.id, self.name)

class Arduino(Base):
    __tablename__ = 'arduino'

    id = Column(Integer, primary_key = True)
    node_id = Column(Integer, ForeignKey('node.id'))
    usb = Column(String(20))
    name = Column(String(50))
    order = Column(Integer)
    timestamp = Column(DateTime)
    radios = relationship('Radio', backref = 'arduino', lazy = 'dynamic')

    def __repr__(self):
        return '<Arduino (id=%r, name=%s, usb=%s)>' % (self.id, self.name, self.usb)

class Radio(Base):
    __tablename__ = 'radio'

    id = Column(Integer, primary_key = True)
    arduino_id = Column(Integer, ForeignKey('arduino.id'))
    pipe = Column(String(12))
    # broadcast / unicast
    type = Column(String(20))
    name = Column(String(50))
    enabled = Column(Boolean(True))
    order = Column(Integer)
    on_request = Column(Boolean(False))
    expired_after = Column(Integer)
    timestamp = Column(DateTime)

    def __repr__(self):
        return '<Radio (id=%r, name=%s)>' % (self.id, self.name)

class Mqtt(Base):
    __tablename__ = 'mqtt'

    id = Column(Integer, primary_key = True)
    name = Column(String(50))
    client_name = Column(String(200))
    order = Column(Integer)
    enabled = Column(Boolean(True))
    timestamp = Column(DateTime)

    def __repr__(self):
        return '<Mqtt (id=%r, name=%s)>' % (self.id, self.name)
