"""add trace.inputs (named workflow inputs snapshot)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 记录本次运行的命名输入 {字段名: 值}；历史行补空对象
    op.add_column(
        "traces",
        sa.Column("inputs", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("traces", "inputs")
