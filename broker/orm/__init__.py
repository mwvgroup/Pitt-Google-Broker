#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module provides an object relational mapper (ORM) for the broker
backend.

Examples:

    To query the entire SDSS table:

    >>> from broker.orm import session, SDSS
    >>> session.query(SDSS).all()

    To backup data to a local SQLite file:

    >>>  from broker.orm import backup_to_sqlite
    >>>  backup_to_sqlite('./backup.db')

    To restore from a backup (via INSERT):

    >>>  from broker.orm import insert_from_sqlite
    >>>  insert_from_sqlite('./backup.db')

"""

from ._ingest_catalogs import populate_backend
from ._orm import \
    SDSS, backup_to_sqlite, engine, insert_from_sqlite, session, upsert
