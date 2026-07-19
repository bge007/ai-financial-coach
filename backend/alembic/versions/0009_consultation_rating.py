"""consultation booking rating and closed_at

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("consultation_bookings") as batch_op:
        batch_op.add_column(sa.Column("expert_rating", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("consultation_bookings") as batch_op:
        batch_op.drop_column("closed_at")
        batch_op.drop_column("expert_rating")
