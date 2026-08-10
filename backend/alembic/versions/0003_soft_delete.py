"""soft delete agents

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agent 软删除标记（非空 = 已删除）
    op.add_column("agents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "deleted_at")
