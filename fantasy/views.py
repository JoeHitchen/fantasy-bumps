from typing import TypedDict, Iterable, Any, TYPE_CHECKING

from django.views.generic.detail import DetailView
from django.views.generic.base import ContextMixin, TemplateView
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.utils.datastructures import MultiValueDictKeyError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models as db
from django.contrib.auth import models as auth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, HttpResponseBase

from .constants import Genders, GENDERS_OVERALL, money, timings, CoachingCompetitions
from . import models
from . import utils
from . import transactions
from . import errors


ContextKwargs = dict[str, Any]
ContextDict = dict[str, Any]


class EventAugmentation(TypedDict):
    user_fantasy: models.GameEntry
    _user_fantasy: list[models.GameEntry]

    mens_crew_ready: bool
    womens_crew_ready: bool


class CrewPopularity(TypedDict):
    purchase_count: int
    popularity: float


if TYPE_CHECKING:
    from django_stubs_ext import WithAnnotations

    EventDetailView = DetailView[models.Event]
    AugmentedEvent = WithAnnotations[models.Event, EventAugmentation]

    CrewWithPopularity = WithAnnotations[models.Crew, CrewPopularity]
    PositionWithPopularity = WithAnnotations[models.Position, CrewPopularity]

else:
    EventDetailView = DetailView

    CrewWithPopularity = models.Crew
    PositionWithPopularity = models.Position



class FantasyBaseMixin(ContextMixin):

    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)
        context['money'] = money
        context['timings'] = timings
        context['coaching'] = CoachingCompetitions
        context['trophy_types'] = models.Trophy.Types

        events = utils.ordered_events()
        if 'event' in context:
            events = events.exclude(id = context['event'].id)
        context['recent_events'] = events[:3]

        return context


    @staticmethod
    def augment_events_for_events_boxes(
        events: Iterable['AugmentedEvent'],
        user: auth.User | auth.AnonymousUser,
    ) -> None:
        """Prefetches data and sets additional event attributes for use with an event box."""

        # Add default financial and days prefetch
        seats = models.Seat.objects.all()
        db.prefetch_related_objects(events, db.Prefetch('days', to_attr = '_days'))  # type: ignore

        # Additional augmentation for logged in users
        if not user.is_anonymous:

            # User financial data prefetch
            db.prefetch_related_objects(
                events,  # type: ignore
                db.Prefetch(
                    'fantasies',
                    queryset = (
                        models.GameEntry.objects
                        .filter(team = user.team)
                        .extend_financials()
                    ),
                    to_attr = '_user_fantasy',
                ),
            )

            # User crews prefetch
            active_days = [event.active_day for event in events]
            db.prefetch_related_objects(
                active_days,
                db.Prefetch(
                    'purchases',
                    queryset = (
                        models.Purchase.objects
                        .filter(crew__gender = Genders.MEN, team = user.team)
                    ),
                    to_attr = 'mens_crew',
                ),
                db.Prefetch(
                    'purchases',
                    queryset = (
                        models.Purchase.objects
                        .filter(crew__gender = Genders.WOMEN, team = user.team)
                    ),
                    to_attr = 'womens_crew',
                ),
            )

            # Add user-specific extra event information
            for event in events:
                if event._user_fantasy:
                    event.user_fantasy = event._user_fantasy[0]
                event.mens_crew_ready = bool(
                    utils.has_all_seats(event.active_day.mens_crew, seats)
                    and not event.coaching_competition
                    or (hasattr(event, 'user_fantasy') and event.user_fantasy.mens_coach)
                    or event.active_day != event.first_day,
                )
                event.womens_crew_ready = bool(
                    utils.has_all_seats(event.active_day.womens_crew, seats)
                    and not event.coaching_competition
                    or (hasattr(event, 'user_fantasy') and event.user_fantasy.womens_coach)
                    or event.active_day != event.first_day,
                )



class IndexView(FantasyBaseMixin, TemplateView):
    template_name = 'fantasy/index.html'

    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)

        # Load and augment events
        context['recent_events'] = list(context['recent_events'])
        self.augment_events_for_events_boxes(context['recent_events'], self.request.user)

        return context



class RulesView(FantasyBaseMixin, TemplateView):
    template_name = 'fantasy/rules.html'



