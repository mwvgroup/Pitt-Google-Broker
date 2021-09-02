from unittest import TestCase

from broker.broker_utils.broker_utils import data_utils


class JDtoMJD(TestCase):
    """Test the conversion from Julian Date to Modified Julian Date"""

    def test_correct_conversion_epoch(self) -> None:
        """Test the correct offset is returned for JD=0"""

        zero_jd_in_mjd = -2400000.5
        returned_mjd = data_utils.jd_to_mjd(0)
        self.assertEqual(zero_jd_in_mjd, returned_mjd)
