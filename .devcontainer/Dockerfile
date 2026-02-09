FROM python:3.12-slim-bookworm AS commons

ARG POETRY_VERSION=2.0.1
ARG BUILD_DEPS='build-essential'

ARG WORKSPACE_FOLDER=segittur_commons

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \ 
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true \
    PYTHONUNBUFFERED=1

RUN mkdir -p /usr/local/${WORKSPACE_FOLDER}
WORKDIR /usr/local/${WORKSPACE_FOLDER}

COPY pyproject.toml .

RUN apt-get -q update \
  && apt-get install --no-install-recommends -yq $BUILD_DEPS \
  && pip install "poetry==$POETRY_VERSION" \
  && poetry install --no-interaction --no-ansi --no-root --with dev \
  && apt autoremove -y && apt-get clean && apt-get purge -y --auto-remove \
  && dpkg -l | grep ^rc | awk '{print $2}' | xargs apt-get purge -y \
  && rm -rf /var/lib/apt/lists/* \
  && rm -Rf pyproject.toml poetry.lock


FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm AS common-test

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG WORKSPACE_FOLDER=segittur_commons
ARG WORKDIR_PATH=/usr/local/${WORKSPACE_FOLDER}

ENV PYTHONPATH="/${WORKDIR_PATH}" \
    VIRTUAL_ENV=${WORKDIR_PATH}/.venv \
    HOME=/${WORKDIR_PATH} \
    PATH="${WORKDIR_PATH}/.venv/bin:$PATH"

COPY --from=commons ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY . /${WORKDIR_PATH}

WORKDIR /${WORKDIR_PATH}