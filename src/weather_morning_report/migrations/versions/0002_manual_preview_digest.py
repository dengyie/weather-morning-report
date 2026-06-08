"""Bind manual jobs to their confirmed preview.

Revision ID: 0002_manual_preview_digest
Revises: 0001_initial_v3
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_manual_preview_digest"
down_revision = "0001_initial_v3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("jobs")}
    if "preview_digest" not in columns:
        op.add_column(
            "jobs",
            sa.Column("preview_digest", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("jobs")}
    if "preview_digest" in columns:
        op.drop_column("jobs", "preview_digest")
