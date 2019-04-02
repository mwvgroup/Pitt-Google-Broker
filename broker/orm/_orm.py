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


class ZTFAlerts(_base):
    """Alerts from ZTF"""

    __tablename__ = 'ztf_alerts'

    objectId = Column(types.Integer, nullable=False)
    candid = Column(types.Integer, nullable=False)
    schemavsn = Column(types.Text, nullable=False)
    publisher = Column(types.Text, nullable=False)


class ZTFCandidate(_base):
    """Candidates identified by ZTF"""

    __tablename__ = 'ztf_candidate'

    # Meta data
    id = Column(types.Integer, primary_key=True)
    jd = Column(types.Float, nullable=False)
    fid = Column(types.Integer, nullable=False)
    pid = Column(types.Integer, nullable=False)
    diffmaglim = Column(types.Float)
    pdiffimfilename = Column(types.Text)
    programpi = Column(types.Text)
    programid = Column(types.Integer, nullable=False)
    candid = Column(types.Integer, nullable=False)
    isdiffpos = Column(types.Text, nullable=False)
    tblid = Column(types.Integer)
    nid = Column(types.Integer)
    rcid = Column(types.Integer)
    field = Column(types.Integer)
    xpos = Column(types.Float)
    ypos = Column(types.Float)
    ra = Column(types.Float, nullable=False)
    dec = Column(types.Float, nullable=False)
    magpsf = Column(types.Float, nullable=False)
    sigmapsf = Column(types.Float, nullable=False)
    chipsf = Column(types.Float)
    magap = Column(types.Float)
    sigmagap = Column(types.Float)
    distnr = Column(types.Float)
    magnr = Column(types.Float)
    sigmagnr = Column(types.Float)
    chinr = Column(types.Float)
    sharpnr = Column(types.Float)
    sky = Column(types.Float)
    magdiff = Column(types.Float)
    fwhm = Column(types.Float)
    classtar = Column(types.Float)
    mindtoedge = Column(types.Float)
    magfromlim = Column(types.Float)
    seeratio = Column(types.Float)
    aimage = Column(types.Float)
    bimage = Column(types.Float)
    aimagerat = Column(types.Float)
    bimagerat = Column(types.Float)
    elong = Column(types.Float)
    nneg = Column(types.Integer)
    nbad = Column(types.Integer)
    rb = Column(types.Float)
    rbversion = Column(types.Text, nullable=False)
    ssdistnr = Column(types.Float)
    ssmagnr = Column(types.Float)
    ssnamenr = Column(types.Text)
    sumrat = Column(types.Float)
    magapbig = Column(types.Float)
    sigmagapbig = Column(types.Float)
    ranr = Column(types.Float, nullable=False)
    decnr = Column(types.Float, nullable=False)
    ndethist = Column(types.Integer, nullable=False)
    ncovhist = Column(types.Integer, nullable=False)
    jdstarthist = Column(types.Float)
    jdendhist = Column(types.Float)
    scorr = Column(types.Float)
    tooflag = Column(types.Integer)
    objectidps1 = Column(types.Integer)
    sgmag1 = Column(types.Float)
    srmag1 = Column(types.Float)
    simag1 = Column(types.Float)
    szmag1 = Column(types.Float)
    sgscore1 = Column(types.Float)
    distpsnr1 = Column(types.Float)
    objectidps2 = Column(types.Integer)
    sgmag2 = Column(types.Float)
    srmag2 = Column(types.Float)
    simag2 = Column(types.Float)
    szmag2 = Column(types.Float)
    sgscore2 = Column(types.Float)
    distpsnr2 = Column(types.Float)
    objectidps3 = Column(types.Integer)
    sgmag3 = Column(types.Float)
    srmag3 = Column(types.Float)
    simag3 = Column(types.Float)
    szmag3 = Column(types.Float)
    sgscore3 = Column(types.Float)
    distpsnr3 = Column(types.Float)
    nmtchps = Column(types.Integer, nullable=False)
    rfid = Column(types.Integer, nullable=False)
    jdstartref = Column(types.Float, nullable=False)
    jdendref = Column(types.Float, nullable=False)
    nframesref = Column(types.Integer, nullable=False)
    dsnrms = Column(types.Float)
    ssnrms = Column(types.Float)
    dsdiff = Column(types.Float)
    magzpsci = Column(types.Float)
    magzpsciunc = Column(types.Float)
    magzpscirms = Column(types.Float)
    nmatches = Column(types.Integer, nullable=False)
    clrcoeff = Column(types.Float)
    clrcounc = Column(types.Float)
    zpclrcov = Column(types.Float)
    zpmed = Column(types.Float)
    clrmed = Column(types.Float)
    clrrms = Column(types.Float)
    neargaia = Column(types.Float)
    neargaiabright = Column(types.Float)
    maggaia = Column(types.Float)
    maggaiabright = Column(types.Float)
    exptime = Column(types.Float)


def __repr__(self):
    return f'<{self.__tablename__}(id={self.id})>'


# Create database if it does not already exist and create connection
session = sessionmaker(bind=engine, autocommit=False)()
_base.metadata.create_all(engine)
