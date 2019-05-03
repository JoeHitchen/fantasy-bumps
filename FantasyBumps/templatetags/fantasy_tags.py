from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import naturalday

from external import models as ext

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
    future_open = day.market_opens if now < day.market_opens else None
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
def bungline_avatar(bungline):
    text = bungline if isinstance(bungline, int) else 'E'
    return format_html('<span class="bungline-avatar">{}</span>', text)


@register.inclusion_tag(template.Template('''
  <tr>
    <td>{{ bungline }}</td>
    <td>{{ tag_crew }}</td>
    <td>£100</td>
    <td><a href="{% url \'fantasybumps:buy\' %}" class="btn btn-sm btn-primary">Buy</a></td>
  </tr>
'''))
def market_division_row(bungline, crew):
    return {'bungline': bungline, 'tag_crew': crew}


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <table class="table table-sm table-bordered table-hover">
    <thead class="thead-dark">
      <tr><th colspan="4">{{ gender }}\'s Division {{ number }}</th></tr>
    </thead>
    <tbody>
    {% for position in division %}
      {% market_division_row forloop.counter position.crew %}
    {% endfor %}
    </tbody>
  </table>
'''))
def market_division_box(division, gender, number):
    return {'division': division, 'gender': gender, 'number': number}


@register.filter
def seat_avatar(seat):
    text = seat.short if isinstance(seat, ext.Seat) else 'E'
    return format_html('<span class="seat-avatar">{}</span>', text)


@register.inclusion_tag(template.Template('''
  {% load fantasy_tags %}
  <tr class="table-{% if rower %}primary{% else %}danger{% endif %}">
    <td>{{ seat|seat_avatar }}</td>
    <td>{% if rower %}{{ rower.crew }}{% else %}Empty{% endif %}</td>
    <td>
      <a href="{% url \'fantasybumps:sell\' %}" class="btn btn-sm btn-primary">Sell</a>
    </td>
  </tr>
'''))
def crew_list_row(seat, rower):
    return {'seat': seat, 'rower': rower}


@register.inclusion_tag(
    template.Template('''
      {% load fantasy_tags %}
      <table class="table table-sm table-bordered table-hover">
        <thead class="thead-dark">
          <tr><th colspan="3">Your crew</th></tr>
        </thead>
        <tbody>
        {% for seat, rower in crew %}
          {% crew_list_row seat rower %}
        {% endfor %}
        </tbody>
        <tfoot>
          <tr class="table-{% if crew_valid %}success{% else %}danger{% endif %}">
            <th colspan="3">
              This crew is {% if not crew_valid %}not {% endif %}ready to race.
            </th>
          </tr>
          <tr class="table-{% if other_crew_valid %}success{% else %}danger{% endif %}">
            <th colspan="3">
              Your other crew is {% if not other_crew_valid %}not {% endif %}ready to race.
            </th>
          </tr>
        </tfoot>
      </table>
    '''),
    takes_context = True,
)
def crew_list_box(context):
    seat_rowers = {seat: [
        rower for rower in context['crew'] if rower.seat == seat
    ] for seat in ext.Seat.objects.all()}
    
    context['crew'] = [(
        seat,
        rowers[0] if rowers else None,
    ) for seat, rowers in seat_rowers.items()]
    
    return context

