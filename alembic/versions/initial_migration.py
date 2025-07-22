"""Initial migration

Revision ID: initial
Revises:
Create Date: 2025-05-08 12:04:13.971923

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guilds",
        sa.Column("guild_id", sa.BigInteger(), primary_key=True),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
    )
    op.create_table(
        "key_value_store",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
    )
    op.create_table(
        "migration_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("migration_name", sa.String(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "features",
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("feature_variables", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.guild_id"]),
        sa.PrimaryKeyConstraint("guild_id", "feature_name"),
    )


def downgrade() -> None:
    op.drop_table("features")
    op.drop_table("migration_log")
    op.drop_table("key_value_store")
    op.drop_table("guilds")
