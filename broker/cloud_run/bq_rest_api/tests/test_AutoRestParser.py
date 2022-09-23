from unittest import TestCase

from tests.utils import GenericSetup


# Todo: The tests in this document are under construction

class ArgumentParsing(GenericSetup, TestCase):
    """Tests for the parsing/casting of rest arguments"""

    def test_orderby_choices_match_columns(self) -> None:
        """Test choices for the ``orderby`` argument match DB column names"""

        orderby_arg = self.parser.args[2]
        expected_columns = [c.name for c in self.table.columns]

        self.assertEqual('orderby', orderby_arg.name)  # Check correct argument is being tested
        self.assertCountEqual(expected_columns, orderby_arg.choices.keys())
