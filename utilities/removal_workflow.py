"""
Removal workflow utilities for managing user removal process
"""

import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from PatsBot.models import TrackedUser, RemovalStatus


class RemovalWorkflow:
    """Handles the removal workflow for tracked users"""

    # Time constants
    FIRST_WARNING_DURATION = datetime.timedelta(days=7)  # 1 week warning
    FINAL_NOTICE_DURATION = datetime.timedelta(days=2)  # 2 days final notice

    @staticmethod
    def mark_user_for_removal(
        session: Session, user_id: str, guild_id: str
    ) -> TrackedUser:
        """Mark a user for removal and set the removal date"""
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()

        if not user:
            # Create new tracked user
            user = TrackedUser(
                user_id=user_id,
                guild_id=guild_id,
                removal_status=RemovalStatus.PENDING_REMOVAL,
                removal_date=datetime.datetime.utcnow()
                + RemovalWorkflow.FIRST_WARNING_DURATION,
            )
            session.add(user)
        else:
            # Update existing user
            user.guild_id = guild_id
            user.removal_status = RemovalStatus.PENDING_REMOVAL
            user.removal_date = (
                datetime.datetime.utcnow() + RemovalWorkflow.FIRST_WARNING_DURATION
            )
            user.first_warning_sent_at = None
            user.final_notice_sent_at = None
            user.removed_at = None
            user.first_warning_message_id = None
            user.final_notice_message_id = None
            user.removal_message_id = None
            user.bot_retries = 0

        session.commit()
        return user

    @staticmethod
    def get_users_needing_first_warning(
        session: Session, guild_id: str
    ) -> List[TrackedUser]:
        """Get users who need their first warning sent"""
        return (
            session.query(TrackedUser)
            .filter(
                TrackedUser.guild_id == guild_id,
                TrackedUser.removal_status == RemovalStatus.PENDING_REMOVAL,
            )
            .all()
        )

    @staticmethod
    def get_users_needing_final_notice(
        session: Session, guild_id: str
    ) -> List[TrackedUser]:
        """Get users who need their final notice sent (within 2 days of removal)"""

        now = datetime.datetime.utcnow()
        return (
            session.query(TrackedUser)
            .filter(
                TrackedUser.guild_id == guild_id,
                TrackedUser.removal_status == RemovalStatus.FIRST_WARNING_SENT,
                TrackedUser.removal_date - RemovalWorkflow.FINAL_NOTICE_DURATION <= now,
                TrackedUser.removal_date > now,
            )
            .all()
        )

    @staticmethod
    def get_users_ready_for_removal(
        session: Session, guild_id: str
    ) -> List[TrackedUser]:
        """Get users who are ready to be removed (past their removal date)"""
        now = datetime.datetime.utcnow()

        return (
            session.query(TrackedUser)
            .filter(
                TrackedUser.guild_id == guild_id,
                TrackedUser.removal_status.in_(
                    [RemovalStatus.FIRST_WARNING_SENT, RemovalStatus.FINAL_NOTICE_SENT]
                ),
                TrackedUser.removal_date <= now,
            )
            .all()
        )

    @staticmethod
    def mark_first_warning_sent(
        session: Session, user_id: str, message_id: str
    ) -> None:
        """Mark that the first warning has been sent to a user"""
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if user:
            user.removal_status = RemovalStatus.FIRST_WARNING_SENT
            user.first_warning_sent_at = datetime.datetime.utcnow()
            user.first_warning_message_id = message_id
            user.bot_retries = 0  # Reset retry count on successful send
            session.commit()

    @staticmethod
    def mark_final_notice_sent(session: Session, user_id: str, message_id: str) -> None:
        """Mark that the final notice has been sent to a user"""
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if user:
            user.removal_status = RemovalStatus.FINAL_NOTICE_SENT
            user.final_notice_sent_at = datetime.datetime.utcnow()
            user.final_notice_message_id = message_id
            session.commit()

    @staticmethod
    def mark_user_removed(session: Session, user_id: str, message_id: str) -> None:
        """Mark that a user has been removed from the guild"""
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if user:
            user.removal_status = RemovalStatus.REMOVED
            user.removed_at = datetime.datetime.utcnow()
            user.removal_message_id = message_id
            session.commit()

    @staticmethod
    def reset_user_status(session: Session, user_id: str) -> None:
        """Reset a user's status to active (when they verify)"""
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if user:
            user.removal_status = RemovalStatus.ACTIVE
            user.removal_date = None
            user.first_warning_sent_at = None
            user.final_notice_sent_at = None
            user.removed_at = None
            user.first_warning_message_id = None
            user.final_notice_message_id = None
            user.removal_message_id = None
            user.bot_retries = 0
            session.commit()

    @staticmethod
    def increment_bot_retries(session: Session, user_id: str) -> int:
        """Increment the bot_retries counter for a user. Returns the new count."""
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if user:
            user.bot_retries = (user.bot_retries or 0) + 1
            session.commit()
            return user.bot_retries
        return 0

    @staticmethod
    def get_user_status(session: Session, user_id: str) -> Optional[TrackedUser]:
        """Get the current status of a user"""
        return session.query(TrackedUser).filter_by(user_id=user_id).first()

    @staticmethod
    def get_removal_summary(session: Session, guild_id: str) -> dict:
        """Get a summary of removal status for a guild"""
        users = session.query(TrackedUser).filter_by(guild_id=guild_id).all()

        summary = {
            "total_tracked": len(users),
            "active": 0,
            "pending_removal": 0,
            "first_warning_sent": 0,
            "final_notice_sent": 0,
            "removed": 0,
        }

        for user in users:
            if user.removal_status == RemovalStatus.ACTIVE:
                summary["active"] += 1
            elif user.removal_status == RemovalStatus.PENDING_REMOVAL:
                summary["pending_removal"] += 1
            elif user.removal_status == RemovalStatus.FIRST_WARNING_SENT:
                summary["first_warning_sent"] += 1
            elif user.removal_status == RemovalStatus.FINAL_NOTICE_SENT:
                summary["final_notice_sent"] += 1
            elif user.removal_status == RemovalStatus.REMOVED:
                summary["removed"] += 1

        return summary
