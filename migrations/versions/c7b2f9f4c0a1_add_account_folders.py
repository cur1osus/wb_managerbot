"""

Revision ID: c7b2f9f4c0a1
Revises: bbc4cfa83846
Create Date: 2025-12-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7b2f9f4c0a1"
down_revision = "bbc4cfa83846"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("accounts", sa.Column("folder_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "accounts_folder_id_fkey",
        "accounts",
        "account_folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("accounts_folder_id_fkey", "accounts", type_="foreignkey")
    op.drop_column("accounts", "folder_id")
    op.drop_table("account_folders")
