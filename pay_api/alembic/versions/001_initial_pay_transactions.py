"""initial pay_transactions

Revision ID: 001_initial
Revises:
Create Date: 2026-04-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 旧版应用在 lifespan 里 init_schema() 已建表时，避免重复 CREATE 导致 DuplicateTableError
    bind = op.get_bind()
    if inspect(bind).has_table("pay_transactions"):
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_pay_transactions_created_at "
            "ON pay_transactions (created_at DESC)"
        )
        return

    op.create_table(
        "pay_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("out_trade_no", sa.String(length=64), nullable=False, unique=True),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("total_amount", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trade_no", sa.String(length=64), nullable=True),
        sa.Column("trade_status", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pay_transactions_created_at "
        "ON pay_transactions (created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pay_transactions_created_at")
    op.drop_table("pay_transactions")
