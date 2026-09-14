from typing import Any, Protocol, cast
from urllib.parse import urlencode

from mcp_server import MCPToolset
from django.http import QueryDict

from fantasy.constants import GENDERS_OVERALL, Series, Genders
from fantasy import models, views


class _EventJsonView(Protocol):
    """The subset of an `EventBase` view needed to render it to JSON."""

    def __init__(self, **kwargs: Any) -> None:
        ...

    def get_context_data(self) -> views.ContextDict:
        ...

    def convert_to_json(self, context: views.ContextDict) -> views.JsonOutput:
        ...


class FantasyBumpsMCP(MCPToolset):
    """A basic MCP for Fantasy Bumps, mirroring the behaviour of the read-only JSON API"""

    def _get_event_json(
        self,
        view_class: type[_EventJsonView],
        series: Series,
        year: int,
        view_kwargs: dict[str, Any] | None = None,
        get_params: dict[str, str] | None = None,
    ) -> views.JsonOutput:
        """Builds a request for an event view and returns its JSON representation."""

        assert self.request is not None  # Needed for MyPy
        if get_params is not None:
            self.request.GET = QueryDict(urlencode(get_params))

        view = view_class(
            object = models.Event.objects.get(series=series, year=year),
            kwargs = view_kwargs or {},
            request = self.request,
        )
        return view.convert_to_json(view.get_context_data())


    def list_events(self) -> list[views.JsonOutput]:
        """Retrieve a list of all events."""

        assert self.request is not None  # Needed for MyPy
        view = views.IndexView(request = self.request)

        return cast(
            list[views.JsonOutput],
            view.convert_to_json(view.get_context_data())['events'],
        )


    def get_event_details(self, series: Series, year: int) -> views.JsonOutput:
        """Retrieve details and crew popularity for an event, using the series and year."""
        return self._get_event_json(views.EventView, series, year)


    def get_event_market(self, series: Series, year: int, gender: Genders) -> views.JsonOutput:
        """Retrieve current market information for an event, using the series, year, and gender -
        including start order, prices, popularity, and possible payouts."""
        return self._get_event_json(
            views.MarketView,
            series,
            year,
            view_kwargs = {'gender': gender},
        )


    def get_event_leaderboard(
        self,
        series: Series,
        year: int,
        gender: Genders | None = None,
        invalid_entries: bool = True,
        allow_subs: bool = True,
        returners: bool = True,
    ) -> views.JsonOutput:
        """Retrieve the leaderboard data for a given series, year, and set of filters.

        - gender (when specified) ranks teams by their men's or women's performance.
        - gender (when omitted) ranks teams by overall performance (men & women combined).

        - invalid_entries (when false) excludes teams with an incomplete entry on their first day.
        - allow_subs (when false) excludes teams that have used a substitute athlete.
        - returners (when false) excludes teams that entered a previous event.

        The default behaviour is to sort by the overall ranking and include all teams."""
        return self._get_event_json(
            views.LeaderboardView,
            series,
            year,
            view_kwargs = {'gender': gender or GENDERS_OVERALL},
            get_params = {
                'invalid-entries': 'true' if invalid_entries else 'false',
                'allow-subs': 'true' if allow_subs else 'false',
                'returners': 'true' if returners else 'false',
            },
        )


    def get_event_team_crews(self, series: Series, year: int, team_name: str) -> views.JsonOutput:
        """Retrieve crew lists, finances, and payouts for a team's entry to an event,
        using the series, year, and team name."""
        return self._get_event_json(
            views.TeamView,
            series,
            year,
            view_kwargs = {'team_name': team_name},
        )

