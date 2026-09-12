import os, sys  # noqa: E401

args = sys.argv[1:]
if not args:
    raise IndexError('Must supply at least one argument')

commands = {
    'test': ('uv run pytest', 'fantasy core'),
    'test:ff': ('uv run pytest -x', 'fantasy core'),
    'test:external': ('uv run pytest', 'integrations'),
    'type': ('uv run mypy', ''),
    'lint': ('uv run flake8', ''),
    'markdown': ('uv run pymarkdownlnt scan -r', '.'),
    'markdown:fix': ('uv run pymarkdownlnt fix -r', '.'),
}

command_raw = args[0]
command_parts = commands.get(command_raw, ('uv run python manage.py {}'.format(command_raw), ''))
command_str = ' '.join([command_parts[0], *(args[1:] if len(args) > 1 else command_parts[1:])])
status = os.system(command_str)

raise SystemExit(bool(status))
