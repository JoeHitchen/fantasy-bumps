from datetime import timedelta

from django import template
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe
from django.contrib.humanize.templatetags.humanize import naturalday

from ..constants import Genders
from .. import utils

register = template.Library()


@register.inclusion_tag(template.Template('''
  <div class="alert alert-{{ style }}{% if dismissable %} alert-dismissible fade show{% endif %}">
    {{ message }}
    {% if dismissable %}<button class="close" data-dismiss="alert">
      <span>&times;</span>
    </button>{% endif %}
  </div>
'''))
def market_status_box(day, allow_dismiss = True):
    """Creates the properties for an alert box that describes the market status."""
    
    # Preparation
    now = timezone.localtime()
    
    def datetime_string(datetime):
        """Generates a partially humanised datetime."""
        day_string = naturalday(datetime, 'l')
        if day_string[0:2] != 'to':
            day_string = 'on ' + day_string
        return '{:%H:%M} {}'.format(datetime, day_string)
    
    
    # While market open
    if day.market_is_open:
        return {
            'style': 'warning' if day.market_closes - now <= timedelta(hours = 6) else 'info',
            'dismissable': allow_dismiss,
            'message': 'The market is open until {}.'.format(
                datetime_string(day.market_closes),
            ),
        }
    
    
    # Held closed
    if day.event.market_held_closed:
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
def avatar(text, club = None):
    classes = 'avatar' + (' club-' + club if club else '')
    return format_html('<span class="{1} flex-shrink-0">{0}</span>', text, classes)


@register.filter
def currency(amount):
    return format_html('{}&nbsp;🦀', amount)


@register.filter
def popularity_indicator(popularity):
    return mark_safe('<span class="popularity">{:.2f}</span>'.format(popularity))


