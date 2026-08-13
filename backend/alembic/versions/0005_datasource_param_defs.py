"""add datasources.param_defs (API parameter contract)

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 参数契约：list[DatasourceParam]（name/label/required/type/options/placeholder）
    op.add_column(
        "datasources",
        sa.Column("param_defs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("datasources", "param_defs")
