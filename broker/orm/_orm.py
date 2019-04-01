#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module provides an object relational mapper (ORM) for the broker
backend.

Included tables:
    SDSS: Object catalogue for SDSS
"""

import os
from warnings import warn

from sqlalchemy import Column, create_engine, types
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

_base = declarative_base()
_db_url = 'postgres://localhost/pitt_broker'
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

    db_path = os.path.abspath(path)
    dump_engine = create_engine(f'sqlite:///{db_path}')
    dump_session = sessionmaker(bind=dump_engine, autocommit=False)()
    _base.metadata.create_all(dump_engine)

    for tbl_name, tbl in _base.metadata.tables.items():
        data = engine.execute(tbl.select()).fetchall()
        if data:
            dump_engine.execute(tbl.insert(), data)

    dump_session.commit()


def insert_from_sqlite(path):
    """Insert entries in the project database from an exported sqlite file

    Args:
        path (str): Path of a sqlite backup
    """

    db_path = os.path.abspath(path)
    load_engine = create_engine(f'sqlite:///{db_path}')
    backup_base = automap_base()
    backup_base.prepare(engine, reflect=True)
    backup_tables = backup_base.metadata.tables

    db_tables = _base.metadata.tables
    if db_tables != backup_tables:
        warn('Database models do not match exactly. Proceeding anyways')

    for tbl_name, tbl in backup_tables.items():
        data = load_engine.execute(tbl.select()).fetchall()
        if data:
            engine.execute(db_tables[tbl_name].insert(), data)

    session.commit()


def upsert(table, values, index, conflict='ignore', skip_cols=()):
    """Execute a bulk UPSERT statement

    Args:
        table (DeclarativeMeta): The ORM table to act on (eg. Supernova)
        values     (list[dict]): Data to upsert
        index    (list[Column]): Table column on which to catch conflicts
        conflict          (str): Either 'ignore' or 'update (Default: 'ignore')
        skip_cols (list[str]): List of columns not to update
    """

    insert_stmt = postgresql.insert(table.__table__).values(values)

    if conflict == 'ignore':
        ignore_stmt = insert_stmt.on_conflict_do_nothing(index_elements=index)
        engine.execute(ignore_stmt)

    elif conflict == 'update':
        update_columns = {col.name: col for col in insert_stmt.excluded if
                          col.name not in skip_cols}

        update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=index,
            set_=update_columns)

        engine.execute(update_stmt)

    else:
        raise ValueError(f'Unknown action: {conflict}')


class SDSS(_base):
    """Objects from the SDSS catalogue"""

    __tablename__ = 'sdss'

    # Meta data
    objid = Column(types.BigInteger, primary_key=True)
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
