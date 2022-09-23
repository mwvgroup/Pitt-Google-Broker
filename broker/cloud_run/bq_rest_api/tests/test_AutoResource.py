from unittest import TestCase

from tests.utils import GenericSetup


class AutomaticResourceCreation(GenericSetup, TestCase):
    """Tests the factory creation of resource objects"""

    def test_generated_class_name(self) -> None:
        """Test the resource class name is generated using the table name"""

        expected_name = self.table.name + 'Resource'
        self.assertEqual(expected_name, self.resource.__name__)