class EventsList(FantasyBaseMixin, TemplateView):
    template_name = 'fantasy/events.html'

    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)

        # Load and augment events
        context['recent_events'] = list(context['recent_events'])
        context['past_events'] = list(utils.ordered_events().exclude(
            id__in = [event.id for event in context['recent_events']],
        ))

        self.augment_events_for_events_boxes(
            context['past_events'] + context['recent_events'],
            self.request.user,
        )

        return context



class EventBase(FantasyBaseMixin, EventDetailView):
    """A base view for event-specific pages."""

    # View settings
    model = models.Event
    slug_url_kwarg = 'event_tag'
    slug_field = 'tag'

    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)

        self.event = self.object  # Provide friendly name for retrieved event.
        self.day = self.event.active_day
        context['day'] = self.day

        if self.request.user.is_authenticated:
            self.team = self.request.user.team
            context['team'] = self.team

        return context



class EventView(EventBase):
    """An main page for an event."""

    # View settings
    template_name = 'fantasy/event.html'

    def popular_crew_query(self, gender: Genders) -> db.QuerySet[CrewWithPopularity]:
        """Creates a Crew queryset with purchase counts and popularity scores."""

        purchase_count = db.Count(
            'purchases',
            filter = db.Q(purchases__day = self.day),
        )
        popularity = db.ExpressionWrapper(
            db.F('purchase_count') / self.game_entry_count,
            db.FloatField(),
        )

        return (
            models.Crew.objects
            .filter(gender = gender, positions__day = self.day)
            .annotate(purchase_count = purchase_count)
            .annotate(popularity = popularity)
            .order_by('-purchase_count', 'positions__rank')
            # ^ Sort by popularity not possible on SQLite
        )[:5]


    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)

        # Leaderboard data
        context['fantasies'] = (
            self.event.fantasies
            .select_related('team', 'team__user')
            .extend_financials()
            .rank_by(GENDERS_OVERALL)
        )[:5]
        context['trophies'] = (
            self.event.trophies
            .select_related('team', 'team__user')
            .prefetch_related(db.Prefetch(
                'team__entries',
                models.GameEntry.objects.filter(event = self.event).extend_financials(),
                to_attr = '_event_entry',
            )).all()
        )

        # Crew popularity data
        self.game_entry_count = self.event.fantasies.count() or 1  # Avoid Div0 error
        context['popular_crews_men'] = self.popular_crew_query(Genders.MEN)
        context['popular_crews_women'] = self.popular_crew_query(Genders.WOMEN)

        return context



