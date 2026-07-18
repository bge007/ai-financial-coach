"""user_profiles for declared preferences

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("monthly_income", sa.Numeric(14, 2), nullable=True),
        sa.Column("emergency_fund", sa.Numeric(14, 2), nullable=True),
        sa.Column("risk_profile", sa.String(length=32), nullable=False, server_default="moderate"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
