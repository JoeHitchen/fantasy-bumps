from django import template
from django.utils.html import format_html

from external import models as ext

register = template.Library()


@register.filter
def bungline_avatar(bungline):
    text = bungline if isinstance(bungline, int) else 'E'
    return format_html('<span class="bungline-avatar">{}</span>', text)


@register.inclusion_tag(template.Template(
    '<tr>\n'
    '  <td>{{ bungline }}</td>\n'
    '  <td>{{ tag_crew }}</td>\n'
    '  <td>£100</td>\n'
    '  <td><a href="{% url \'fantasybumps:buy\' %}" class="btn btn-sm btn-primary">Buy</a></td>\n'
    '</tr>\n',
))
def market_division_row(bungline, crew):
    return {'bungline': bungline, 'tag_crew': crew}


@register.inclusion_tag(template.Template(
    '{% load fantasy_tags %}\n'
    '<table class="table table-sm table-bordered table-hover">'
    '  <thead class="thead-dark">'
    '    <tr><th colspan="4">{{ gender }}\'s Division {{ number }}</th></tr>'
    '  </thead>'
    '  <tbody>'
    '  {% for position in division %}'
    '    {% market_division_row forloop.counter position.crew %}'
    '  {% endfor %}'
    '  </tbody>'
    '</table>',
))
def market_division_box(division, gender, number):
    return {'division': division, 'gender': gender, 'number': number}


@register.filter
def seat_avatar(seat):
    text = seat.short if isinstance(seat, ext.Seat) else 'E'
    return format_html('<span class="seat-avatar">{}</span>', text)


@register.inclusion_tag(template.Template(
    '{% load fantasy_tags %}\n'
    '<tr class="table-{% if rower %}primary{% else %}danger{% endif %}">\n'
    '  <td>{{ seat|seat_avatar }}</td>\n'
    '  <td>{% if rower %}{{ rower.crew }}{% else %}Empty{% endif %}</td>\n'
    '</tr>\n',
))
def crew_list_row(seat, rower):
    return {'seat': seat, 'rower': rower}


@register.inclusion_tag(
    template.Template(
        '{% load fantasy_tags %}\n'
        '<table class="table table-sm table-bordered table-hover">\n'
        '  <thead class="thead-dark">\n'
        '    <tr><th colspan="2">Your crew</th></tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        '  {% for seat, rower in crew %}'
        '    {% crew_list_row seat rower %}'
        '  {% endfor %}\n'
        '  </tbody>\n'
        '  <tfoot>\n'
        '    <tr class="table-{% if crew_valid %}success{% else %}danger{% endif %}">\n'
        '      <th colspan="2">\n'
        '        This crew is {% if not crew_valid %}not {% endif %}ready to race.\n'
        '      </th>\n'
        '    </tr>\n'
        '    <tr class="table-{% if other_crew_valid %}success{% else %}danger{% endif %}">'
        '      <th colspan="2">\n'
        '        Your other crew is {% if not other_crew_valid %}not {% endif %}ready to race.'
        '      </th>\n'
        '    </tr>\n'
        '  </tfoot>\n'
        '</table>\n',
    ),
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

