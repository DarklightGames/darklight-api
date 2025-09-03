ARG PYTHON_VERSION=3.13.2

FROM python:${PYTHON_VERSION}

ENV APP_USER=app

RUN useradd --create-home \
            --home-dir "/home/${APP_USER}" \
            --shell "/bin/bash" \
            --gid root \
            --groups sudo \
            --uid 1001 \
            "${APP_USER}"

USER ${APP_USER}

ENV APP_HOME="/home/${APP_USER}/src"
RUN mkdir -p ${APP_HOME}dd


# Install dependencies
COPY requirements.txt .
RUN sed `/pywin32/d` requirements.txt

RUN python -m pip install --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR ${APP_HOME}

EXPOSE 8000
