"""Add defaults for newly created users.

Revision ID: 0003_new_user_defaults
Revises: 0002_manual_preview_digest
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0003_new_user_defaults"
down_revision = "0002_manual_preview_digest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "new_user_defaults" not in inspector.get_table_names():
        op.create_table(
            "new_user_defaults",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "location_name",
                sa.String(length=240),
                nullable=False,
                server_default="Changning District, Shanghai",
            ),
            sa.Column(
                "location_query",
                sa.String(length=500),
                nullable=False,
                server_default="Changning,Shanghai",
            ),
            sa.Column(
                "timezone",
                sa.String(length=80),
                nullable=False,
                server_default="Asia/Shanghai",
            ),
            sa.Column(
                "language",
                sa.String(length=10),
                nullable=False,
                server_default="zh-CN",
            ),
            sa.Column(
                "local_send_time",
                sa.String(length=5),
                nullable=False,
                server_default="08:30",
            ),
            sa.Column(
                "report_type",
                sa.String(length=20),
                nullable=False,
                server_default="morning",
            ),
            sa.Column(
                "send_policy",
                sa.String(length=20),
                nullable=False,
                server_default="always",
            ),
            sa.Column(
                "schedule_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
    defaults = sa.table(
        "new_user_defaults",
        sa.column("id", sa.Integer()),
        sa.column("location_name", sa.String()),
        sa.column("location_query", sa.String()),
        sa.column("timezone", sa.String()),
        sa.column("language", sa.String()),
        sa.column("local_send_time", sa.String()),
        sa.column("report_type", sa.String()),
        sa.column("send_policy", sa.String()),
        sa.column("schedule_enabled", sa.Boolean()),
        sa.column("updated_at", sa.DateTime()),
    )
    connection = op.get_bind()
    exists = connection.execute(
        sa.text("SELECT id FROM new_user_defaults WHERE id = 1")
    ).first()
    if exists is None:
        op.bulk_insert(
            defaults,
            [
                {
                    "id": 1,
                    "location_name": "Changning District, Shanghai",
                    "location_query": "Changning,Shanghai",
                    "timezone": "Asia/Shanghai",
                    "language": "zh-CN",
                    "local_send_time": "08:30",
                    "report_type": "morning",
                    "send_policy": "always",
                    "schedule_enabled": True,
                    "updated_at": datetime.now(UTC).replace(tzinfo=None),
                }
            ],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "new_user_defaults" in inspector.get_table_names():
        op.drop_table("new_user_defaults")
