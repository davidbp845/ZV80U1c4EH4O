"""evento_calendario_id en citas

Revision ID: 4794f8eeb103
Revises: cfcefe4475b9
Create Date: 2026-08-07 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '4794f8eeb103'
down_revision: Union[str, Sequence[str], None] = 'cfcefe4475b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'citas',
        sa.Column('evento_calendario_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('citas', 'evento_calendario_id')
