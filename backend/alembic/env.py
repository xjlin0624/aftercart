import sys
from pathlib import Path

# Make sure `backend/` is on the path so app imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.settings import get_settings
from app.models.base import Base

# Import all models so their metadata is registered on Base
import app.models.user  # noqa: F401
import app.models.user_preferences  # noqa: F401
import app.models.order  # noqa: F401
import app.models.order_item  # noqa: F401
import app.models.price_snapshot  # noqa: F401
import app.models.alert  # noqa: F401
import app.models.delivery_event  # noqa: F401
import app.models.subscription  # noqa: F401
import app.models.outcome_log  # noqa: F401
import app.models.push_device_token  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the value from our Pydantic settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
