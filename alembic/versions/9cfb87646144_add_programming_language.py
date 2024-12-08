"""add programming language

Revision ID: 9cfb87646144
Revises: c75a5cdda4fb
Create Date: 2024-11-25 20:14:56.407677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cfb87646144'
down_revision: Union[str, None] = 'c75a5cdda4fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('playground_code', sa.Column('programming_language', sa.String(), nullable=False, server_default='python'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('playground_code', 'programming_language')
    # ### end Alembic commands ###
