import os, sys  # noqa: E401

args = sys.argv[1:]
if not args:
    raise IndexError('Must supply at least one argument')

commands = {
    '_test': 'python manage.py test --pattern=*tests.py',
    'test': 'python project.py _test --exclude=external',
    'test:ff': 'python project.py _test --exclude=external --failfast',
    'test:external': 'python project.py _test --tag=external',
    'lint': 'flake8',
}

command = args[0]
command = commands.get(command, 'python manage.py {}'.format(command))
command = ' '.join([command, *args[1:]])
status = os.system(command)

raise SystemExit(bool(status))
