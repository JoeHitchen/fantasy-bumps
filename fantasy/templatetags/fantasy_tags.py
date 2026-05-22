from datetime import datetime, timedelta

from django import template
from django.db import models as db
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.auth import models as auth
from django.templatetags.static import static
from django.contrib.humanize.templatetags.humanize import naturalday

from ..constants import Genders, money
from .. import models, utils
from . import fantasy_tags_types as types

register = template.Library()


@register.inclusion_tag(template.Template('''
  <div class="alert alert-{{ style }}{% if dismissable %} alert-dismissible fade show{% endif %}">
    {{ message }}
    {% if dismissable %}<button class="close" data-dismiss="alert">
      <span>&times;</span>
    </button>{% endif %}
  </div>
'''))
def market_status_box(day: models.Day, allow_dismiss: bool = True) -> types.MarketStatus:
    """Creates the properties for an alert box that describes the market status."""

    # Preparation
    now = timezone.localtime()

    def datetime_string(datetime: datetime) -> str:
        """Generates a partially humanised datetime."""

        day_string = naturalday(datetime, 'l')
        assert day_string  # Needed for MyPy

        if day_string[0:2] != 'to':
            day_string = 'on ' + day_string
        return '{:%H:%M} {}'.format(datetime, day_string)


    # While market open
    if day.market_is_open and day.market_closes:  # Duplication needed for MyPy
        return {
            'style': 'warning' if day.market_closes - now <= timedelta(hours = 6) else 'info',
            'dismissable': allow_dismiss,
            'message': 'The market is open until {}.'.format(
                datetime_string(day.market_closes),
            ),
        }


    # Held closed
    if day.event.market_held_closed or (day.prev and not day.prev.advanced):
        return {
            'style': 'danger',
            'dismissable': False,
            'message': 'The market is being held closed for technical reasons.',
        }

    # After racing
    if not day.next:
        return {
            'style': 'info',
            'dismissable': False,
            'message': 'This event has concluded.',
        }

    # Market closed
    future_open = day.market_opens if day.market_opens and now < day.market_opens else None
    if (not future_open) and day.next and day.next.market_opens and day.next.market_opens >= now:
        future_open = day.next.market_opens
    return {
        'style': 'danger',
        'dismissable': False,
        'message': 'The market is closed{}.'.format(
            ', and will open at {}'.format(datetime_string(future_open))
            if future_open
            else '',
        ),
    }


@register.filter
def avatar(text: str | int, club: str | None = None) -> str:
    classes = 'avatar' + (' club-' + club if club else '')
    return format_html('<span class="{1} flex-shrink-0">{0}</span>', text, classes)


@register.filter
def currency(amount: int) -> str:
    return format_html('{}&nbsp;🦀', amount)


@register.filter
def popularity_indicator(popularity: float) -> str:
    return mark_safe('<span class="popularity">{:.2}</span>'.format(popularity))


@register.inclusion_tag(template.Template('''
  <button
      class="payout btn btn-primary btn-sm flex-shrink-0"
      data-toggle="popover"
      data-placement="top"
      title="Analysis for {{ analysis_crew }}"
      data-popularity="{{ popularity|floatformat:2 }}"
      data-bump-up="{{ bump_up|stringformat:"+d" }}"
      data-row-over="{{ row_over|stringformat:"+d" }}"
      data-bumped-down="{{ bumped_down|stringformat:"+d" }}"
  >
    {{ popularity|floatformat:2 }}&nbsp;&nbsp;<span class="oi oi-graph"></span>
  </button>
'''))
def analysis_button(position: types.PositionWithPopularity) -> types.AnalysisButton:

    def delta_crabs_for_change(position_change: int) -> int:
        delta_crabs = utils.payout_by_day_gender_positions(
            position.day,
            Genders(position.crew.gender),
            position.rank,
            position.rank - position_change,
        )
        return delta_crabs['value_change'] + delta_crabs['payout']

    bump_up = delta_crabs_for_change(+1) if not position.rank == 1 else 0
    row_over = delta_crabs_for_change(0)
    bumped_down = (
        delta_crabs_for_change(-1)
        if not position.rank == position.day.event.num_crews(Genders(position.crew.gender))
        else 0
    )

    return {
        'analysis_crew': position.crew,
        'popularity': position.popularity,
        'bump_up': bump_up,
        'row_over': row_over,
        'bumped_down': bumped_down,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <a
    href="{% url 'fantasy:team' event.tag fantasy.team.user.username %}"
    class="list-group-item list-group-item-action popularity-row"
  >
    {{ rank|avatar:style }}
    <div class="flex-grow-1">{{ fantasy.team }}</div>
    <span>{{ fantasy.total_budget }}</span>
  </a>
'''))
def mini_leaderboard_row(
    rank: int,
    fantasy: models.FinancialGameEntry,
    event: models.Event,
) -> types.MiniLeaderboardRow:
    style_matrix = {1: 'first', 2: 'second', 3: 'third'}
    return {
        'fantasy': fantasy,
        'rank': rank,
        'event': event,
        'style': style_matrix.get(rank, 'other'),
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group-item popularity-row">
    {{ rank|avatar:crew.club }}
    <div class="flex-grow-1">{{ crew }}</div>
    {{ crew.popularity|popularity_indicator }}
  </div>
'''))
def popularity_row(rank: int, crew: types.CrewWithPopularity) -> types.PopularityRow:
    return {'rank': rank, 'crew': crew}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <button
    class="btn btn-primary btn-sm btn-buy{{ disabled }} flex-shrink-0"
    {% if not disabled %}data-day="{{ day.id }}" data-crew="{{ crew.id }}"{% endif %}
  >
    Buy {{ crew_value|currency }}
  </button>
