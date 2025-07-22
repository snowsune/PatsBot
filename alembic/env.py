from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from typing import Dict, Any

from alembic import context

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models import Base  # Import Base from new models.py

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata if Base else None


def get_url():
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Use local SQLite for development if DATABASE_URL is not set
    return "sqlite:///./.local.sqlite"


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration: Dict[str, Any] = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
