#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module provides object relational mapper (ORM)

Included tables:
    SDSS: Object catalogue for SDSS
"""

import os
from warnings import warn

from sqlalchemy import Column, create_engine, types
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')
_db_url = f'sqlite:///{_db_path}'

_base = declarative_base()
engine = create_engine(_db_url)
if not database_exists(engine.url):
    warn(f'No existing database found. Creating {_db_url}')
    create_database(engine.url)


def backup_to_sqlite(path):
    """Create a copy of the current database and write it to a sqlite file

    Args:
        path (str): Path of the output database file
    """

    if os.path.exists(path):
        raise FileExistsError(f'File already exists: {path}')

    db_path = os.path.abspath(path).lstrip('/')
    dump_engine = create_engine(f'sqlite:///{db_path}')
    dump_session = sessionmaker(bind=dump_engine, autocommit=False)()
    _base.metadata.create_all(dump_engine)

    for tbl_name, tbl in _base.metadata.tables.items():
        data = engine.execute(tbl.select()).fetchall()
        if data:
            dump_engine.execute(tbl.insert(), data)

    dump_session.commit()


def restore_from_sqlite(path, force=False):
    """Insert entries in the project database from an exported sqlite file

    Args:
        path   (str): Path of a sqlite backup
        force (bool): Attempt update even if db models match (default = False)
    """

    db_path = os.path.abspath(path).lstrip('/')
    load_engine = create_engine(f'sqlite:///{db_path}')
    backup_base = automap_base()
    backup_base.prepare(engine, reflect=True)
    backup_tables = backup_base.metadata.tables

    db_tables = _base.metadata.tables
    if not (force or db_tables == backup_tables):
        raise RuntimeError('Cannot auto update. Database models do not match.')

    for tbl_name, tbl in backup_tables.items():
        data = load_engine.execute(tbl.select()).fetchall()
        if data:
            engine.execute(db_tables[tbl_name].insert(), data)

    session.commit()


class SDSS(_base):
    """Objects from the SDSS catalogue"""

    __tablename__ = 'sdss'

    # Meta data
    id = Column(types.INTEGER, primary_key=True)
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
