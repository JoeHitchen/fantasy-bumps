# Fantasy Bumps

A prediction and speculation game for Oxford bumps racing.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python package management.

### Installation

1. Install [uv](https://docs.astral.sh/uv/#getting-started) if you haven't already.

2. Sync project dependencies:

   ```bash
   uv sync
   ```

   This installs all main dependencies needed to run the application. For development, you can install additional tool groups:

   ```bash
   uv sync --all-groups  # Includes linting, testing, and type-checking tools
   ```

3. Initialize the application:

   ```bash
   python project.py init [--dev-team]
   ```

   This command migrates the database and installs fixed data (such as seat values).
With the `--dev-team` flag, a user/team can also be loaded for development.

   > Default credentials when using `--dev-team`:
   >
   > - Username: DevTeam
   > - Password: password

## Running Games

Games are created with:

```bash
python project.py game_start --eights | --torpids | --demo [--date YYYY-MM-DD | --year YYYY]
```

Where:

- The first flag (e.g., `--torpids`, `--eights`) indicates which series the event belongs to
- `--demo` uses fixed data for demonstration/testing (requires an empty database)
- By default, events start in five days; override with `--date` flag
- Use `--year` flag to create an event using data from a previous year
- The `--date` and `--year` flags cannot be used simultaneously

Games are advanced with:

```bash
python project.py game_advance [--forced]
```

A `cron` job should be scheduled to run this after racing ends but before market open/day tickover (8pm typical).
With the `--forced` flag, development/demonstration games progress faster.

## Development

### Project Commands

This project provides useful commands via `project.py`. Run commands with:

```bash
python project.py <command> [args]
```

Available commands include:

- `test` - Run pytest on core and fantasy modules
- `test:ff` - Run tests, stopping on first failure
- `test:external` - Run tests on integrations
- `type` - Run mypy type checking
- `lint` - Run flake8 code linting
- `markdown` - Check markdown files
- `markdown:fix` - Fix markdown formatting issues
- Plus any Django management command: `python project.py <manage.py command>`

All commands execute via `uv run`, ensuring they use the synced dependencies.

### Development Setup

For local development, install all dependencies including development tools:

```bash
uv sync --all-groups
```

This includes:

- **Testing**: pytest and pytest-django
- **Linting**: flake8 and plugins (style, import order, comprehensions, etc.)
- **Type Checking**: mypy and type stubs for Django, Celery, and other packages
- **Markdown**: pymarkdownlnt for documentation validation

### Example Workflows

Start a development game and advance it 24 hours:

```bash
python project.py devgame:start
python project.py devgame:advance
```

Create a development user/team:

```bash
python project.py loaddata dev_team
```

Run quality checks before committing:

```bash
python project.py lint     # Code style
python project.py type     # Type checking
python project.py markdown # Documentation
python project.py test     # Unit tests
```

## Dependency Management

Dependencies are defined in `pyproject.toml` with the following groups:

| Group | Purpose | Install |
|-------|---------|---------|
| Main | Runtime application dependencies | `uv sync` |
| `linting` | Code quality and markdown tools | `uv sync --group linting` |
| `testing` | Test framework and plugins | `uv sync --group testing` |
| `typing` | Type checking and stubs | `uv sync --group typing` |
| `dev` | All development tools combined | `uv sync --group dev` |

For quick development setup, use:

```bash
uv sync --all-groups  # Installs all optional groups
```

## Docker

The application is containerized for production deployment. The Docker image:

- Uses Python 3.14 on Alpine Linux for minimal size
- Installs dependencies via `uv` with frozen lock file for reproducibility
- Runs gunicorn on port 8000

Build the image locally:

```bash
docker build -t fantasy-bumps .
```

Run the container:

```bash
docker run -p 8000:8000 fantasy-bumps
```

## CI/CD

GitHub Actions workflows automate quality checks and deployments:

- **Quality Control**: Runs on every push
  - Markdown linting
  - Code linting (flake8)
  - Type checking (mypy)
  - Unit testing (pytest)

- **Build & Publish**: Runs on successful QC when pushing to `deploy` branch
  - Builds Docker image
  - Verifies image with internal tests
  - Pushes to Docker Hub registry
