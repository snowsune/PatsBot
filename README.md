# PatsBot

Written by (Vixi)[mailto:vixi@snowsune.net] for Pats and their discord server!

## Commands

```md
- Version
  Prints revision info and where to file bugs!
```

## Development!

Built and managed with docker! You can run the whole stack
or just build and run locally with pipenv

Import ENV variables
```
DATABASE_URL=
DISCORD_TOKEN=
```

### Developing locally

```shell
pipenv install
pipenv run python -m PatsBot
```

## Running with Docker

You can build and run the bot in a Docker container for local testing:

```sh
# Build the Docker image
docker build -t pats-bot . --load

# Run the container (best practice, use a .env with tokens and vars)
docker run --rm -it \
    --env-file .env \
    -v $(pwd)/.local.sqlite:/app/.local.sqlite \
    pats-bot
```

- The bot will automatically run Alembic migrations on startup.
- The `.local.sqlite` file will be created in your project root and mapped into the container for persistence.
- You can add other environment variables as needed (e.g., `DEBUG=1`).
