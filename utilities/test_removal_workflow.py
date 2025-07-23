"""
Utility script to help test the removal workflow by manipulating database timestamps
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PatsBot.models import TrackedUser, RemovalStatus

# Use the same DB URL logic as the main app
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./.local.sqlite"
engine = create_engine(DATABASE_URL, future=True)
Session = sessionmaker(bind=engine)


def list_users():
    """List all tracked users with their current status"""
    session = Session()
    try:
        users = session.query(TrackedUser).all()
        print(f"\n📋 Found {len(users)} tracked users:")
        print("-" * 80)

        for user in users:
            status_emoji = {
                RemovalStatus.ACTIVE: "✅",
                RemovalStatus.PENDING_REMOVAL: "⏳",
                RemovalStatus.FIRST_WARNING_SENT: "⚠️",
                RemovalStatus.FINAL_NOTICE_SENT: "🚨",
                RemovalStatus.REMOVED: "🚫",
            }

            print(f"User ID: {user.user_id}")
            print(f"Guild ID: {user.guild_id}")
            print(
                f"Status: {status_emoji[user.removal_status]} {user.removal_status.value}"
            )
            print(f"Joined: {user.joined_at}")

            if user.removal_date:
                print(f"Removal Date: {user.removal_date}")
            if user.first_warning_sent_at:
                print(f"First Warning: {user.first_warning_sent_at}")
            if user.final_notice_sent_at:
                print(f"Final Notice: {user.final_notice_sent_at}")
            if user.removed_at:
                print(f"Removed: {user.removed_at}")

            print("-" * 80)

    finally:
        session.close()


def mark_user_for_removal(user_id: str, guild_id: str):
    """Mark a user for removal (sets removal date to 7 days from now)"""
    session = Session()
    try:
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if not user:
            print(f"❌ User {user_id} not found in database")
            return

        # Set removal date to 7 days from now
        removal_date = datetime.utcnow() + timedelta(days=7)
        user.removal_status = RemovalStatus.PENDING_REMOVAL
        user.removal_date = removal_date
        user.first_warning_sent_at = None
        user.final_notice_sent_at = None
        user.removed_at = None
        user.first_warning_message_id = None
        user.final_notice_message_id = None
        user.removal_message_id = None

        session.commit()
        print(f"✅ Marked user {user_id} for removal on {removal_date}")

    finally:
        session.close()


def simulate_first_warning_sent(user_id: str):
    """Simulate that first warning was sent (sets first_warning_sent_at to now)"""
    session = Session()
    try:
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if not user:
            print(f"❌ User {user_id} not found in database")
            return

        user.removal_status = RemovalStatus.FIRST_WARNING_SENT
        user.first_warning_sent_at = datetime.utcnow()
        user.first_warning_message_id = f"TEST_{datetime.utcnow().timestamp()}"

        session.commit()
        print(f"✅ Simulated first warning sent for user {user_id}")

    finally:
        session.close()


def simulate_final_notice_sent(user_id: str):
    """Simulate that final notice was sent (sets final_notice_sent_at to now)"""
    session = Session()
    try:
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if not user:
            print(f"❌ User {user_id} not found in database")
            return

        user.removal_status = RemovalStatus.FINAL_NOTICE_SENT
        user.final_notice_sent_at = datetime.utcnow()
        user.final_notice_message_id = f"TEST_{datetime.utcnow().timestamp()}"

        session.commit()
        print(f"✅ Simulated final notice sent for user {user_id}")

    finally:
        session.close()


def simulate_user_removed(user_id: str):
    """Simulate that user was removed (sets removed_at to now)"""
    session = Session()
    try:
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if not user:
            print(f"❌ User {user_id} not found in database")
            return

        user.removal_status = RemovalStatus.REMOVED
        user.removed_at = datetime.utcnow()
        user.removal_message_id = f"TEST_{datetime.utcnow().timestamp()}"

        session.commit()
        print(f"✅ Simulated user removal for user {user_id}")

    finally:
        session.close()


def reset_user_status(user_id: str):
    """Reset a user's status to active"""
    session = Session()
    try:
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if not user:
            print(f"❌ User {user_id} not found in database")
            return

        user.removal_status = RemovalStatus.ACTIVE
        user.removal_date = None
        user.first_warning_sent_at = None
        user.final_notice_sent_at = None
        user.removed_at = None
        user.first_warning_message_id = None
        user.final_notice_message_id = None
        user.removal_message_id = None

        session.commit()
        print(f"✅ Reset user {user_id} status to active")

    finally:
        session.close()


