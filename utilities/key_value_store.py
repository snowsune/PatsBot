from PatsBot.models import KeyValue
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os

# Use the same DB URL logic as Alembic
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./.local.sqlite"
engine = create_engine(DATABASE_URL, future=True)
Session = sessionmaker(bind=engine)


def get_value(key: str) -> str:
    """Get a value from the key-value store."""
    session = Session()
    try:
        kv = session.get(KeyValue, key)
        return kv.value if kv else None
    except:
        return None
    finally:
        session.close()


def set_value(key: str, value: str):
    """Set a value in the key-value store."""
    session = Session()
    try:
        kv = KeyValue(key=key, value=value)
        session.merge(kv)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
