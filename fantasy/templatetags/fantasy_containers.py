from typing import Any

from django import template

from fantasy import models


register = template.Library()


@register.tag(name = 'crew_list_row')
def do_crew_list_row(parser: Any, token: Any) -> 'CrewListRowNode':
    token_contents = token.split_contents()
    inner_content = parser.parse(('end_crew_list_row',))
    parser.delete_first_token()
    return CrewListRowNode(
        seat = token_contents[1],
        purchase_or_crew = token_contents[2],
        name = token_contents[3] if len(token_contents) > 3 else None,
        inner_content = inner_content,
    )


class CrewListRowNode(template.Node):
    def __init__(self, seat: Any, purchase_or_crew: Any, name: Any, inner_content: Any) -> None:

        self.seat = template.Variable(seat)
        self.purchase_or_crew = template.Variable(purchase_or_crew)
        self.name = template.Variable(name) if name else None
        self.inner_content = inner_content

    def render(self, context: Any) -> str:

        seat = self.seat.resolve(context)
        purchase_or_crew = self.purchase_or_crew.resolve(context)
        name = self.name.resolve(context) if self.name else None

        crew = None
        if isinstance(purchase_or_crew, models.Purchase):
            crew = purchase_or_crew.crew
            name = purchase_or_crew.athlete
        elif isinstance(purchase_or_crew, models.Crew):
            crew = purchase_or_crew

        classes = ['list-group-item', 'crew-row']
        if not crew:
            classes.insert(1, 'list-group-item-danger')

        return template.Template('''
            {% load fantasy_tags %}
            <div class="''' + ' '.join(classes) + '''">
                {{ seat|avatar:club }}
                {% if crew %}
                <div class="flex-grow-1{% if name %} crew-row-athlete{% endif %}">
                  {% if name %}<div>{{ name }}</div>{% endif %}
                  <div>{{ crew }}</div>
                </div>
                {{ inner_content|safe }}
                {% endif %}
            </div>
        ''').render(template.Context({
            'seat': seat.short if isinstance(seat, models.Seat) else seat,
            'crew': crew,
            'name': name,
            'club': crew and crew.club,
            'inner_content': self.inner_content.render(context),
        }))


