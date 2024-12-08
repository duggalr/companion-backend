"""update name schema for code

Revision ID: 7bad20f1f0b9
Revises: b45f06fda2c9
Create Date: 2024-12-03 22:26:38.862136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bad20f1f0b9'
down_revision: Union[str, None] = 'b45f06fda2c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('playground_object', 'unique_name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('playground_object', 'unique_name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###
