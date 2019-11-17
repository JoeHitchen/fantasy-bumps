import os, sys  # noqa: E401

args = sys.argv[1:]
if not args:
    raise IndexError('Must supply at least one argument')

commands = {
    'test': 'python manage.py test --pattern=*tests.py',
    'test:ff': 'python project.py test --failfast',
    'lint': 'flake8',
    'demo:start': 'python manage.py demogame_start',
    'demo:advance': 'python manage.py demogame_advance',
    'e19:lb:start': 'python manage.py eights_2019_livebumps_start',
    'e19:lb:advance': 'python manage.py eights_2019_livebumps_advance',
}

command = args[0]
command = commands.get(command, 'python manage.py {}'.format(command))
command = ' '.join([command, *args[1:]])
os.system(command)