@register.inclusion_tag(template.Template('''
  <button
      class="payout btn btn-primary btn-sm flex-shrink-0"
      data-toggle="popover"
      data-placement="top"
      title="Analysis for {{ analysis_crew }}"
      data-popularity="{{ popularity|floatformat:2 }}"
      data-bump-up="{{ bump_up }}"
      data-row-over="{{ row_over }}"
      data-bumped-down="{{ bumped_down }}"
  >
    {{ popularity|floatformat:2 }}&nbsp;&nbsp;<span class="oi oi-graph"></span>
  </button>
'''))
def analysis_button(position):
    
    def delta_crabs_for_change(position_change):
        delta_crabs = utils.payout_by_day_gender_positions(
            position.day,
            position.crew.gender,
            position.rank,
            position.rank - position_change,
        )
        return delta_crabs['value_change'] + delta_crabs['payout']
    
    bump_up = delta_crabs_for_change(+1) if not position.rank == 1 else 0
    row_over = delta_crabs_for_change(0)
    bumped_down = (
        delta_crabs_for_change(-1)
        if not position.rank == position.day.event.num_crews(position.crew.gender)
        else 0
    )
    
    return {
        'analysis_crew': position.crew,
        'popularity': position.popularity,
        'bump_up': '{:+d}'.format(bump_up),
        'row_over': '{:+d}'.format(row_over),
        'bumped_down': '{:+d}'.format(bumped_down),
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
def mini_leaderboard_row(rank, fantasy, event):
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
def popularity_row(rank, crew):
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
def buy_button(position, disabled = False):
    return {
        'day': position.day,
        'crew': position.crew,
        'crew_value': utils.pricing_by_day_gender(
            position.rank,
            position.day,
            position.crew.gender,
        ),
        'disabled': ' disabled' if disabled else '',
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <button class="btn btn-primary btn-sm btn-sell flex-shrink-0" data-purchase="{{ purchase.id }}">
    Sell {{ crew_value|currency }}
  </button>
'''))
def sell_button(purchase):
    price = purchase.price if hasattr(purchase, 'price') else purchase.crew.value(purchase.day)
    return {'purchase': purchase, 'crew_value': price}


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
def switch_button(purchase):
    return {'purchase': purchase}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group-item market-row">
    {{ position.bungline|avatar:position.crew.club }}
    <div class="flex-grow-1">{{ position.crew }}</div>
    {% analysis_button position %}
    {% if show_actions %}
    {% buy_button position disabled %}{% endif %}
  </div>
'''))
def market_row(position, balance, show_actions):
    
    crew_value = utils.pricing_by_day_gender(
        position.rank,
        position.day,
        position.crew.gender,
    )
    
    disabled = show_actions and crew_value > balance
    
    return {
        'position': position,
        'disabled': disabled,
        'show_actions': show_actions,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group mb-3">
    <div class="list-group-item list-group-item-dark market-row">
      <h5 class="mb-0">{{ gender.label }}'s Division {{ number }}</h5>
    </div>
    {% for position in division %}{% market_row position balance show_actions %}{% endfor %}
  </div>
'''))
def market_division_box(division, gender, number, balance, show_actions):
    return {
        'division': division,
        'gender': gender,
        'number': number,
        'balance': balance,
        'show_actions': show_actions,
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
def crew_list_header(finances):
    return {
        'budget': finances['budget'],
        'crew_value': finances['crew_value'],
        'balance': finances['balance'],
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group-item{% if not purchase %} list-group-item-danger{% endif %} crew-row">
    {{ seat.short|avatar:club }}
    {% if purchase %}
    <div class="flex-grow-1{% if purchase.athlete %} crew-row-athlete{% endif %}">
      {% if purchase.athlete %}<div>{{ purchase.athlete }}</div>{% endif %}
      <div>{{ purchase.crew }}</div>
    </div>
    {% if show_actions %}
      {% switch_button purchase %}
      {% sell_button purchase %}
    {% endif %}
    {% endif %}
  </div>
'''))
def crew_list_row(seat, purchase, show_actions):
    return {
        'seat': seat,
        'purchase': purchase,
        'club': purchase.crew.club if purchase else None,
        'show_actions': show_actions,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  {% if finances %}
    {% crew_list_header finances %}
  {% endif %}
  {% for seat, rower in crew_list %}
    {% crew_list_row seat rower show_actions %}
  {% endfor %}
'''))
def crew_list_box(crew_list, seats, finances = None, show_actions = False):
    seat_rowers = {seat: [
        rower for rower in crew_list if rower.seat == seat
    ] for seat in seats}
    
    crew_list = [(
        seat,
        rowers[0] if rowers else None,
    ) for seat, rowers in seat_rowers.items()]
    
    return {'crew_list': crew_list, 'finances': finances, 'show_actions': show_actions}


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
def crew_status_box(event, gender, crew_valid, other_crew_valid):

    def styling(gender, valid):
        return {
            'colour': 'success' if valid else 'danger',
            'crew': "{}'s crew".format(gender.label),
            'text': 'Ready' if valid else 'Not ready',
        }
    
    other_gender = utils.reverse_gender(gender)
    
    return {
        'main': styling(gender, crew_valid),
        'other': styling(other_gender, other_crew_valid),
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
def crew_ready_button(event, gender):
    
    try:
        crew_ready = {
            Genders.MEN: event.mens_crew_ready,
            Genders.WOMEN: event.womens_crew_ready,
        }[gender]
    
    except AttributeError:
        action = 'compete' if event.active_day.first_race else 'view your results'
        return {
            'link': reverse('login'),
            'colour': 'primary',
            'text': f'Sign in to {action}',
        }
    
    if not event.active_day.first_race:
        styles = {'colour': 'primary', 'text': 'View final crew'}
    elif crew_ready:
        styles = {'colour': 'success', 'text': 'Ready to race'}
    elif event.active_day == event.first_day:
        styles = {'colour': 'danger', 'text': 'Entry incomplete'}
    else:
        styles = {'colour': 'danger', 'text': 'Subs required'}
    
    return {
        'link': reverse(f'fantasy:{gender.label}'.lower(), kwargs = {'event_tag': event.tag}),
        **styles,
    }


@register.inclusion_tag('fantasy/event-box.html')
def event_box(event, user):
    return {'event': event, 'genders': Genders, 'user': user}

