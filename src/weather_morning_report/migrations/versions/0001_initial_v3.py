"""Initial v3 service schema.

Revision ID: 0001_initial_v3
Revises:
"""

from alembic import op

from weather_morning_report.database.models import Base

revision = "0001_initial_v3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