'''))
def buy_button(position: models.Position, disabled: bool = False) -> types.BuyButton:
    return {
        'day': position.day,
        'crew': position.crew,
        'crew_value': utils.pricing_by_day_gender(
            position.rank,
            position.day,
            Genders(position.crew.gender),
        ),
        'disabled': ' disabled' if disabled else '',
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <button class="btn btn-primary btn-sm btn-sell flex-shrink-0" data-purchase="{{ purchase.id }}">
    Sell {{ crew_value|currency }}
  </button>
'''))
def sell_button(purchase: models.Purchase) -> types.SellButton:
    price = purchase.price if hasattr(purchase, 'price') else purchase.crew.value(purchase.day)
    return {'purchase': purchase, 'crew_value': price}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <button class="btn btn-primary btn-sm btn-hire flex-shrink-0" data-crew="{{ crew.id }}">
    Hire Coach
  </button>
'''))
def hire_button(crew: models.Crew) -> types.HireButton:
    return {'crew': crew}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <button class="btn btn-primary btn-sm btn-fire flex-shrink-0">
    Fire Coach
  </button>
'''))
def fire_button() -> types.FireButton:
    return {}


@register.inclusion_tag(template.Template('''
  {% load static %}
  {% if not purchase.seat.cox %}
    <a
        href="{% url 'fantasy:switch' purchase.id %}" class="btn btn-sm btn-primary"
        data-toggle="tooltip" data-placement="top" title="Change athlete or seat"
    >
      <img class="btn-switch" src="{% static 'fantasy/switch-white.svg' %}" />
    </a>
  {% endif %}
'''))
def switch_button(purchase: models.Purchase) -> types.SwitchButton:
    return {'purchase': purchase}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group-item market-row">
    {{ position.bungline|avatar:position.crew.club }}
    <div class="flex-grow-1">{{ position.crew }}</div>
    {% analysis_button position %}
    {% if show_crew_actions %}{% buy_button position disabled %}{% endif %}
    {% if show_coach_hire %}{% hire_button position.crew %}{% endif %}
  </div>
