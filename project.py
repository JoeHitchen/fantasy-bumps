import os, sys  # noqa: E401

args = sys.argv[1:]
if not args:
    raise IndexError('Must supply at least one argument')

commands = {
    'test': ['python manage.py test --pattern=*tests.py', 'fantasy core'],
    'test:ff': ['python manage.py test --pattern=*tests.py --fastfail', 'fantasy core'],
    'test:external': ['python -m unittest', 'integrations.tests'],
    'type': ['mypy'],
    'lint': ['flake8'],
    'worker': ['python manage.py qcluster'],
}

command = args[0]
command = commands.get(command, ['python manage.py {}'.format(command)])
command = ' '.join([command[0], *(args[1:] if len(args) > 1 else command[1:])])
status = os.system(command)

raise SystemExit(bool(status))
