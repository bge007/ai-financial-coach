"""consultation bookings for premium 1-on-1 sessions

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consultation_bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_time", sa.String(length=32), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_consultation_bookings_user_id",
        "consultation_bookings",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_consultation_bookings_user_id", table_name="consultation_bookings")
    op.drop_table("consultation_bookings")
