from PatsBot.models import Guild
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
import json

# Use the same DB URL logic as Alembic
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./.local.sqlite"
engine = create_engine(DATABASE_URL, future=True)
Session = sessionmaker(bind=engine)


def get_guild_settings(guild_id: int) -> dict:
    """Get all settings for a guild."""
    session = Session()
    try:
        guild = session.get(Guild, str(guild_id))
        if guild and guild.settings:
            return json.loads(guild.settings)
        return {}
    except:
        return {}
    finally:
        session.close()


def set_guild_setting(guild_id: int, key: str, value):
    """Set a specific setting for a guild."""
    session = Session()
    try:
        guild = session.get(Guild, str(guild_id))
        if not guild:
            guild = Guild(guild_id=str(guild_id))
            session.add(guild)

        settings = json.loads(guild.settings) if guild.settings else {}
        settings[key] = value
        guild.settings = json.dumps(settings)

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_guild_setting(guild_id: int, key: str, default=None):
    """Get a specific setting for a guild."""
    settings = get_guild_settings(guild_id)
    return settings.get(key, default)


def ensure_guild_exists(guild_id: int, guild_name: str = None):
    """Ensure a guild record exists in the database."""
    session = Session()
    try:
        guild = session.get(Guild, str(guild_id))
        if not guild:
            guild = Guild(guild_id=str(guild_id), name=guild_name, settings="{}")
            session.add(guild)
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
