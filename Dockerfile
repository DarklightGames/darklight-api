# syntax=docker/dockerfile:1.2

ARG PYTHON_VERSION=3.8.3

# STAGE 1: Build dependencies

FROM python:${PYTHON_VERSION}-alpine as builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apk update \
    && apk add --no-cache \
               --upgrade \
               postgresql-dev \
               gcc \
               musl-dev \
               python3-dev

WORKDIR /wheels

COPY ./requirements.txt /wheels/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip wheel -r requirements.txt

# STAGE 2: Final image

FROM python:${PYTHON_VERSION}-alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create an app user
ENV APP_USER=app
RUN addgroup -S ${APP_USER} && adduser -S ${APP_USER} -G ${APP_USER}

# Create a directory for the app
ENV APP_HOME="/home/${APP_USER}/src"
RUN echo ${APP_HOME}
RUN mkdir -p $APP_HOME

# Install dependencies
RUN apk update \
    && apk add --no-cache \
               --upgrade \
               libpq \
               bash

COPY --from=builder /wheels /wheels

RUN pip install --upgrade pip \
    && pip install --no-cache \
                   -r /wheels/requirements.txt \
                   -f /wheels \
    && rm -rf /wheels

COPY . ${APP_HOME}
RUN chown -R ${APP_USER}:${APP_USER} ${APP_HOME}

USER ${APP_USER}
WORKDIR ${APP_HOME}

RUN chmod +x ./entrypoint.sh
ENTRYPOINT [ "./entrypoint.sh" ]