from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Enum
from sqlalchemy.dialects.sqlite import JSON
import datetime
import enum

Base = declarative_base()


class RemovalStatus(enum.Enum):
    """Status of user in the removal process"""

    ACTIVE = "active"  # User is active and verified
    PENDING_REMOVAL = (
        "pending_removal"  # User marked for removal, waiting for first warning
    )
    FIRST_WARNING_SENT = (
        "first_warning_sent"  # First warning sent, waiting for final notice
    )
    FINAL_NOTICE_SENT = "final_notice_sent"  # Final notice sent, waiting for removal
    REMOVED = "removed"  # User has been removed from guild


class Guild(Base):
    __tablename__ = "guilds"
    guild_id = Column(String, primary_key=True)  # Discord guild ID as string
    name = Column(String, nullable=True)
    joined_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    settings = Column(Text, nullable=True)  # JSON string for guild settings


class TrackedUser(Base):
    __tablename__ = "tracked_users"
    user_id = Column(String, primary_key=True)  # Discord user ID as string
    guild_id = Column(String, nullable=False)  # Which guild this user belongs to
    joined_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    roles = Column(Text, nullable=True)  # Store as comma-separated string or JSON

    # Removal process fields
    removal_status = Column(
        Enum(RemovalStatus), nullable=False, default=RemovalStatus.ACTIVE
    )
    removal_date = Column(
        DateTime, nullable=True
    )  # When they should be removed (1 week from first warning)
    first_warning_sent_at = Column(
        DateTime, nullable=True
    )  # When first warning was sent
    final_notice_sent_at = Column(DateTime, nullable=True)  # When final notice was sent
    removed_at = Column(DateTime, nullable=True)  # When they were actually removed

    # Notification tracking
    first_warning_message_id = Column(
        String, nullable=True
    )  # Discord message ID of first warning
    final_notice_message_id = Column(
        String, nullable=True
    )  # Discord message ID of final notice
    removal_message_id = Column(
        String, nullable=True
    )  # Discord message ID of removal notification


class KeyValue(Base):
    __tablename__ = "key_value_store"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
