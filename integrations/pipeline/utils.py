from datetime import datetime, date, timedelta
import logging

from . import anu
from .. import live_bumps

logger = logging.getLogger('BumpsTasks')
logger.setLevel('INFO')


def anu_to_live_bumps(series: str, first_day_str: str, gender: str) -> None:
    """Loads the latest data from Anu's data files and pushes the results to Live Bumps."""
    
    # Get event days
    first_day = date.fromisoformat(first_day_str)
    days = [first_day + timedelta(i) for i in range(5)]
    
    active_days = [day for day in days if day <= datetime.now().date() + timedelta(1)]
    if len(active_days) < 2:
        return
    
    # Get event positions
    positions = []
    for day in active_days:
        
        start_order = anu.load_start_order(series, day, gender, day == days[-1])
        positions.append(anu.__start_order_to_positions(start_order))
        if not day == active_days[-1]:
            prev_start_order = start_order
    
    # Prune un-raced crews
    unraced_divisions = [
        division for division in prev_start_order
        if division['race_time'] >= datetime.now()
    ]
    unraced_crews = [crew for division in unraced_divisions for crew, _ in division['crews']]
    for crew in unraced_crews:
        del positions[-1][crew]
    
    # Update Live Bumps
    live_bumps.write_positions(series, first_day.year, positions)

