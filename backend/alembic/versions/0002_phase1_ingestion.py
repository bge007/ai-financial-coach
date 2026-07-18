"""phase 1 ingestion tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-18

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("rows_parsed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_date", sa.Date(), nullable=True),
        sa.Column("max_date", sa.Date(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "sha256", name="uq_uploaded_files_user_hash"),
    )
    op.create_index("ix_uploaded_files_user_id", "uploaded_files", ["user_id"])
    op.create_index("ix_uploaded_files_sha256", "uploaded_files", ["sha256"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column(
            "uploaded_file_id",
            sa.Integer(),
            sa.ForeignKey("uploaded_files.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_date", "transactions", ["date"])

    op.create_table(
        "financial_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("monthly_income", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column(
            "monthly_expenses", sa.Numeric(14, 2), nullable=False, server_default="0"
        ),
        sa.Column("surplus", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_debt", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("emi_outgo", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("financial_profiles")
    op.drop_index("ix_transactions_date", table_name="transactions")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_uploaded_files_sha256", table_name="uploaded_files")
    op.drop_index("ix_uploaded_files_user_id", table_name="uploaded_files")
    op.drop_table("uploaded_files")
