from datetime import timedelta

from django import template
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe
from django.contrib.humanize.templatetags.humanize import naturalday

from ..constants import Genders
from .. import models
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
    now = timezone.now()
    
    def datetime_string(datetime):
        """Generates a partially humanised datetime."""
        return '{:%H:%M} {}'.format(datetime, naturalday(datetime, 'd/m/Y'))
    
    
    # While market open
    if day.market_is_open:
        return {
            'style': 'warning' if day.market_closes - now <= timedelta(hours = 6) else 'info',
            'dismissable': allow_dismiss,
            'message': 'The market is open until {}.'.format(
                datetime_string(day.market_closes),
            ),
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
    return format_html('<span class="{1}">{0}</span>', text, classes)


@register.filter
def currency(amount):
    return format_html('{}&nbsp;🦀', amount)


@register.filter
def popularity_indicator(popularity):
    return mark_safe('<span class="popularity">{:.2f}</span>'.format(popularity))


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
    class="btn btn-primary btn-sm btn-buy{{ disabled }}"
    {% if not disabled %}data-day="{{ day.id }}" data-crew="{{ crew.id }}"{% endif %}
  >
    Buy {{ crew_value|currency }}
  </button>
'''))
def buy_button(position, disabled = False):
    return {
        'day': position.day,
        'crew': position.crew,
        'crew_value': utils.pricing_by_day_and_gender(
            position.rank,
            position.day,
            position.crew.gender,
        ),
        'disabled': ' disabled' if disabled else '',
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <button class="btn btn-primary btn-sm btn-sell" data-purchase="{{ purchase.id }}">
    Sell {{ crew_value|currency }}
  </button>
'''))
def sell_button(purchase):
    return {'purchase': purchase, 'crew_value': purchase.crew.value(purchase.day)}


@register.inclusion_tag(template.Template('''
  {% load static %}
  {% if not purchase.seat.cox %}
    <a href="{% url 'fantasy:switch' purchase.id %}" class="btn btn-sm btn-primary">
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
    {{ position.popularity|popularity_indicator }}
    {% if show_actions %}<span style="width: 1em">&nbsp;</span>
    {% buy_button position disabled %}{% endif %}
  </div>
'''))
def market_row(position, balance, show_actions):
    
    crew_value = utils.pricing_by_day_and_gender(
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
  <div class="list-group">
    <div class="list-group-item list-group-item-dark">
      {{ gender.label }}'s Division {{ number }}
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
  <div class="list-group-item list-group-item-dark">
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
  <div>
    {% if finances %}
      {% crew_list_header finances %}
    {% endif %}
    {% for seat, rower in crew_list %}
      {% crew_list_row seat rower show_actions %}
    {% endfor %}
  </div>
'''))
def crew_list_box(crew_list, finances = None, show_actions = False):
    seat_rowers = {seat: [
        rower for rower in crew_list if rower.seat == seat
    ] for seat in models.Seat.objects.all()}
    
    crew_list = [(
        seat,
        rowers[0] if rowers else None,
    ) for seat, rowers in seat_rowers.items()]
    
    return {'crew_list': crew_list, 'finances': finances, 'show_actions': show_actions}


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
        return {
            'link': reverse('login'),
            'colour': 'primary',
            'text': 'Sign in to compete',
        }
    
    if crew_ready:
        styles = {'colour': 'success', 'text': 'Ready to race'}
    elif event.active_day == event.first_day:
        styles = {'colour': 'danger', 'text': 'Entry incomplete'}
    elif not event.active_day.first_race:
        styles = {'colour': 'primary', 'text': 'View final crew'}
    else:
        styles = {'colour': 'danger', 'text': 'Subs required'}
    
    return {
        'link': reverse(f'fantasy:{gender.label}'.lower(), kwargs = {'event_tag': event.tag}),
        **styles,
    }