class MarketView(EventBase):
    """Presents the market pages for an event."""

    # View settings
    template_name = 'fantasy/market.html'

    def add_purchase_count(
        self,
        start_order: db.QuerySet[models.Position],
    ) -> db.QuerySet[PositionWithPopularity]:
        """Extends a purchase queryset with purchase counts and popularity scores."""

        purchase_count = db.Count(
            'crew__purchases',
            filter = db.Q(crew__purchases__day = self.day),
        )
        popularity = db.ExpressionWrapper(
            db.F('purchase_count') / self.game_entry_count,
            db.FloatField(),
        )
        return (
            start_order
            .annotate(purchase_count = purchase_count)
            .annotate(popularity = popularity)
        )


    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)

        gender = self.kwargs['gender']
        context['gender'] = gender
        seats = models.Seat.objects.all()
        context['seats'] = seats
        is_first_day = self.day == self.day.event.first_day

        self.game_entry_count = self.day.event.fantasies.count() or 1  # Avoid Div0 error
        context['start_order'] = [
            self.add_purchase_count(division_start_order)
            for division_start_order in self.day.start_order(gender)
        ]

        if not self.request.user.is_authenticated:
            context['show_crew_actions'] = False
            context['show_coach_fire'] = False
            context['show_coach_hire'] = False
            return context

        try:
            game_entry = self.team.entries.extend_financials().get(event = self.event)
            context['finances'] = {
                Genders.MEN: {
                    'budget': game_entry.mens_budget,
                    'crew_value': game_entry.mens_crew_value,
                    'balance': game_entry.mens_balance,
                },
                Genders.WOMEN: {
                    'budget': game_entry.womens_budget,
                    'crew_value': game_entry.womens_crew_value,
                    'balance': game_entry.womens_balance,
                },
            }[gender]

        except models.GameEntry.DoesNotExist:
            context['finances'] = {
                'budget': money.INITIAL_BALANCE,
                'crew_value': 0,
                'balance': money.INITIAL_BALANCE,
            }

            context['show_crew_actions'] = self.day.market_is_open
            context['show_coach_row'] = self.day.event.coaching_competition and is_first_day
            context['show_coach_fire'] = False
            context['show_coach_hire'] = False
            context['crew'] = utils.crew_list_by_seat([], seats)
            context['coach_crew'] = None
            context['coach_name'] = None

            return context

        context['show_crew_actions'] = self.day.market_is_open
        crew = (
            self.request.user.team
            .get_crew(self.day, gender)
            .select_related('seat', 'crew', 'athlete')
            .prefetch_related(db.Prefetch(
                'crew__positions',
                models.Position.objects.filter(day = self.day),
                to_attr = '_position',
            ))
        )
        for purchase in crew:
            purchase.price = utils.pricing_by_day_gender(
                purchase.crew._position[0].rank,  # type: ignore
                self.day,
                gender,
            )
        context['crew'] = utils.crew_list_by_seat(crew, seats)
        crew_valid = utils.has_all_seats(crew, seats)

        require_coach = self.event.coaching_competition and is_first_day
        context['coach_crew'] = game_entry.get_coach(gender)
        context['coach_name'] = self.event.coaches.filter(crew = context['coach_crew']).first()
        context['show_coach_row'] = (
            self.day.event.coaching_competition
            and (context['coach_crew'] or is_first_day)
        )
        context['show_coach_fire'] = require_coach and context['show_crew_actions']
        context['show_coach_hire'] = (
            context['show_coach_fire']
            and crew_valid
            and not context['coach_crew']
        )

        other_gender = utils.reverse_gender(gender)
        other_crew = self.request.user.team.get_crew(self.day, other_gender)
        context['crew_valid'] = crew_valid and (not require_coach or context['coach_crew'])
        context['other_crew_valid'] = (
            utils.has_all_seats(other_crew, seats)
            and (not require_coach or game_entry.get_coach(other_gender))
        )
        return context



class LeaderboardView(EventBase):
    """Presents the leaderboard for an event."""

    # View settings
    template_name = 'fantasy/leaderboard.html'

    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)
        context['genders'] = Genders
        context['GENDERS_OVERALL'] = GENDERS_OVERALL

        invalid_entries = self.request.GET.get('invalid-entries', 'true') == 'true'
        allow_subs = self.request.GET.get('allow-subs', 'true') == 'true'
        returners = self.request.GET.get('returners', 'true') == 'true'
        context.update({
            'show_validity': self.day.prev,
            'show_subs_usage': self.day.prev and self.day.prev.prev,
            'invalid_entries': invalid_entries,
            'allow_subs': allow_subs,
            'returners': returners,
        })

        ranking = self.kwargs.get('gender', GENDERS_OVERALL)
        context['ranking'] = ranking
        context['fantasies'] = (
            self.event.fantasies
            .select_related('team', 'team__user')
            .filter(**{'valid_entry': True} if not invalid_entries else {})
            .filter(**{'has_subs': False} if not allow_subs else {})
            .annotate(previous_entries = db.Count(
                'id',
                filter = db.Q(team__entries__event_id__lt = self.event.id),
            ))
            .filter(**{'previous_entries': 0} if not returners else {})
            .extend_financials()
            .rank_by(ranking)
            .prefetch_related('team__trophies')
        )

        return context



class TeamView(EventBase):
    """Presents a team's crews for an event."""

    # View settings
    template_name = 'fantasy/team.html'

    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)

        related_selects = ['team', 'team__user', 'mens_coach', 'womens_coach']
        entry = get_object_or_404(
            models.GameEntry.objects.select_related(*related_selects).extend_financials(),
            team__user__username = self.kwargs['team_name'],
            event = self.event,
        )
        team = entry.team

        context['team'] = team
        context['seats'] = models.Seat.objects.all()
        context['finances'] = entry

        racing_days = self.day.event.days.filter(
            date__lte = self.day.date,
            first_race_time__isnull = False,
        )
        context['crews'] = [{
            'day': day,
            'mens_crew': utils.crew_list_by_seat(
                team.get_crew(day, Genders.MEN)
                .select_related('day', 'day__event', 'crew', 'seat', 'athlete'),
                context['seats'],
            ),
            'womens_crew': utils.crew_list_by_seat(
                team.get_crew(day, Genders.WOMEN)
                .select_related('day', 'day__event', 'crew', 'seat', 'athlete'),
                context['seats'],
            ),
        } for day in racing_days.reverse()]

        context['show_coach_row'] = self.event.coaching_competition and (
            entry.mens_coach
            or entry.womens_coach
            or self.event.active_day == self.event.first_day
        )
        context['mens_coach_crew'] = entry.mens_coach
        context['mens_coach_name'] = self.event.coaches.filter(crew = entry.mens_coach).first()
        context['womens_coach_crew'] = entry.womens_coach
        context['womens_coach_name'] = (
            self.event.coaches
            .filter(crew = entry.womens_coach)
            .first()
        )

        return context



