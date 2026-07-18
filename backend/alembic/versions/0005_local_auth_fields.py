"""local email/password auth fields on users

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("google_sub", existing_type=sa.String(length=64), nullable=True)
        batch.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("dob", sa.Date(), nullable=True))
        batch.add_column(sa.Column("gender", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("gender")
        batch.drop_column("dob")
        batch.drop_column("password_hash")
        batch.alter_column("google_sub", existing_type=sa.String(length=64), nullable=False)
