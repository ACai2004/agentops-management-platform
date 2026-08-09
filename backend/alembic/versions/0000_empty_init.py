"""empty init

Revision ID: 0000
Revises:
Create Date: 2026-08-05
"""

# revision identifiers, used by Alembic.
revision = "0000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """初始空迁移：仅建立 alembic_version 表。Layer 1 起在其上叠加真实表结构。"""
    pass


def downgrade() -> None:
    pass