@require_POST
@login_required(redirect_field_name = None)
def buy(request: HttpRequest) -> HttpResponse:
    """Purchas a new athlete for the user's team, if they have sufficient funds.

    Inputs:
        POST 'day'  - ID of Day on which to conduct purchase.
                      Markets must be open for that day.
        POST 'crew' - ID of Crew to purchase.
                      Must be racing on said day.

    Requires 14 base queries. Adding a team budget increases this by three.
    """
    assert isinstance(request.user, auth.User)  # Needed for MyPy

    # Process inputs
    try:
        team = request.user.team
        day = models.Day.objects.select_related().get(id = request.POST['day'])
        crew = models.Crew.objects.get(id = request.POST.get('crew', -1))

    except (ObjectDoesNotExist, MultiValueDictKeyError):
        messages.error(request, 'An error occurred processing the request data.')
        return redirect('fantasy:index')


    # Check market status
    gender_string = crew.get_gender_display().lower()
    market_url_name = f'fantasy:{gender_string}'
    market_redirect = redirect(market_url_name, event_tag = day.event.tag)

    if not day.market_is_open:
        messages.warning(request, 'Markets are not open for this sale.')
        return market_redirect


    # Get seat to fill
    filled_seats = team.get_crew(day, crew.gender).values_list('seat', flat = True)
    seat = models.Seat.objects.exclude(id__in = filled_seats).first()
    if not seat:
        messages.warning(request, "You have already filled your {}'s crew.".format(gender_string))
        return market_redirect


    # Get athlete
    try:
        athlete = crew.crew_lists.get(event = day.event, seat = seat)
    except models.Athlete.DoesNotExist:
        athlete = None


    # Perform transaction
    try:
        transactions.buy(team, day, seat, crew, athlete)

    except errors.NotRacingError:
        messages.warning(request, 'Cannot buy a crew on a day they are not racing.')

    except errors.InsufficientFundsError:
        messages.warning(request, 'You do not have sufficient funds to make this purchase.')

    # Generate success message
    else:
        athlete_string = '{} ({})'.format(athlete, crew) if athlete else crew

        if seat.cox:
            seat_string = 'cox'
        elif len(seat.name) == 1:
            seat_string = seat.name.lower() + '-seat'
        else:
            seat_string = seat.name.lower() + ' seat'

        success_text = "Bought {} as your {}'s {}.".format(
            athlete_string,
            gender_string,
            seat_string,
        )
        messages.success(request, success_text)

    return market_redirect



