# Fantasy Bumps

A prediction and speculation game for Oxford bumps racing.
Hosted live at [fantasybumps.org.uk](https://fantasybumps.org.uk/)

## Running Fantasy Bumps

Fantasy Bumps provides various Django management commands for running games.
These should be triggered using the form `python project.py ...` on a system with `uv` installed.

The first is:

```bash
init [--dev-team]
```

This migrates the database, loads constant fixtures such as seats data.
If the `--dev-team` flag is set, also loads a user account for development use, with the credentials:

- Username: `DevTeam`  
- Password: `password`

### Game Creation

The most important command is the `game_start` command.
This is used to create new competitions and takes the form:

```bash
game_start [--date <yyyy-mm-dd> | --year <yyyy>] [--source <source>] [--crew-lists <source>] [--coaching <competition>] {torpids|eights|lents|mays|demo}
```

By default, the event will start in five days' time, and use data from the current year.

- `--date` can be used to change the start date of the event.
- `--year` can be used to set up the event using results from past years, but cannot be used in conjunction with `--date`.
- `--source` is used to change the start order source for the event.
  The default sources are LiveBumps for Oxford and CamFM for Cambridge.
- `--crew-lists` does the same for crew list information.
  The default source is LiveBumps again for Oxford and crew lists are not available for Cambridge.
- `--coaching` is used to set the coaching competition for the event.

### Game Advances

Game advances are the act whereby payouts are awarded after each day of racing and the player purchases are rolled over for the next day of trading.
When the game is started, advances are automatically scheduled for 50 minutes after the last race each day.
They can also be triggered by invoking:

```bash
game_advance [--forced] [--override]
```

A game advance will be aborted if the `market_held_closed` flag has been set in response to (or anticipation of) technical difficulties, with the same flag also holding markets closed indefinitely.
The `--override` flag bypasses this block on game advancement, and allows it to proceed as normal.
It should NOT be set in any automation and should only be used as part of recovery efforts.

The `--forced` flag is intended for development and shifts the entire event one day earlier, simulating 24 hours having passed, as well as performing a standard advance.

### Renumbered Crews

If crews are renumbered and race the main event with a different crew number to their original entry, the system will not be able to auto-detect this and the crew lists displayed will be incorrect.
This can be resolved by running:

```bash
renumbered_crew <event_tag> <club> <gender> <new_rank> <old_rank> [--source <source>]
```

Where `new_rank` is the number that the crew now hold and `old_rank` is the number that the crew were originally entered under.
Note that if crews have _swapped_ numbers, this command must be run twice; once in each direction.

### Live Bumps Updates

Fantasy Bumps also acts as the data pipeline for Oxford [Live Bumps](https://bumps.live/), using data provided by Anu Dudhia.
This is also primarily operated on an automatic task schedule, but two commands are provided for manual usage:

- `update_live_bumps <series> <year> <gender>` reads the latest data for one gender from Anu's sources and pushes it to Live Bumps for display.
- `wipe_live_bumps <series> <year>` removes all results data for both sides of event from Live Bumps, but does not remove/reset the initial start order.

## Development

### Development Setup

Local development requires Python 3.14+ and [`uv`](https://docs.astral.sh/uv/).

Install all dependencies (including development tools) and install the pre-commit checks with:

```bash
uv sync --all-groups
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

If needed, the pre-commit & pre-push hooks can be validated with

``` bash
uv run pre-commit run --all-files --hook-stage pre-commit
uv run pre-commit run --all-files --hook-stage pre-push
```

### Project Commands & QA Suite

The project provides the `project.py` interface for interacting with project tooling and pre-defined QA suite.
This will run all commands within the appropriate `uv` environment, but does not itself need to be invoked using `uv`.

| Command | Effect |
| ------- | ------ |
| `python project.py markdown` | Run markdown format checking |
| `python project.py markdown:fix` | Check & fix markdown formatting issues* |
| `python project.py lint` | Run flake8 code linting |
| `python project.py type` | Run mypy type checking |
| `python project.py test` | Run pytest on main project modules |
| `python project.py test:ff` | Run tests, stopping on first failure |
| `python project.py test:external` | Run tests on external integrations |
| `python project.py dump_database FILENAME` | Back up all users and app data to a JSON fixture |
| `python project.py <command> [args]` | Run any standard Django management command, including `migrate`, `runserver`, and others. |

\* Note that support for actual fixes is limited.

## Dependency Management

Dependencies are defined in `pyproject.toml` with the following groups:

| Group | Purpose | Install |
| ------- | --------- | --------- |
| Main | Runtime application dependencies | `uv sync` |
| `markdown` | Markdown checking tools | `uv sync --group-only markdown` |
| `linting` | Code style/format tooling | `uv sync --group-only linting` |
| `typing` | Type check evaluation | `uv sync --group-only typing` |
| `testing` | Test framework and plugins | `uv sync --group testing` |
| `dev` | Pre-commit itself | `uv sync --group-only dev` |
| All | All runtime & development dependencies | `uv sync --all-groups` |

N.B. The `testing` group is a dynamic check, so it also requires the full set of project installs, unlike the other groups/toolsets which are static checks.

## Docker & Deployment

The application is containerised for production deployment, with the image build defined in the project `Dockerfile`.
Note that dependency installations are inexact due to non-development dependencies (e.g. `gunicorn`, `mysqlclient`, `boto3`) being installed directly in the build process rather than defined in the application.

The application image is built automatically in the GitHub workflow when there is a push to `development`, `master` or `deploy` and the baseline QA checks have passed.
As well as building the container, the workflow verifies that the tests run correctly within the container, and that the production services start correctly.
A push to `deploy` will also publish the built image to Docker Hub, if the runtime checks pass.

The three commands used in production to run application containers are:

| Service | Command |
| ------- | ------- |
| Server | `gunicorn core.wsgi:application --bind 0.0.0.0:8000 --logger-class overrides.GunicornLogger` |
| Scheduler | `celery --app=core beat --loglevel=info` |
| Worker | `celery --app=core worker --loglevel=info` |
