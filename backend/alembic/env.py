# pyright: reportMissingImports=false
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config  # type: ignore
from sqlalchemy import pool  # type: ignore

from alembic import context # type: ignore
from dotenv import load_dotenv

# add your model's directory to sys.path
sys.path.append(os.getcwd())
if os.path.exists("../.env.local"):
    load_dotenv("../.env.local")
elif os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

from db import Base  # type: ignore
import models  # type: ignore # ensure all models are imported
import training_models  # type: ignore # ensure training models are included

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Use None to allow migrations to run based on migration files alone
# since the Python models are deprecated/broken.
target_metadata = None

def get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        # Fallback for local development if not set
        return "sqlite:///./levi.db"
    return url

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
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
