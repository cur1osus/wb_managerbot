"""

Revision ID: 4d9f2c0f3c1b
Revises: c7b2f9f4c0a1
Create Date: 2025-12-20 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4d9f2c0f3c1b"
down_revision = "c7b2f9f4c0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("greetings_morning", sa.Text(), nullable=False),
        sa.Column("greetings_day", sa.Text(), nullable=False),
        sa.Column("greetings_evening", sa.Text(), nullable=False),
        sa.Column("greetings_night", sa.Text(), nullable=False),
        sa.Column("greetings_anytime", sa.Text(), nullable=False),
        sa.Column("clarifying_texts", sa.Text(), nullable=False),
        sa.Column("follow_up_texts", sa.Text(), nullable=False),
        sa.Column("lead_in_texts", sa.Text(), nullable=False),
        sa.Column("closing_texts", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
    )


def downgrade() -> None:
    op.drop_table("account_texts")