@require_POST
@login_required(redirect_field_name = None)
def sell(request: HttpRequest) -> HttpResponse:
    """Sell a previously bought athlete, to release the cash and seat.

    Inputs:
        POST 'purchase' - ID of the Purchase object to sell.
                          Must belong to user's team.
                          Must be for day that has currently open markets.

    Requires nine queries.
    """
    assert isinstance(request.user, auth.User)  # Needed for MyPy

    # Process input data
    try:
        purchase = models.Purchase.objects.select_related().get(
            id = request.POST['purchase'],
            team = request.user.team,
        )

    except (models.Purchase.DoesNotExist, MultiValueDictKeyError):

        # Try elegant redirect back to market page using additional form data
        messages.error(request, 'You are not authorised to conduct this sale.')
        try:
            gender = Genders(request.POST['gender'])
            url_name = f'fantasy:{gender.label.lower()}'
            event = models.Event.objects.get(tag = request.POST.get('event'))
            return redirect(url_name, event_tag = event.tag)

        except (KeyError, models.Event.DoesNotExist):
            return redirect('fantasy:index')


    # Check market status
    gender_string = purchase.crew.get_gender_display().lower()
    market_url_name = f'fantasy:{gender_string}'
    market_redirect = redirect(market_url_name, event_tag = purchase.day.event.tag)

    if not purchase.day.market_is_open:
        messages.warning(request, 'Markets are not open for this sale.')
        return market_redirect


    # Perform transaction
    try:
        transactions.sell(purchase)

    except models.Purchase.DoesNotExist:
        messages.warning(request, 'This sale has already been completed.')

    except (models.GameEntry.DoesNotExist, MultipleObjectsReturned):
        messages.error(request, 'An unknown error occurred processing this sale.')

    # Generate success message
    else:
        if purchase.athlete:
            athlete_string = '{} ({})'.format(purchase.athlete, purchase.crew)
        else:
            athlete_string = str(purchase.crew)

        if purchase.seat.cox:
            seat_string = 'coxing seat'
        elif len(purchase.seat.name) == 1:
            seat_string = purchase.seat.name.lower() + '-seat'
        else:
            seat_string = purchase.seat.name.lower() + ' seat'

        success_text = "Sold {} from your {}'s {}.".format(
            athlete_string,
            gender_string,
            seat_string,
        )
        messages.success(request, success_text)

    return market_redirect



@require_POST
@login_required(redirect_field_name = None)
def hire(request: HttpRequest) -> HttpResponse:
    """Hires a coach.

    Inputs:
        POST 'event' - Tag of the event for the hiring.
                        Must have first day markets open.
             'crew'  - ID of the crew to hire as coach.

    Requires seven queries.
    """
    assert isinstance(request.user, auth.User)  # Needed for MyPy

    try:
        fantasy = (
            models.GameEntry.objects
            .select_related('event')
            .get(event__tag = request.POST['event'], team = request.user.team)
        )
    except (models.GameEntry.DoesNotExist, MultiValueDictKeyError):
        messages.error(request, 'Unable to find a matching competition entry.')
        return redirect('fantasy:index')

    try:
        crew = models.Crew.objects.get(id = request.POST['crew'])
        gender_string = Genders(crew.gender).label.lower()
    except (models.Crew.DoesNotExist, MultiValueDictKeyError):
        messages.error(request, 'Unable to find the coach being hired.')
        return redirect('fantasy:index')


    # Check market status
    market_redirect = redirect(f'fantasy:{gender_string}', event_tag = fantasy.event.tag)

    if not fantasy.event.first_day.market_is_open:
        messages.warning(request, 'Markets are not open for this hiring.')
        return market_redirect


    # Hire coach
    fantasy.set_coach(Genders(crew.gender), crew)
    fantasy.save()

    messages.success(request, f"Hired {crew} as your {gender_string}'s coach.")
    return market_redirect



@require_POST
@login_required(redirect_field_name = None)
def fire(request: HttpRequest) -> HttpResponse:
    """Fires a previously hired coach.

    Inputs:
        POST 'event'  - Tag of the event for the firing.
                        Must have first day markets open.
             'gender' - Gender of the crew to fire the coach for.

    Requires six queries.
    """
    assert isinstance(request.user, auth.User)  # Needed for MyPy

    try:
        fantasy = (
            models.GameEntry.objects
            .select_related('event', 'mens_coach', 'womens_coach')
            .get(event__tag = request.POST['event'], team = request.user.team)
        )
        gender = Genders(request.POST['gender'])
    except (models.GameEntry.DoesNotExist, MultiValueDictKeyError, ValueError):
        messages.error(request, 'Unable to identify the coach to be fire.')
        return redirect('fantasy:index')


    # Check market status
    market_url_name = f'fantasy:{gender.label.lower()}'
    market_redirect = redirect(market_url_name, event_tag = fantasy.event.tag)

    if not fantasy.event.first_day.market_is_open:
        messages.warning(request, 'Markets are not open for this firing.')
        return market_redirect

    # Identify and fire coach
    old_coach = fantasy.get_coach(gender)
    fantasy.set_coach(gender, None)
    fantasy.save()

    messages.success(request, (
        f"Fired {old_coach} as your {gender.label.lower()}'s coach."
        if old_coach else
        f"Your {gender.label.lower()}'s coaching slot is now empty."
    ))
    return market_redirect



