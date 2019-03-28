#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module provides object relational mapper (ORM)

Included tables:
    SDSS: Object catalogue for SDSS
"""

from os import path
from warnings import warn

from sqlalchemy import Column, create_engine, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

_db_path = path.join(path.dirname(path.abspath(__file__)), 'broker.db')
_db_url = f'sqlite:///{_db_path}'

_base = declarative_base()
engine = create_engine(_db_url)
if not database_exists(engine.url):
    warn(f'No existing database found. Creating {_db_url}')
    create_database(engine.url)


def backup_to_sqlite(out_path):
    """Create a copy of the current database and write it to a sqlite file

    Args:
        path (str): Path of the output database file
    """

    if path.exists(path):
        raise FileExistsError(f'File already exists: {out_path}')

    dump_engine = create_engine(f'sqlite:///{out_path}')
    dump_session = sessionmaker(bind=dump_engine, autocommit=False)()
    _base.metadata.create_all(dump_engine)

    for tbl_name, tbl in _base.metadata.tables.items():
        data = engine.execute(tbl.select()).fetchall()
        if data:
            dump_engine.execute(tbl.insert(), data)

    dump_session.commit()


class SDSS(_base):
    """Objects from the SDSS catalogue"""

    __tablename__ = 'sdss'

    # Meta data
    id = Column(types.Integer, primary_key=True)
    run = Column(types.Integer)
    rerun = Column(types.Integer)
    ra = Column(types.Float)
    dec = Column(types.Float)
    u = Column(types.Float)
    g = Column(types.Float)
    r = Column(types.Float)
    i = Column(types.Float)
    z = Column(types.Float)
    u_err = Column(types.Float)
    g_err = Column(types.Float)
    r_err = Column(types.Float)
    i_err = Column(types.Float)
    z_err = Column(types.Float)


def __repr__(self):
    return f'<{self.__tablename__}(id={self.id})>'


# Create database if it does not already exist and create connection
session = sessionmaker(bind=engine, autocommit=False)()
_base.metadata.create_all(engine)