'''))
def market_row(
    position: models.Position,
    balance: int,
    show_crew_actions: bool,
    show_coach_hire: bool,
) -> types.MarketRow:

    crew_value = utils.pricing_by_day_gender(
        position.rank,
        position.day,
        Genders(position.crew.gender),
    )

    disabled = show_crew_actions and crew_value > balance

    return {
        'position': position,
        'disabled': disabled,
        'show_crew_actions': show_crew_actions,
        'show_coach_hire': show_coach_hire,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group mb-3">
    <div class="list-group-item list-group-item-dark market-row">
      <h5 class="mb-0">{{ gender.label }}'s Division {{ number }}</h5>
    </div>
    {% for position in division %}
      {% market_row position balance show_crew_actions show_coach_hire %}
    {% endfor %}
  </div>
'''))
def market_division_box(
    division: db.QuerySet[models.StartOrderPosition],
    gender: Genders,
    number: int,
    balance: int,
    show_crew_actions: bool,
    show_coach_hire: bool,
) -> types.MarketDivision:
    return {
        'division': division,
        'gender': gender,
        'number': number,
        'balance': balance,
        'show_crew_actions': show_crew_actions and not show_coach_hire,
        'show_coach_hire': show_coach_hire,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group-item list-group-item-dark crew-row">
    <div class="container"><div class="row justify-content-between">
      <span>Crew Value: {{ crew_value|currency }}</span>
      <span>Cash: {{ balance|currency }}</span>
    </div></div>
  </div>
'''))
def crew_list_header(finances: types.GenderFinances) -> types.GenderFinances:
    return finances


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group-item{% if not purchase %} list-group-item-danger{% endif %} crew-row">
    {{ seat.short|avatar:club }}
    {% if purchase %}
    <div class="flex-grow-1{% if purchase.athlete %} crew-row-athlete{% endif %}">
      {% if purchase.athlete %}<div>{{ purchase.athlete }}</div>{% endif %}
      <div>{{ purchase.crew }}</div>
    </div>
    {% if show_crew_actions %}
      {% switch_button purchase %}
      {% sell_button purchase %}
    {% endif %}
    {% endif %}
  </div>
'''))
def crew_list_row(
    seat: models.Seat,
    purchase: models.Purchase,
    show_crew_actions: bool,
) -> types.CrewListRow:
    return {
        'seat': seat,
        'purchase': purchase,
        'club': purchase.crew.club if purchase else None,
        'show_crew_actions': show_crew_actions,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  {% if finances %}
    {% crew_list_header finances %}
  {% endif %}
  {% for seat, rower in crew_list %}
    {% crew_list_row seat rower show_crew_actions %}
  {% endfor %}
'''))
def crew_list_box(
    crew_list: db.QuerySet[models.Purchase],
    seats: db.QuerySet[models.Seat],
    finances: types.GenderFinances | None = None,
    show_crew_actions: bool = False,
) -> types.CrewListBox:
    seat_rowers = {seat: [
        rower for rower in crew_list if rower.seat == seat
    ] for seat in seats}

    merged_crew_list = [(
        seat,
        rowers[0] if rowers else None,
    ) for seat, rowers in seat_rowers.items()]

    return {
        'crew_list': merged_crew_list,
        'finances': finances,
        'show_crew_actions': show_crew_actions,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group-item{% if not crew %} list-group-item-danger{% endif %} crew-row">
    {{ "X"|avatar:club }}
    {% if crew %}
    <div class="flex-grow-1{% if name %} crew-row-athlete{% endif %}">
      {% if name %}<div>{{ name }}</div>{% endif %}
      <div>{{ crew }}</div>
    </div>
    {% if show_coach_fire %}{% fire_button %}{% endif %}
    {% endif %}
  </div>
'''))
def crew_list_coach_row(
    crew: models.Crew | None,
    name: models.Coach | None,
    show_coach_fire: bool = False,
) -> types.CrewListCoachRow:
    return {
        'crew': crew,
        'club': crew.club if crew else None,
        'name': name,
        'show_coach_fire': show_coach_fire,
    }


@register.inclusion_tag(template.Template('''
    <div class="list-group-item p-0">
      <table class="table table-sm table-borderless mb-0"><tr>
      <td class="table-{{ main.colour }} text-center align-middle" style="width: 50%">
        <strong>{{ main.crew }}</strong>
        <br/>
        <strong class="text-{{ main.colour }}">{{ main.text }}</strong>
      </td>
      <td class="table-{{ other.colour }} text-center" style="width: 50%">
        <strong>{{ other.crew }}</strong>
        <br/>
        <strong class="text-{{ other.colour }}">{{ other.text }}</strong>
        <a href="{{ other_gender_link }}" class="btn btn-sm btn-{{ other.colour }} ml-2 px-1 py-0">
          View <small><span class="oi oi-chevron-right"></span></small>
        </a>
      </td>
      </tr></table>
    </div>
'''))
def crew_status_box(
    event: models.Event,
    gender: Genders,
    crew_valid: bool,
    other_crew_valid: bool,
) -> types.CrewStatusBox:

    def styling(gender: Genders, valid: bool, done: bool) -> types.CrewStatusStyling:
        return {
            'colour': 'primary' if done else 'success' if valid else 'danger',
            'crew': "{}'s crew".format(gender.label),
            'text': 'Concluded ' if done else 'Ready' if valid else 'Not ready',
        }

    event_done = not event.active_day.is_racing_day
    other_gender = utils.reverse_gender(gender)

    return {
        'main': styling(gender, crew_valid, event_done),
        'other': styling(other_gender, other_crew_valid, event_done),
        'other_gender_link': reverse(
            'fantasy:{}'.format(other_gender.label.lower()),
            kwargs = {'event_tag': event.tag},
        ),
    }


