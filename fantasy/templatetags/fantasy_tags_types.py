from typing import TypedDict, TYPE_CHECKING

from django.db import models as db
from django.contrib.auth import models as auth

from ..constants import Genders, money
from .. import models


class MarketStatus(TypedDict):
    style: str
    dismissable: bool
    message: str


class BunglinePopularity(TypedDict):
    bungline: int
    popularity: float


class AnalysisButton(TypedDict):
    analysis_crew: models.Crew
    popularity: float
    bump_up: int
    row_over: int
    bumped_down: int


class PopularityRow(TypedDict):
    rank: int
    crew: 'CrewWithPopularity'


class MiniLeaderboardRow(TypedDict):
    fantasy: models.FinancialGameEntry
    rank: int
    event: models.Event
    style: str


class BuyButton(TypedDict):
    day: models.Day
    crew: models.Crew
    crew_value: int
    disabled: str


class SellButton(TypedDict):
    purchase: models.Purchase
    crew_value: int


class SwitchButton(TypedDict):
    purchase: models.Purchase


class MarketRow(TypedDict):
    position: models.Position
    disabled: bool
    show_crew_actions: bool


class MarketDivision(TypedDict):
    division: db.QuerySet[models.StartOrderPosition]
    gender: Genders
    number: int
    balance: int
    show_crew_actions: bool


class GenderFinances(TypedDict):
    budget: int
    crew_value: int
    balance: int


class CrewListRow(TypedDict):
    seat: models.Seat
    purchase: models.Purchase
    club: str | None
    show_crew_actions: bool


class CrewListBox(TypedDict):
    crew_list: list[tuple[models.Seat, models.Purchase | None]]
    finances: GenderFinances | None
    show_crew_actions: bool


class CrewListCoachRow(TypedDict):
    crew: models.Crew | None
    club: str | None


class CrewStatusStyling(TypedDict):
    colour: str
    crew: str
    text: str


class CrewStatusBox(TypedDict):
    main: CrewStatusStyling
    other: CrewStatusStyling
    other_gender_link: str


class CrewReadyButton(TypedDict):
    link: str
    colour: str
    text: str


class EventAugmentation(TypedDict):
    mens_crew_ready: bool
    womens_crew_ready: bool


class EventBox(TypedDict):
    event: 'AugmentedEvent'
    genders: type[Genders]
    user: auth.User | auth.AnonymousUser
    money: type[money]


if TYPE_CHECKING:
    from django_stubs_ext import WithAnnotations

    PositionWithPopularity = WithAnnotations[models.Position, BunglinePopularity]
    CrewWithPopularity = WithAnnotations[models.Crew, BunglinePopularity]
    AugmentedEvent = WithAnnotations[models.Event, EventAugmentation]

else:
    PositionWithPopularity = models.Position
    CrewWithPopularity = models.Crew
    AugmentedEvent = models.Event

