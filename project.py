import os, sys  # noqa: E401

args = sys.argv[1:]
if not args:
    raise IndexError('Must supply at least one argument')

commands = {
    'test': ['pytest', 'fantasy core'],
    'test:ff': ['pytest -x', 'fantasy core'],
    'test:external': ['pytest', 'integrations'],
    'type': ['mypy'],
    'lint': ['flake8'],
    'markdown': [
        'pymarkdownlnt',
        '--disable-rules=line-length',
        'scan',
        '--respect-gitignore',
        '-r',
        '.',
    ],
    'markdown:fix': [
        'pymarkdownlnt',
        '--disable-rules=line-length',
        'fix',
        '--respect-gitignore',
        '-r',
        '.',
    ],
}

command_raw = args[0]
command_parts = commands.get(command_raw, ['python manage.py {}'.format(command_raw)])
command_str = ' '.join([command_parts[0], *(args[1:] if len(args) > 1 else command_parts[1:])])
status = os.system(command_str)

raise SystemExit(bool(status))