def set_removal_date(user_id: str, days_from_now: int):
    """Set a user's removal date to a specific number of days from now"""
    session = Session()
    try:
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if not user:
            print(f"❌ User {user_id} not found in database")
            return

        removal_date = datetime.utcnow() + timedelta(days=days_from_now)
        user.removal_date = removal_date

        session.commit()
        print(
            f"✅ Set removal date for user {user_id} to {removal_date} ({days_from_now} days from now)"
        )

    finally:
        session.close()


def set_joined_date(user_id: str, days_ago: int):
    """Set a user's joined date to a specific number of days ago"""
    session = Session()
    try:
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if not user:
            print(f"❌ User {user_id} not found in database")
            return

        joined_date = datetime.utcnow() - timedelta(days=days_ago)
        user.joined_at = joined_date

        session.commit()
        print(
            f"✅ Set joined date for user {user_id} to {joined_date} ({days_ago} days ago)"
        )

    finally:
        session.close()


def set_first_warning_date(user_id: str, days_ago: int):
    session = Session()
    try:
        user = session.query(TrackedUser).filter_by(user_id=user_id).first()
        if not user:
            print(f"❌ User {user_id} not found in database")
            return
        user.removal_status = RemovalStatus.FIRST_WARNING_SENT
        user.first_warning_sent_at = datetime.utcnow() - timedelta(days=days_ago)
        session.commit()
        print(f"✅ Set first warning date for user {user_id} to {days_ago} days ago")
    finally:
        session.close()


def main():
    """Main function to run the test utility"""
    print("🧪 Removal Workflow Test Utility")
    print("=" * 50)

    while True:
        print("\nAvailable commands:")
        print("1. list - List all tracked users")
        print("2. mark <user_id> <guild_id> - Mark user for removal")
        print("3. first <user_id> - Simulate first warning sent")
        print("4. final <user_id> - Simulate final notice sent")
        print("5. remove <user_id> - Simulate user removed")
        print("6. reset <user_id> - Reset user status to active")
        print("7. set_removal <user_id> <days> - Set removal date (days from now)")
        print("8. set_joined <user_id> <days> - Set joined date (days ago)")
        print("9. quit - Exit")
        print(
            "10. set_first_warning <user_id> <days> - Set first warning date (days ago)"
        )

        command = input("\nEnter command: ").strip().split()

        if not command:
            continue

        cmd = command[0].lower()

        try:
            if cmd == "list":
                list_users()
            elif cmd == "mark" and len(command) >= 3:
                mark_user_for_removal(command[1], command[2])
            elif cmd == "first" and len(command) >= 2:
                simulate_first_warning_sent(command[1])
            elif cmd == "final" and len(command) >= 2:
                simulate_final_notice_sent(command[1])
            elif cmd == "remove" and len(command) >= 2:
                simulate_user_removed(command[1])
            elif cmd == "reset" and len(command) >= 2:
                reset_user_status(command[1])
            elif cmd == "set_removal" and len(command) >= 3:
                set_removal_date(command[1], int(command[2]))
            elif cmd == "set_joined" and len(command) >= 3:
                set_joined_date(command[1], int(command[2]))
            elif cmd == "set_first_warning" and len(command) >= 3:
                set_first_warning_date(command[1], int(command[2]))
            elif cmd == "quit":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid command or missing arguments")

        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
