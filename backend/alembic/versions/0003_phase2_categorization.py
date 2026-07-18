"""phase 2: category_rules + category_cache

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-18

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "category_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("pattern", sa.String(length=512), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_category_rules_user_id", "category_rules", ["user_id"])

    op.create_table(
        "category_cache",
        sa.Column("description_hash", sa.String(length=64), primary_key=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("category_cache")
    op.drop_index("ix_category_rules_user_id", table_name="category_rules")
    op.drop_table("category_rules")
