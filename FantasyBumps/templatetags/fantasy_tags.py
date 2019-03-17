from django.utils.html import format_html

from external import models as ext


def seat_avatar(seat):
    text = seat.short if isinstance(seat, ext.Seat) else 'E'
    return format_html('<span class="seat-avatar">{}</span>', text)

