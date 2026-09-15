import os
import json

from django.contrib.messages import constants as messages


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'ThisMustBeReplaced')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', '').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('DJANGO_HOSTS', '').split(',')

CSRF_TRUSTED_ORIGINS = [
    '{}://{}'.format('http' if DEBUG else 'https', domain)
    for domain in ALLOWED_HOSTS
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'fantasy',
    'django_celery_beat',
    'mcp_server',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'core', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
        'HOST': os.environ.get('DATABASE_HOST', ''),
        'PORT': os.environ.get('DATABASE_PORT', ''),
        'USER': os.environ.get('DATABASE_USER', ''),
        'PASSWORD': os.environ.get('DATABASE_PASS'),
        'NAME': os.environ.get('DATABASE_NAME', 'database.sqlite3'),
        'TEST': {
            'NAME': os.environ.get('DATABASE_NAME_TEST', 'test.sqlite3'),
        },
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


# Task workers

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULTS')
CELERY_BROKER_TRANSPORT_OPTIONS = json.loads(os.environ.get('CELERY_BROKER_OPTIONS', '{}'))

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_WORKER_LOG_FORMAT = '%(processName)-17s %(levelname)-8s %(message)s'


# Email

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_HOST_USER = os.environ.get('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASS', '')
EMAIL_USE_TLS = EMAIL_HOST != 'localhost'
DEFAULT_FROM_EMAIL = 'no-reply@mail.fantasybumps.org.uk'

SERVER_EMAIL = 'server-notice@mail.fantasybumps.org.uk'
EMAIL_SUBJECT_PREFIX = '[FantasyBumps] '
ADMINS = [('Joe Hitchen', 'hitchenjoe+sysadmin@gmail.com')]


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalisation and localisation

USE_I18N = False
LANGUAGE_CODE = 'en-gb'

USE_TZ = True
TIME_ZONE = 'Europe/London'


# Static files (CSS, JavaScript, Images)

STATIC_BACKEND = os.environ.get(
    'STATIC_BACKEND',
    'django.contrib.staticfiles.storage.StaticFilesStorage',
)
STATIC_URL = os.environ.get('STATIC_URL', '/static/')
STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR, 'static'))
STATIC_OPTIONS = json.loads(os.environ.get('STATIC_OPTIONS', '{}'))
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'core', 'static')]

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': STATIC_BACKEND, 'OPTIONS': STATIC_OPTIONS},
}

if STATIC_BACKEND.split('.')[0] == 'storages':
    INSTALLED_APPS.append('storages')


# MCP server

DJANGO_MCP_GLOBAL_SERVER_CONFIG = {
    'stateless': True,  # No container/session state to share between requests.
    'instructions': (
        'Fantasy Bumps is a fantasy sports game built around Oxford and Cambridge '
        'bumps racing (multi-day inter-collegiate rowing regattas where crews start '
        'in a fixed order and try to bump - catch - the boat ahead). Players build a '
        "team by buying real crews before each day's racing, using an in-game currency called "
        '"crabs". The market data is static each day - Pricing is based only on position on the '
        'river, there is no dynamic pricing. Payouts are awarded each day based on performance of '
        'crews, with crews "rowing over" (neither bumping or being bumped) getting a small payout '
        'and crews who bump getting a much larger payout, particularly if they gain multiple '
        'places. Be aware that because bumps racing is a competition, lower rankings are '
        'better, with rank 1 (also known as "Head of the River" or "Headship") being the best, '
        "and position changes have the reversed effect - a gained place decreases a crew's rank. "
        '\n\n'
        'Call list_events() first to find valid series-year pairs. `series` is one of: `D`=Demo, '
        '`T`=Torpids, `E`=Eights, `L`=Lents, `M`=Mays. Where a tool takes `gender`, it is `M`=Men '
        'or `W`=Women.\n'
        'Everything exposed here is read-only and already public via the website UI and JSON API.'
    ),
}


# Other settings
LOGIN_REDIRECT_URL = 'index'
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}
