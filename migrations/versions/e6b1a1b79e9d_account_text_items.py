"""

Revision ID: e6b1a1b79e9d
Revises: 4d9f2c0f3c1b
Create Date: 2025-12-20 12:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e6b1a1b79e9d"
down_revision = "4d9f2c0f3c1b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_greetings_morning",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "account_greetings_day",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "account_greetings_evening",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "account_greetings_night",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "account_greetings_anytime",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "account_clarifying_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "account_follow_up_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "account_lead_in_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "account_closing_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_texts_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_texts_id"],
            ["account_texts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.drop_column("account_texts", "greetings_morning")
    op.drop_column("account_texts", "greetings_day")
    op.drop_column("account_texts", "greetings_evening")
    op.drop_column("account_texts", "greetings_night")
    op.drop_column("account_texts", "greetings_anytime")
    op.drop_column("account_texts", "clarifying_texts")
    op.drop_column("account_texts", "follow_up_texts")
    op.drop_column("account_texts", "lead_in_texts")
    op.drop_column("account_texts", "closing_texts")


def downgrade() -> None:
    op.add_column(
        "account_texts",
        sa.Column(
            "greetings_morning",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "account_texts",
        sa.Column(
            "greetings_day",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "account_texts",
        sa.Column(
            "greetings_evening",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "account_texts",
        sa.Column(
            "greetings_night",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "account_texts",
        sa.Column(
            "greetings_anytime",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "account_texts",
        sa.Column(
            "clarifying_texts",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "account_texts",
        sa.Column(
            "follow_up_texts",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "account_texts",
        sa.Column(
            "lead_in_texts",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "account_texts",
        sa.Column(
            "closing_texts",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.drop_table("account_closing_texts")
    op.drop_table("account_lead_in_texts")
    op.drop_table("account_follow_up_texts")
    op.drop_table("account_clarifying_texts")
    op.drop_table("account_greetings_anytime")
    op.drop_table("account_greetings_night")
    op.drop_table("account_greetings_evening")
    op.drop_table("account_greetings_day")
    op.drop_table("account_greetings_morning")
