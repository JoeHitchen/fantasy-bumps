from django.db import migrations
from django.db.models import F
from django.apps.registry import Apps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor as SchemaEditor


def restore_top_five_finishers(apps: Apps, schema_editor: SchemaEditor) -> None:
    """Re-flags teams whose Top-Five flag was cleared by a later, Top-Ten only finish."""

    Event = apps.get_model('fantasy', 'Event')
    Team = apps.get_model('fantasy', 'Team')

    top_five_team_ids: set[int] = set()
    for event in Event.objects.all():
        top_five_team_ids.update((
            event.fantasies
            .annotate(
                total_budget = F('mens_budget') + F('womens_budget'),
                total_crew_value = (
                    F('mens_budget') - F('mens_balance') + F('womens_budget') - F('womens_balance')
                ),
            )
            .order_by('-total_budget', '-total_crew_value', 'team__user__username')
            .values_list('team_id', flat = True)[:5]
        ))

    Team.objects.filter(id__in = top_five_team_ids).update(top_five_finisher = True)


def noop(apps: Apps, schema_editor: SchemaEditor) -> None:
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('fantasy', '0027_alter_event_coaching_competition'),
    ]

    operations = [
        migrations.RunPython(restore_top_five_finishers, noop),
    ]
