import json
import sys
sys.path.append('/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend')
from app.database import SessionLocal
from app.models import ProblemSetQuestion, LectureQuestion, LectureMain

db = SessionLocal()

ps_json_fp = '/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend/app/mit_6.100_course/problem_set_json_files/problem_set_one_representation.json'
with open(ps_json_fp, 'r', encoding='utf-8') as file:
    data = json.load(file)

tmp_lecture_main_object = db.query(LectureMain).filter(
    LectureMain.number == 1
).first()
print('Lecture Object:', tmp_lecture_main_object)

problems_list = data['problems']
# print(problems_list[0])

problem_set_object = ProblemSetQuestion(
    ps_number = 1,
    ps_name = 'Problem Set 1: Compound Interest',
    lecture_main_object_id = tmp_lecture_main_object.id
)
db.add(problem_set_object)
db.commit()
db.refresh(problem_set_object)

for pdict in problems_list:
    print(f"Saving question {pdict['name']}")

    if 'test_case_list' in pdict:
        test_case_list = str(pdict['test_case_list'])
        test_function_name = pdict['test_function_name']
    else:
        test_case_list = str([])
        test_function_name = ""

    ps_lecture_question_obj = LectureQuestion(
        name = pdict['name'],
        text = pdict['exercise'],

        example_io_list = str(pdict['input_output_list']),
        starter_code = pdict['starter_code'],
        correct_solution = pdict['mit_correct_solution'],

        function_name = pdict.get('function_name', None),
        class_name = pdict.get('class_name', None),

        test_case_list = test_case_list,
        test_function_name = test_function_name,

        # TODO: Problem Set
        question_type = "problem_set",
        problem_set_part = pdict['part'],
        problem_set_number = 1,  # TODO: manually hardcoded for now

        lecture_main_object_id = tmp_lecture_main_object.id,
    )
    db.add(ps_lecture_question_obj)
    db.commit()
    db.refresh(ps_lecture_question_obj)


# {'problem_set_number': 1, 'problem_set_name': 'Problem Set 1: Compound Interest', 'part': 'A', 'name': 'Problem Set #1 - Part A', 'exercise': 'Write a function to calculate the number of months required to save for a down payment given the yearly salary, portion saved, and cost of a dream home. Assume an annual return rate of 0.05 and a down payment percentage of 0.25.', 'starter_code': 'def calculate_months_to_save(yearly_salary, portion_saved, cost_of_dream_home):\n    # Your code here\n    pass', 'mit_correct_solution': 'TODO:', 'function_name': 'calculate_months_to_save', 'input_output_list': [{'input': {'yearly_salary': 112000, 'portion_saved': 0.17, 'cost_of_dream_home': 750000}, 'output': 97}, {'input': {'yearly_salary': 65000, 'portion_saved': 0.2, 'cost_of_dream_home': 400000}, 'output': 79}, {'input': {'yearly_salary': 350000, 'portion_saved': 0.3, 'cost_of_dream_home': 10000000}, 'output': 189}], 'test_case_list': [{'yearly_salary': 112000, 'portion_saved': 0.17, 'cost_of_dream_home': 750000, 'expected': 97}, {'yearly_salary': 65000, 'portion_saved': 0.2, 'cost_of_dream_home': 400000, 'expected': 79}, {'yearly_salary': 350000, 'portion_saved': 0.3, 'cost_of_dream_home': 10000000, 'expected': 189}], 'test_function_name': 'run_test_cases_without_function'}

# for rw in data:
#     lec_num, lec_name = rw['lecture_number'], rw['lecture_name']

#     print(f"Saving lecture {lec_num} with name {lec_name}")
#     lm_object = LectureMain(
#         number = rw['lecture_number'],
#         name = rw['lecture_name'],
#         description = rw['lecture_description'],
#         # video_url = rw['lecture_video_url'],
#         notes_url = rw['lecture_notes_url'],
#         video_url = rw['lecture_video_url'],
#         embed_video_url = rw['lecture_embed_video_url'],
#         thumbnail_image_url = rw['lecture_thumbnail_image_url'],
#         code_url = rw['lecture_code_url']
#     )
#     db.add(lm_object)
#     db.commit()
#     db.refresh(lm_object)



# with open('lecture_exercises.json', 'r', encoding='utf-8') as file:
#     data = json.load(file)

# print(f"Number of Examples: {len(data)}")
# for rw in data:
#     lec_num, lec_name = rw['lecture_number'], rw['lecture_name']

#     print(f"Saving lecture {lec_num} with name {lec_name}")
#     lm_object = LectureMain(
#         number = rw['lecture_number'],
#         name = rw['lecture_name'],
#         description = rw['lecture_description'],
#         # video_url = rw['lecture_video_url'],
#         notes_url = rw['lecture_notes_url'],
#         video_url = rw['lecture_video_url'],
#         embed_video_url = rw['lecture_embed_video_url'],
#         thumbnail_image_url = rw['lecture_thumbnail_image_url'],
#         code_url = rw['lecture_code_url']
#     )
#     db.add(lm_object)
#     db.commit()
#     db.refresh(lm_object)

#     print(f"Saving question {rw['name']}")
#     if 'test_case_list' in rw:
#         test_case_list = str(rw['test_case_list'])
#         test_function_name = rw['test_function_name']
#     else:
#         test_case_list = str([])
#         test_function_name = ""

#     lq_object = LectureQuestion(
#         name = rw['name'],
#         text = rw['exercise'],
#         example_io_list = str(rw['input_output_list']),
#         starter_code = rw['starter_code'],
#         correct_solution = rw['mit_correct_solution'],

#         function_name = rw.get('function_name', None),
#         class_name = rw.get('class_name', None),

#         test_case_list = test_case_list,
#         test_function_name = test_function_name,
#         lecture_main_object_id = lm_object.id,
#     )
#     db.add(lq_object)
#     db.commit()
#     db.refresh(lq_object)