@register.inclusion_tag(template.Template('''
  <a
      href="{{ link }}"
      class="btn btn-{{ colour }} btn-sm d-flex justify-content-between"
  >
    <div>{{ text }}</div>
    <div class="ml-2"><small><span class="oi oi-chevron-right"></span></small></div>
  </a>
'''))
def crew_ready_button(event: types.AugmentedEvent, gender: Genders) -> types.CrewReadyButton:

    try:
        crew_ready = {
            Genders.MEN: event.mens_crew_ready,
            Genders.WOMEN: event.womens_crew_ready,
        }[gender]

    except AttributeError:
        action = 'to compete' if event.active_day.is_racing_day else 'for your team'
        return {
            'link': reverse('login'),
            'colour': 'primary',
            'text': f'Sign in {action}',
        }

    link = reverse(f'fantasy:{gender.label}'.lower(), kwargs = {'event_tag': event.tag})

    if not event.active_day.is_racing_day:
        return {'link': link, 'colour': 'primary', 'text': 'View final crew'}
    elif crew_ready:
        return {'link': link, 'colour': 'success', 'text': 'Ready to race'}
    elif event.active_day == event.first_day:
        return {'link': link, 'colour': 'danger', 'text': 'Entry incomplete'}
    return {'link': link, 'colour': 'danger', 'text': 'Subs required'}


@register.inclusion_tag('fantasy/event-box.html')
def event_box(event: types.AugmentedEvent, user: auth.User | auth.AnonymousUser) -> types.EventBox:
    return {'event': event, 'genders': Genders, 'user': user, 'money': money}


trophy_styles: dict[str, tuple[str, bool, bool]] = {
    models.Trophy.Types.GOLDEN_SWAN: ('gold', True, False),
    models.Trophy.Types.SILVER_SWAN: ('silver', True, False),
    models.Trophy.Types.BRONZE_SWAN: ('bronze', True, False),
    models.Trophy.Types.GOLDEN_COB: ('cob', True, False),
    models.Trophy.Types.GOLDEN_PEN: ('pen', True, False),
    models.Trophy.Types.GOLDEN_CYGNET: ('gold', False, False),
    models.Trophy.Types.STEADY_SWAN: ('silver', False, True),
    models.Trophy.Types.UGLY_DUCKLING: ('ugly', False, False),
    models.Trophy.Types.JESTER_SWAN: ('jester', False, True),
    'Top Five': ('other', True, False),
    'Top Ten': ('other', False, False),
    'Oxford': ('oxford', False, False),
    'Cambridge': ('cambridge', False, False),
}


def swan_image(trophy_type: str, tooltip: str, bottom_tooltip: bool) -> str:

    file_tag, is_large, is_reversed = trophy_styles[trophy_type]

    style_classes = ['swan-trophy', 'swan-trophy-large' if is_large else 'swan-trophy-small']
    if is_reversed:
        style_classes.append('swan-trophy-reversed')

    return '<img src="{}" class="{}" data-toggle="tooltip" data-placement="{}" title="{}" />'.format(  # noqa: E501
        static('fantasy/swan-{}.svg'.format(file_tag)),
        ' '.join(style_classes),
        'bottom' if bottom_tooltip else 'top',
        tooltip,
    )


@register.filter
def display_trophies(team: models.Team, bottom_tooltip: bool = False) -> str:

    trophy_string = ''

    for trophy in team.get_leaderboard_trophies():
        trophy_string += swan_image(trophy.type, str(trophy), bottom_tooltip)

    if not team.get_leaderboard_trophies():
        if team.top_five_finisher:
            trophy_string += swan_image('Top Five', 'Top Five Finisher', bottom_tooltip)
        elif team.top_ten_finisher:
            trophy_string += swan_image('Top Ten', 'Top Ten Finisher', bottom_tooltip)

    if team.oxford_veteran:
        trophy_string += swan_image('Oxford', 'Oxford Veteran', bottom_tooltip)
    if team.cambridge_veteran:
        trophy_string += swan_image('Cambridge', 'Cambridge Veteran', bottom_tooltip)

    return mark_safe(trophy_string)
