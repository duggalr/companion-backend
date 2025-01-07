"""complete object

Revision ID: 8913a271f429
Revises: 313c38dbdf44
Create Date: 2025-01-05 13:15:30.076540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8913a271f429'
down_revision: Union[str, None] = '313c38dbdf44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('problem_set_question', sa.Column('ps_url', sa.String(), nullable=False))
    op.alter_column('problem_set_question', 'ps_number',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('problem_set_question', 'ps_name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_constraint('problem_set_question_ps_name_key', 'problem_set_question', type_='unique')
    op.create_unique_constraint(None, 'problem_set_question', ['ps_url'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'problem_set_question', type_='unique')
    op.create_unique_constraint('problem_set_question_ps_name_key', 'problem_set_question', ['ps_name'])
    op.alter_column('problem_set_question', 'ps_name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('problem_set_question', 'ps_number',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_column('problem_set_question', 'ps_url')
    # ### end Alembic commands ###