class Switch(FantasyBaseMixin, TemplateView):
    """Presents athlete and seat selectors for a purchase to alter it.

    Additionally, has a POST action to perform the switch.
    """
    template_name = 'fantasy/switch.html'

    @method_decorator(login_required(redirect_field_name = None))
    def dispatch(
        self,
        request: HttpRequest,
        *args: list[Any],
        **kwargs: dict[str, Any],
    ) -> HttpResponseBase:
        assert isinstance(request.user, auth.User)  # Needed for MyPy

        # Look for purchase
        self.purchase = get_object_or_404(
            models.Purchase.objects.select_related(),  # Misses purchase.athlete, but simpler code
            id = kwargs.get('purchase_id', None),
            team = request.user.team,
        )

        # Check market status
        market_url_name = f'fantasy:{self.purchase.crew.get_gender_display().lower()}'
        self.market_redirect = redirect(market_url_name, event_tag = self.purchase.day.event.tag)

        if not self.purchase.day.market_is_open:
            messages.warning(request, 'Markets are not open to alter this purchase.')
            return self.market_redirect

        # Cannot switch coxes
        if self.purchase.seat.cox:
            messages.warning(request, 'Coxes must stay in their place.')
            return self.market_redirect

        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs: ContextKwargs) -> ContextDict:
        context = super().get_context_data(**kwargs)

        context['event'] = self.purchase.day.event
        context['purchase'] = self.purchase

        context['rowers'] = models.Athlete.objects.filter(
            event = self.purchase.day.event,
            crew = self.purchase.crew,
            seat__cox = False,
        ).select_related('seat')


        other_purchases = self.purchase.team.get_crew(
            day = self.purchase.day,
            gender = self.purchase.crew.gender,
        ).exclude(id = self.purchase.id)

        context['other_purchased_athletes'] = models.Athlete.objects.filter(
            id__in = other_purchases.values_list('athlete', flat = True),
        )

        context['seats'] = models.Seat.objects.all()

        return context


    def post(self, request: HttpRequest, purchase_id: int) -> HttpResponse:
        """Move a purchase between rowing seats and select named athlete.

        Inputs:
            POST 'athlete_id': ID of Athlete to occupy Seat (or '0' for unnamed athlete)
            POST 'seat_id':    ID of Seat for Athlete to occupy

        Requires 12 queries.
        """

        # Perform action
        try:
            seat = models.Seat.objects.get(id = request.POST.get('seat', -1))
            if 'athlete' in request.POST:
                athlete = (
                    models.Athlete.objects
                    .filter(id = request.POST.get('athlete', -1))
                    .select_related('seat').first()
                )
            else:
                athlete = self.purchase.athlete

            updated_purchase = transactions.switch(self.purchase, seat, athlete)

        except (models.Athlete.DoesNotExist, errors.ReverseNinthSeatError, errors.WrongCrewError):
            messages.warning(request, 'Must pick a rower from the purchased crew.')

        except errors.DuplicateAthleteError:
            messages.warning(request, 'Cannot pick the same rower twice.')

        except models.Seat.DoesNotExist:
            messages.warning(request, 'Target seat does not exist.')

        except errors.NinthSeatError:
            messages.warning(request, "Rowers can't cox.")

        # Generate success message
        else:

            if updated_purchase.athlete:
                crew_string = '{} ({})'.format(updated_purchase.athlete, updated_purchase.crew)
            else:
                crew_string = str(updated_purchase.crew)

            seat_string = updated_purchase.seat.name.lower()
            seat_string = seat_string + ('-' if len(seat_string) == 1 else ' ') + 'seat'

            messages.success(request, "Selected {} for your {}'s {}.".format(
                crew_string,
                self.purchase.crew.get_gender_display().lower(),
                seat_string,
            ))


        return self.market_redirect



def is_superuser(user: auth.AbstractBaseUser | auth.AnonymousUser) -> bool:
    return isinstance(user, auth.User) and user.is_superuser


@require_POST
@user_passes_test(is_superuser, redirect_field_name = None)
def market_hold(request: HttpRequest) -> HttpResponse:
    """Toggles the `market_held_closed` flag for an event."""

    event = get_object_or_404(models.Event, tag = request.POST.get('event'))
    event.market_held_closed = request.POST.get('toggle-from') == 'False'
    event.save()

    return redirect('fantasy:index')

