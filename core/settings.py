import os

from django.contrib.messages import constants as messages


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'ThisMustBeReplaced')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG').lower() == 'true' if 'DJANGO_DEBUG' in os.environ else False

ALLOWED_HOSTS = os.environ.get('DJANGO_HOSTS').split(',') if 'DJANGO_HOSTS' in os.environ else []


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'fantasy',
    'django_q',
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

Q_CLUSTER = {
    'orm': 'default',
    'timeout': 45,
    'catch_up': False,
}


# Email

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_HOST_USER = os.environ.get('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASS', '')
EMAIL_USE_TLS = EMAIL_HOST != 'localhost'
DEFAULT_FROM_EMAIL = 'no-reply@mail.fantasybumps.org.uk'

SERVER_EMAIL = 'server-notice@mail.fantasybumps.org.uk'
EMAIL_SUBJECT_PREFIX = '[FantasyBumps] '
ADMINS = [('Joe Hitchen', 'hitchenjoe+sysadmin@gmail.com')]
IGNORABLE_404_URLS = []


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

USE_L10N = False


# Static files (CSS, JavaScript, Images)

STATIC_URL = os.environ.get('STATIC_URL', '/static/')
STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR, 'static'))
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'core', 'static')]

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))


# Other settings
LOGIN_REDIRECT_URL = 'index'
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}
