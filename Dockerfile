FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HOME /usr/src/app
ENV STATIC_ROOT /usr/data/static
ENV MEDIA_ROOT /usr/data/media

WORKDIR $HOME
RUN adduser --disabled-password python && chown -R python:python $HOME \
 && mkdir -p $STATIC_ROOT $MEDIA_ROOT && chown -R python:python /usr/data

# Install build dependencies and production packages
RUN apk add --no-cache --update mariadb-connector-c-dev libcurl \
 && apk add --no-cache --virtual .build gcc musl-dev mariadb-dev curl-dev \
 && pip install --no-cache-dir uv mysqlclient 'celery[sqs]' 'boto3>=1.43.86' 'pycurl>=7.47.0' django-storages[s3] gunicorn \
 && apk del --purge .build
# boto3 version pin required because messages are not received with the latest version

# Copy project configuration and lock file (for reproducible builds)
COPY --chown=python pyproject.toml uv.lock .

# Install Python dependencies using exact locked versions
RUN uv sync --no-cache --frozen

COPY --chown=python . .

USER python
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--logger-class", "overrides.GunicornLogger"]
EXPOSE 8000

