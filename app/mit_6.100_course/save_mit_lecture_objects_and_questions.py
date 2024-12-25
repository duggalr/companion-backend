import json
import sys
sys.path.append('/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend')
from app.database import SessionLocal
from app.models import LectureMain, LectureQuestion

db = SessionLocal()

with open('lecture_exercises.json', 'r') as file:
    data = json.load(file)

print(f"Number of Examples: {len(data)}")
for rw in data:
    lec_num, lec_name = rw['lecture_number'], rw['lecture_name']
    
    print(f"Saving lecture {lec_num} with name {lec_name}")
    lm_object = LectureMain(
        number = rw['lecture_number'],
        name = rw['lecture_name'],
        description = rw['lecture_description'],
        # video_url = rw['lecture_video_url'],
        notes_url = rw['lecture_notes_url'],
        video_url = rw['lecture_video_url'],
        embed_video_url = rw['lecture_embed_video_url'],
        thumbnail_image_url = rw['lecture_thumbnail_image_url'],
        code_url = rw['lecture_code_url']
    )
    db.add(lm_object)
    db.commit()
    db.refresh(lm_object)

    print(f"Saving question {rw['name']}")
    lq_object = LectureQuestion(
        name = rw['name'],
        text = rw['exercise'],
        example_io_list = str(rw['input_output_list']),
        starter_code = rw['starter_code'],
        correct_solution = rw['mit_correct_solution'],
        test_case_list = str(rw['test_case_list']),
        lecture_main_object_id = lm_object.id,
    )
    db.add(lq_object)
    db.commit()
    db.refresh(lq_object)

