"""lecture models change

Revision ID: 0488018406fa
Revises: 66a8f7a0f948
Create Date: 2024-12-23 19:57:38.289760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0488018406fa'
down_revision: Union[str, None] = '66a8f7a0f948'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('lecture_main', sa.Column('embed_video_url', sa.String(), nullable=True))
    op.add_column('lecture_main', sa.Column('thumbnail_image_url', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('lecture_main', 'thumbnail_image_url')
    op.drop_column('lecture_main', 'embed_video_url')
    # ### end Alembic commands ###
