import pprint
import json


with open('lecture_exercises.json', 'r') as file:
    data = json.load(file)

# for item in data:
#     print(f"Exercise:\n{item['exercise']}\n")
#     print(f"Solution:\n{item['mit_code_solution']}")
#     print("\n\n")
#     print('------------------------------------------------')
#     print("\n\n")


# TODO:
 # start here by inserting the first question into the db model
 # display on frontend
 # implement functionality
 # go from there
    # will need 'course user homepage' --> checkmarks, etc. for questions they finished or did not complete, etc.

rw = data[0]
pprint.pprint(rw, compact=True)

import sys
sys.path.append('/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend')
from app.models import LectureQuestion
from app.database import SessionLocal

db = SessionLocal()

lq_object = LectureQuestion(
    name = rw['name'],
    text = rw['exercise'],
    example_io_list = rw['input_output_list'],
    lecture_name = rw['lecture_name'],
    lecture_video_url = rw['lecture_video_url'],
    lecture_notes_url = rw['lecture_notes_url'],
    correct_solution = rw['mit_correct_solution']
)
db.add(lq_object)
db.commit()
db.refresh(lq_object)

