FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm AS commons

ARG POETRY_VERSION=2.0.1
ARG BUILD_DEPS='build-essential'

ARG UID=1000
ARG USER=commons
ARG GROUP=commons
ARG WORKSPACE_FOLDER=segittur_commons

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \ 
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true \
    PYTHONUNBUFFERED=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN mkdir -p /usr/local/${WORKSPACE_FOLDER}
WORKDIR /usr/local/${WORKSPACE_FOLDER}

COPY pyproject.toml .

RUN apt-get -q update \
  && apt-get install --no-install-recommends -yq $BUILD_DEPS \
  && pip install "poetry==$POETRY_VERSION" \
  && poetry install --no-interaction --no-ansi --no-root && rm -rf ${POETRY_CACHE_DIR}\
  && apt autoremove -y && apt-get clean && apt-get purge -y --auto-remove \
  && dpkg -l | grep ^rc | awk '{print $2}' | xargs apt-get purge -y \
  && rm -rf /var/lib/apt/lists/* \
  && rm -Rf pyproject.toml poetry.lock
