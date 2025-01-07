"""complete object

Revision ID: 313c38dbdf44
Revises: dd767085167c
Create Date: 2025-01-05 12:48:14.030673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '313c38dbdf44'
down_revision: Union[str, None] = 'dd767085167c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_created_lecture_question', sa.Column('complete', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_created_lecture_question', 'complete')
    # ### end Alembic commands ###