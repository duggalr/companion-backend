"""lecture models

Revision ID: 66a8f7a0f948
Revises: 600340a44e94
Create Date: 2024-12-23 12:14:18.268331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66a8f7a0f948'
down_revision: Union[str, None] = '600340a44e94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('lecture_main',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('video_url', sa.String(), nullable=True),
    sa.Column('notes_url', sa.String(), nullable=True),
    sa.Column('created_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('lecture_question', sa.Column('lecture_main_object_id', sa.UUID(), nullable=True))
    op.create_foreign_key(None, 'lecture_question', 'lecture_main', ['lecture_main_object_id'], ['id'])
    op.drop_column('lecture_question', 'lecture_name')
    op.drop_column('lecture_question', 'lecture_video_url')
    op.drop_column('lecture_question', 'lecture_notes_url')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('lecture_question', sa.Column('lecture_notes_url', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('lecture_question', sa.Column('lecture_video_url', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('lecture_question', sa.Column('lecture_name', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'lecture_question', type_='foreignkey')
    op.drop_column('lecture_question', 'lecture_main_object_id')
    op.drop_table('lecture_main')
    # ### end Alembic commands ###