import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app import AutoSchema, AutoRestParser, AutoResource, app, api, LOG

db_url = 'bigquery://' + os.environ['GOOGLE_CLOUD_PROJECT']
LOG.info(f'Connecting to {db_url}')
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

LOG.info('Mapping database schema')
Base = declarative_base(bind=engine)
Base.metadata.reflect(bind=engine)

LOG.info('Defining API endpoints')
for table_name, table in Base.metadata.tables.items():
    endpoint_name = table_name.replace('.', '/')

    schema = AutoSchema(table, many=True)
    parser = AutoRestParser(table, schema)
    resource = AutoResource(table, schema, parser, Session)

    LOG.debug(f'Creating endpoint for table {table_name} at {endpoint_name}')
    api.add_resource(resource, f'/{endpoint_name}')

LOG.info('Launching application')
app.run(debug=os.environ.get('DEBUG', False))
