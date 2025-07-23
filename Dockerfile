FROM python:3.11-slim

# Authors
LABEL authors="vixi@snowsune.net"

# Set the name of our app
ARG APP_NAME=pats-bot
ENV APP_NAME=${APP_NAME}

# App home
ARG HOME="/app"
ENV HOME=${HOME}

# Upgrade pip
RUN pip install --upgrade pip --no-cache-dir

# Set workdir
WORKDIR ${HOME}
ENV PYTHONPATH=/app

# Add any packages we need
RUN apt update && apt install -y python3-dev curl libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev

# Install requirements
COPY requirements.txt ./
RUN pip install -r requirements.txt --no-cache-dir

# Copy the rest of the app
COPY README.md ./
COPY setup.py ./
COPY alembic.ini ./
COPY bin ./bin
COPY cogs ./cogs
COPY utilities ./utilities

# Copy the PatsBot package
COPY PatsBot ./PatsBot

# Add bin to PATH
ENV PATH=$PATH:/app/bin

# Install our app as a package
RUN pip install -e /app

# The `|| exit 1` isn't required but it's good practice anyway.
HEALTHCHECK CMD alembic current || exit 1

# Run the entrypoint bin
ENTRYPOINT ["entrypoint"] 