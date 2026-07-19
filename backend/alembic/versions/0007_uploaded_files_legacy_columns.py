"""drop legacy uploaded_files columns not used by current model

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_LEGACY_COLUMNS = (
    "content_type",
    "rows_parsed",
    "rows_skipped",
    "min_date",
    "max_date",
)


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("uploaded_files"):
        return

    cols = {c["name"] for c in insp.get_columns("uploaded_files")}
    to_drop = [name for name in _LEGACY_COLUMNS if name in cols]
    if not to_drop:
        return

    with op.batch_alter_table("uploaded_files") as batch:
        for name in to_drop:
            batch.drop_column(name)


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("uploaded_files"):
        return

    cols = {c["name"] for c in insp.get_columns("uploaded_files")}
    with op.batch_alter_table("uploaded_files") as batch:
        if "content_type" not in cols:
            batch.add_column(
                sa.Column(
                    "content_type",
                    sa.String(length=100),
                    nullable=False,
                    server_default="application/octet-stream",
                )
            )
        if "rows_parsed" not in cols:
            batch.add_column(
                sa.Column(
                    "rows_parsed",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )
        if "rows_skipped" not in cols:
            batch.add_column(
                sa.Column(
                    "rows_skipped",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )
        if "min_date" not in cols:
            batch.add_column(sa.Column("min_date", sa.Date(), nullable=True))
        if "max_date" not in cols:
            batch.add_column(sa.Column("max_date", sa.Date(), nullable=True))
