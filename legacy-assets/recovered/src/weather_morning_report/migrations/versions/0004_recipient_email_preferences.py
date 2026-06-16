"""Add per-recipient email presentation preferences.

Revision ID: 0004_recipient_email_preferences
Revises: 0003_new_user_defaults
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0004_recipient_email_preferences"
down_revision = "0003_new_user_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "recipient_email_preferences" not in inspector.get_table_names():
        op.create_table(
            "recipient_email_preferences",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("recipient_id", sa.Integer(), nullable=False),
            sa.Column(
                "email_template",
                sa.String(length=20),
                nullable=False,
                server_default="1",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["recipient_id"], ["recipients.id"]),
            sa.UniqueConstraint(
                "recipient_id",
                name="uq_recipient_email_preference",
            ),
        )
    connection = op.get_bind()
    recipients = sa.table(
        "recipients",
        sa.column("id", sa.Integer()),
    )
    preferences = sa.table(
        "recipient_email_preferences",
        sa.column("recipient_id", sa.Integer()),
        sa.column("email_template", sa.String()),
        sa.column("updated_at", sa.DateTime()),
    )
    existing = {
        row[0]
        for row in connection.execute(
            sa.text("SELECT recipient_id FROM recipient_email_preferences")
        )
    }
    rows = [
        {
            "recipient_id": recipient.id,
            "email_template": "1",
            "updated_at": datetime.now(UTC).replace(tzinfo=None),
        }
        for recipient in connection.execute(sa.select(recipients.c.id))
        if recipient.id not in existing
    ]
    if rows:
        op.bulk_insert(preferences, rows)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "recipient_email_preferences" in inspector.get_table_names():
        op.drop_table("recipient_email_preferences")
