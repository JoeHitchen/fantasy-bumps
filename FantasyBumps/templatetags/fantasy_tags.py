from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import naturalday

from .. import models

register = template.Library()


@register.inclusion_tag(template.Template('''
  <div class="alert alert-{{ style }}{% if dismissable %} alert-dismissible fade show{% endif %}">
    {{ message }}
    {% if dismissable %}<button class="close" data-dismiss="alert">
      <span>&times;</span>
    </button>{% endif %}
  </div>
'''))
def market_status_box(day):
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
            'dismissable': True,
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
    return format_html('<span class="currency">₢ {}</span>', amount)


@register.filter
def value(crew, day):
    return currency(crew.value(day))


@register.filter
def results_item(places, default_align):
    
    if not places:
        text = format_html('&minus;')
        background = 'bg-warning'
        align = 'text-center'
    elif places > 0:
        text = format_html('&plus;{}', places)
        background = 'bg-success'
        align = default_align
    else:
        text = format_html('&minus;{}', -places)
        background = 'bg-danger'
        align = default_align
    
    return format_html(
        '<div class="{1} {2} font-weight-bold">&nbsp;{0}&nbsp;</div>',
        text, background, align,
    )


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="results-pill row">
    {{ results.week|results_item:'text-right' }}
    <div class="bg-dark"></div>
    {{ results.yesterday|results_item:'text-left' }}
  </div>
'''))
def results_pill(results):
    return {'results': results}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <button
    class="btn btn-primary btn-sm btn-buy{{ disabled }}"
    {% if not disabled %}data-day="{{ day.id }}" data-crew="{{ crew.id }}"{% endif %}
  >
    Buy {{ crew|value:day }}
  </button>
'''))
def buy_button(day, crew, disabled = False):
    return {'day': day, 'crew': crew, 'disabled': ' disabled' if disabled else ''}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <button class="btn btn-primary btn-sm btn-sell" data-purchase="{{ purchase.id }}">
    Sell {{ purchase.crew|value:purchase.day }}
  </button>
'''))
def sell_button(purchase):
    return {'purchase': purchase}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group-item market-row">
    {{ position.bungline|avatar:position.crew.club }}
    <div class="flex-grow-1">{{ position.crew }}</div>
    {% results_pill results %}
    {% if show_actions %}{% buy_button position.day position.crew disabled %}{% endif %}
  </div>
'''))
def market_row(position, balance, show_actions):
    disabled = show_actions and position.crew.value(position.day) >= balance
    results = position.crew.results(position.day)
    return {
        'position': position,
        'disabled': disabled,
        'show_actions': show_actions,
        'results': results,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group">
    <div class="list-group-item list-group-item-dark">
      {{ gender }}'s Division {{ number }}
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
  <div class="list-group-item{% if not purchase %} list-group-item-danger{% endif %} crew-row">
    {{ seat.short|avatar:club }}
    {% if purchase %}
    <div class="flex-grow-1">{{ purchase.crew }}</div>
    {% if show_actions %}{% sell_button purchase %}{% endif %}
    {% endif %}
  </div>
'''))
def crew_row(seat, purchase, show_actions):
    return {
        'seat': seat,
        'purchase': purchase,
        'club': purchase.crew.club if purchase else None,
        'show_actions': show_actions,
    }


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <div class="list-group sticky-top">
    <div class="list-group-item list-group-item-dark">
      <div class="container"><div class="row justify-content-between">
        <span>Crew Value: {{ finances.crew_value|currency }}</span>
        <span>Cash: {{ finances.balance|currency }}</span>
      </div></div>
    </div>
    {% for seat, rower in crew %}
      {% crew_row seat rower show_actions %}
    {% endfor %}
  </div>
'''))
def crew_list_box(crew, finances):
    seat_rowers = {seat: [
        rower for rower in crew if rower.seat == seat
    ] for seat in models.Seat.objects.all()}
    
    crew = [(
        seat,
        rowers[0] if rowers else None,
    ) for seat, rowers in seat_rowers.items()]
    
    return {'crew': crew, 'finances': finances}

