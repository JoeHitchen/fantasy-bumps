from typing import TypedDict, TYPE_CHECKING
from enum import Enum

from django.db import models as db
from django.contrib.auth import models as auth

from ..constants import Genders, money
from .. import models, utils


class Blades(Enum):
    WON = 'won'
    ON = 'on'
    OFF = 'off'
    LOST = 'lost'


class MarketStatus(TypedDict):
    style: str
    dismissable: bool
    message: str


class BunglinePopularity(TypedDict):
    bungline: int
    popularity: float


class CoachingButton(TypedDict):
    competition: str
    payout_condition: str


class AnalysisButton(TypedDict):
    analysis_crew: models.Crew
    popularity: float
    bump_up: int
    row_over: int
    bumped_down: int


class PopularityRow(TypedDict):
    rank: int
    crew: 'CrewWithPopularity'


class BuyButton(TypedDict):
    day: models.Day
    crew: models.Crew
    crew_value: int
    disabled: str


class SellButton(TypedDict):
    purchase: models.Purchase
    crew_value: int


class HireButton(TypedDict):
    crew: models.Crew


class FireButton(TypedDict):
    pass


class SwitchButton(TypedDict):
    purchase: models.Purchase


class MarketRow(TypedDict):
    position: models.Position
    disabled: bool
    show_crew_actions: bool
    show_coach_hire: bool


class MarketDivision(TypedDict):
    division: db.QuerySet[models.StartOrderPosition]
    gender: Genders
    number: int
    balance: int
    show_crew_actions: bool
    show_coach_hire: bool


class GenderFinances(TypedDict):
    budget: int
    crew_value: int
    balance: int


class CrewListRow(TypedDict):
    seat: models.Seat
    purchase: models.Purchase
    club: str | None
    show_crew_actions: bool
    payout: utils.Payout | None


class CrewListBox(TypedDict):
    crew_list: list[tuple[models.Seat, models.Purchase | None]]
    finances: GenderFinances | None
    show_crew_actions: bool
    evaluate_payouts: bool
    event: models.Event | None


class CrewListCoachRow(TypedDict):
    event: models.Event | None
    crew: models.Crew | None
    club: str | None
    name: models.Coach | None
    show_coach_fire: bool


class CrewListCoachResult(TypedDict):
    crew: models.Crew | None
    club: str | None
    name: models.Coach | None
    payout: utils.Payout | None
    payout_html: str


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

