"""add_bot_retries_to_tracked_users

Revision ID: 8539765bf3be
Revises: c67dd4c23e18
Create Date: 2026-01-01 15:47:01.438879

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8539765bf3be"
down_revision: Union[str, None] = "c67dd4c23e18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "tracked_users",
        sa.Column("bot_retries", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tracked_users", "bot_retries")
