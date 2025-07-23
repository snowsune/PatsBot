from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.dialects.sqlite import JSON
import datetime

Base = declarative_base()


class Test(Base):
    __tablename__ = "test"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class Guild(Base):
    __tablename__ = "guilds"
    guild_id = Column(String, primary_key=True)  # Discord guild ID as string
    name = Column(String, nullable=True)
    joined_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    settings = Column(Text, nullable=True)  # JSON string for guild settings


class TrackedUser(Base):
    __tablename__ = "tracked_users"
    user_id = Column(String, primary_key=True)  # Discord user ID as string
    joined_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    roles = Column(Text, nullable=True)  # Store as comma-separated string or JSON
    marked_for_removal = Column(
        Boolean, nullable=False, default=False
    )  # We'll remove them next cycle
    kicked_at = Column(DateTime, nullable=True)  # When (and if) they were kicked


class KeyValue(Base):
    __tablename__ = "key_value_store"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
