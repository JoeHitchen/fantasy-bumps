from typing import TypedDict
from datetime import datetime


class IntervalSchedule():
    MINUTES: str
    objects: _IntervalManager


class PeriodicTask():
    objects: _PeriodicManager


class _IntervalManager():
    
    def get_or_create(self, period: str, every: int) -> tuple[IntervalSchedule, bool]:
        ...


class _PeriodicManager():
    
    def update_or_create(self, task: str, kwargs: str, defaults: _TaskSpec) -> None:
        ...


class _TaskSpec(TypedDict):
    name: str
    interval: IntervalSchedule
    expires: datetime

