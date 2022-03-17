from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from main import AutoSchema, AutoRestParser, AutoResource

SqlalchemyBase = declarative_base()
engine = create_engine('sqlite:///test.db')
Session = sessionmaker(bind=engine)


class DummyTable(SqlalchemyBase):
    """Simple dummy table used for testing purposes"""

    __tablename__ = 'dummy_table'
    col1 = Column(Integer, primary_key=True)
    col2 = Column(String)


class GenericSetup:
    """Reusable class setup tasks used by multiple test cases"""

    @classmethod
    def setUpClass(cls) -> None:
        """Create ``AutoSchema``, ``AutoRestParser``, and ``AutoResource`` instances"""

        # Get table from metadata so AutoSchema is tested
        # the same way it is used in deployment
        cls.table = SqlalchemyBase.metadata.tables['dummy_table']
        cls.schema = AutoSchema(cls.table)

        cls.schema = AutoSchema(cls.table, many=True)
        cls.parser = AutoRestParser(cls.table, cls.schema)
        cls.resource = AutoResource(cls.table, cls.schema, cls.parser, Session)
