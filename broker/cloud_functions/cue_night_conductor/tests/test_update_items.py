import sys
from unittest import TestCase

sys.path.append('..')
from main import get_update_items


class Test(Testcase):
    """This is a placeholder test just so the CI pipeline has something to run"""

    def runtest(self):
        cue = 'END'
        output = get_update_items(cue, None)
        self.assertEqual(output[0], [{'key': 'NIGHT', 'value': cue}])
