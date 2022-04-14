from django.test import TestCase, tag

from parsing import anu


@tag('external')
class Test__Anu(TestCase):
    
    cases = [
        # At time of writing, no pre-Covid start orders are available
        ('T', 2021, ['tue', 'wed', 'thu', 'fri', 'end'], 128),
        ('T', 2022, ['wed', 'thu', 'fri', 'sat', 'end'], 134),
    ]
    
    def test__anu(self):
        """Checks no errors are raised parsing all Anu's known start/finish orders."""
        
        for series, year, days, num_crews in self.cases:
            for day in days:
                
                with self.subTest((series, year, day)):
                    order = anu.get_start_order(series, year, day)
                    self.assertEqual(len(order.keys()), num_crews)

