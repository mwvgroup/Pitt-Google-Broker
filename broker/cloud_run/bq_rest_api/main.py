"""
GCP REST API
============

A REST interface for querying data from Big Query.

Big Query already provides its own
`REST API <https://cloud.google.com/bigquery/docs/reference/rest/>`_,
but the interface isn't flexible enough for our needs.
This API provides a simpler, read-only interface for table data.

Source Documentation
--------------------

.. automodule:: pgb_utils.pgb_utils.figures
   :members:
"""

from __future__ import annotations

import logging
import os
from typing import Type

from flask import Flask
from flask_marshmallow import Marshmallow, Schema
from flask_restful import Api, Resource, reqparse
from sqlalchemy import Table, select, column, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import Select

LOG = logging.getLogger('mylogger')
LOG.setLevel(logging.DEBUG)

LOG.info('Initializing application constructs')
app = Flask(__name__)  # Handles running the web application
ma = Marshmallow(app)  # Handles serialization of database objects to dictionaries
api = Api(app)  # Handles definition of REST endpoints


class AutoResource:
    """A restful flask resource that automatically maps to a database schema

    Instances of this class are responsible for handling incoming GET requests.
    The generated resource is read-only and only supports GET requests.
    """

    def __new__(cls, table: Table, schema: Schema, parser: AutoRestParser, session_maker) -> Type[Resource]:
        """Return a new REST resource

        Args:
            table: The sqlalchemy table to serve data from
            schema: The schema used to serialize query data

        Returns:
            A ``flask_restful.Resource`` class
        """

        LOG.debug(f'Creating REST resource for table {table.name}')

        class GeneratedResource(Resource):
            _table = table
            _schema = schema
            _parser = parser

            def get(self):
                query = self._parser.build_query()
                with session_maker() as session:
                    result = session.execute(query).all()

                return self._schema.dump(result)

        GeneratedResource.__name__ = table.name.replace('.', '') + 'Resource'
        return GeneratedResource


class AutoSchema:
    """A Marshmallow schema that automatically reflects a given table

    Instances of this class are responsible for serializing database
    queries into a web compatible JSON format.
    """

    def __new__(cls, table: Table, *args, **kwargs) -> Schema:
        """Return a new marshmallow schema representing a given table

        Args:
            table: The sqlalchemy table to generate a schema for
            Any other arguments supported by the ``marshmallow.Schema`` class

        Returns:
            A ``marshmallow.Schema`` instance
        """

        LOG.debug(f'Mapping schema for table {table.name}')

        class GeneratedSchema(ma.Schema):
            class Meta:
                fields = tuple(c.name for c in table.columns)

        GeneratedSchema.__name__ = table.name.replace('.', '') + 'Schema'
        return GeneratedSchema(*args, **kwargs)


class AutoRestParser(reqparse.RequestParser):
    """Rest argument parser that generates argument options from a table schema

    Instances of this class are responsible for parsing REST arguments and
    converting them into SQL statements.
    """

    def __init__(self, table: Table, schema: Schema) -> None:
        """Create a new REST parser for fetching data from a SQLAlchemy table

        Args:
            table: The sqlalchemy table to generate a REST parser for
            schema: The marshmallow schema for the given table
        """

        super().__init__()
        self._table = table
        self._schema = schema

        # So we can split comma seperated REST arguments into a list
        split_columns = lambda x: x.split(',')

        LOG.debug(f'Creating REST parser for table {table.name}')
        self.add_argument('columns', type=split_columns, help='Only return results from the given columns')
        self.add_argument('limit', type=int, help='Maximum number of results to return')
        self.add_argument('orderby', type=str, choices=schema.fields, help='Name of column to sort by')
        self.add_argument('desc', type=bool, help='Sort values in descending order')

    def build_query(self) -> Select:
        """Build a database query based on an HTTP request

        Returns:
            A SQLAlchemy query object
        """

        args = self.parse_args()
        if args.columns:
            query = select(map(column, args.columns)).select_from(self._table)

        else:
            query = select(self._table)

        query = query.limit(args.limit or int(os.environ.get('MAX_ROWS', 1_000_000)))

        if args.orderby:
            order_col = getattr(self._table.columns, args.orderby)
            if args.desc:
                order_col = order_col.desc()

            query = query.order_by(order_col)

        return query


db_url = 'bigquery://' + os.environ['GOOGLE_CLOUD_PROJECT']
LOG.info(f'Connecting to {db_url}')
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

LOG.info('Mapping database schema')
Base = declarative_base(bind=engine)
Base.metadata.reflect(bind=engine)

LOG.info('Defining API endpoints')
for table_name, table_obj in Base.metadata.tables.items():
    endpoint_name = table_name.replace('.', '/')

    _schema = AutoSchema(table_obj, many=True)
    _parser = AutoRestParser(table_obj, _schema)
    _resource = AutoResource(table_obj, _schema, _parser, Session)

    LOG.debug(f'Creating endpoint for table {table_name} at {endpoint_name}')
    api.add_resource(_resource, f'/{endpoint_name}')

LOG.info('Launching application')
app.run(debug=os.environ.get('DEBUG', False))
