import os, sys  # noqa: E401

args = sys.argv[1:]
if not args:
    raise IndexError('Must supply at least one argument')

commands = {
    'test': ('uv run pytest', 'fantasy core'),
    'test:ff': ('uv run pytest -x', 'fantasy core'),
    'test:external': ('uv run pytest', 'integrations'),
    'type': ('uv run mypy', ''),
    'lint': ('uv run flake8 --extend-exclude .venv,venv', ''),
    'markdown': ('uv run pymarkdownlnt --disable-rules=line-length scan --respect-gitignore -r', '.'),
    'markdown:fix': ('uv run pymarkdownlnt --disable-rules=line-length fix --respect-gitignore -r', '.'),
}

command_raw = args[0]

if command_raw in commands:
    cmd, default_args = commands[command_raw]
    if len(args) > 1:
        # User provided arguments - replace defaults with user args
        command_str = ' '.join([cmd, *args[1:]])
    else:
        # Use default arguments
        command_str = ' '.join([cmd, default_args]) if default_args else cmd
else:
    # Unknown command - pass to Django manage.py
    command_str = 'python manage.py {}'.format(command_raw)

status = os.system(command_str)

raise SystemExit(bool(status))
