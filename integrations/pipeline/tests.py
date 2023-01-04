from datetime import date

from django.test import TestCase

from . import common, anu


class Test__Anu(TestCase):
    
    def test__load_start_order__smoke(self):
        """Checks no errors are raised parsing all Anu's known start/finish order data files."""
        
        event_days = [
            (common.TORPIDS, '2022-03-02', False),
            (common.TORPIDS, '2022-03-03', False),
            (common.TORPIDS, '2022-03-04', False),
            (common.TORPIDS, '2022-03-05', False),
            (common.TORPIDS, '2022-03-06', True),
            (common.EIGHTS, '2022-05-25', False),
            (common.EIGHTS, '2022-05-26', False),
            (common.EIGHTS, '2022-05-27', False),
            (common.EIGHTS, '2022-05-28', False),
            (common.EIGHTS, '2022-05-29', True),
        ]
        
        for day in event_days:
            
            event_date = date.fromisoformat(day[1])
            mens_args = (day[0], event_date, common.MEN, day[2])
            womens_args = (day[0], event_date, common.WOMEN, day[2])
        
            with self.subTest(call_args = mens_args):
                anu.load_start_order(*mens_args)
            
            with self.subTest(call_args = womens_args):
                anu.load_start_order(*womens_args)

