from unittest import TestCase

from tests.utils import GenericSetup


class AutomaticSchemaCreation(GenericSetup, TestCase):
    """Tests the factory creation of schema objects"""

    def test_has_table_fields(self) -> None:
        """Test schema field names match DB table columns"""

        expected_columns = [c.name for c in self.table.columns]
        self.assertCountEqual(expected_columns, self.schema.fields)

    def test_generated_class_name(self) -> None:
        """Test the schema class name is generated using the table name"""

        expected_name = self.table.name + 'Schema'
        self.assertEqual(expected_name, self.schema.__class__.__name__)
