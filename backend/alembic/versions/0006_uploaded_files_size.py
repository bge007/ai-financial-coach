"""add uploaded_files.size for legacy databases

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("uploaded_files"):
        return

    cols = {c["name"] for c in insp.get_columns("uploaded_files")}
    if "size" in cols:
        return

    with op.batch_alter_table("uploaded_files") as batch:
        batch.add_column(
            sa.Column("size", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("uploaded_files"):
        return

    cols = {c["name"] for c in insp.get_columns("uploaded_files")}
    if "size" not in cols:
        return

    with op.batch_alter_table("uploaded_files") as batch:
        batch.drop_column("size")
