import pprint
import json

# with open('lecture_exercises.json', 'r') as file:
#     data = json.load(file)

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

# rw = data[0]
# pprint.pprint(rw, compact=True)

import sys
sys.path.append('/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend')
from app.models import LectureQuestion
from app.database import SessionLocal

db = SessionLocal()

question_dict = {
        "name": "Finger Exercise Lecture 1",
        "exercise": "Assume three variables are already defined for you: a, b, and c. Create a variable called total that adds a and b then multiplies the result by c. Include a last line in your code to print the value: print(total)",
        "mit_correct_solution": """total = (a + b) * c
print(total)""",
        "lecture_name": "Introduction to Python",
        "lecture_video_url": "https://www.youtube.com/watch?v=xAcTmDO6NTI&ab_channel=MITOpenCourseWare",
        "lecture_notes_url": "https://ocw.mit.edu/courses/6-100l-introduction-to-cs-and-programming-using-python-fall-2022/resources/mit6_100l_f22_lec01_pdf/",
        "input_output_list": """[
            {
                "input": "a = 2, b = 3, c = 4",
                "output": "20",
                "explanation": "First, add a and b: 2 + 3 = 5. Then, multiply the result by c: 5 * 4 = 20. The value of total is 20."
            },
            {
                "input": "a = 5, b = 5, c = 2",
                "output": "20",
                "explanation": "First, add a and b: 5 + 5 = 10. Then, multiply the result by c: 10 * 2 = 20. The value of total is 20."
            },
            {
                "input": "a = 1, b = 6, c = 3",
                "output": "21",
                "explanation": "First, add a and b: 1 + 6 = 7. Then, multiply the result by c: 7 * 3 = 21. The value of total is 21."
            }
        ]""",
        "starter_code": "# TODO: write your code here"
    }

lq_object = LectureQuestion(
    name = question_dict['name'],
    text = question_dict['exercise'],
    example_io_list = question_dict['input_output_list'],
    lecture_name = question_dict['lecture_name'],
    lecture_video_url = question_dict['lecture_video_url'],
    lecture_notes_url = question_dict['lecture_notes_url'],
    correct_solution = question_dict['mit_correct_solution']
)
db.add(lq_object)
db.commit()
db.refresh(lq_object)

