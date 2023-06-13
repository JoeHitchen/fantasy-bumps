from typing import TypedDict


class IntervalSchedule():
    MINUTES: str
    objects: _IntervalManager


class ClockedSchedule():
    objects: _ClockedManager


class PeriodicTask():
    objects: _PeriodicManager


class _IntervalManager():
    
    def get_or_create(self, period: str, every: int) -> tuple[IntervalSchedule, bool]:
        ...


class _ClockedManager():
    
    def get_or_create(self, clocked_time: bool) -> tuple[ClockedSchedule, bool]:
        ...


class _PeriodicManager():
    
    def filter(self, name: str) -> _PeriodicManager:
        ...
    
    def update(self, enabled: bool) -> None:
        ...
    
    def update_or_create(
        self,
        task: str,
        kwargs: str,
        defaults: _TaskSpec1 | _TaskSpec2,
        name: str = '',
    ) -> None:
        ...


class _TaskSpec1(TypedDict):
    name: str
    interval: IntervalSchedule


class _TaskSpec2(TypedDict):
    clocked: ClockedSchedule
    one_off: bool

