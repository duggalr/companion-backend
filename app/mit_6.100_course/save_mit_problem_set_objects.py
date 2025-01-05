import json
import sys
sys.path.append('/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend')
from app.database import SessionLocal
from app.models import ProblemSetQuestion, LectureQuestion, LectureMain

db = SessionLocal()

problem_set_fp_list = [
    "/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend/app/mit_6.100_course/problem_set_json_files/problem_set_one_representation.json",
    "/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend/app/mit_6.100_course/problem_set_json_files/problem_set_three_representation.json",
    "/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend/app/mit_6.100_course/problem_set_json_files/problem_set_four_representation.json"
]
for ps_json_fp in problem_set_fp_list:
    with open(ps_json_fp, 'r', encoding='utf-8') as file:
        data = json.load(file)

    lecture_number = data['lecture_number']
    problem_set_number = data['problem_set_number']
    problem_set_name = data['problem_set_name']
    problem_set_url = data['problem_set_url']

    lecture_main_object = db.query(LectureMain).filter(
        LectureMain.number == lecture_number
    ).first()

    print("Saving Problem Set...")
    problem_set_object = ProblemSetQuestion(
        ps_number = problem_set_number,
        ps_name = problem_set_name,
        ps_url = problem_set_url,
        lecture_main_object_id = lecture_main_object.id
    )
    db.add(problem_set_object)
    db.commit()
    db.refresh(problem_set_object)

    print("Saving questions associated with the problem set...")
    problems_list = data['problems']
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
            test_case_list = test_case_list,

            function_name = pdict.get('function_name', None),
            class_name = pdict.get('class_name', None),
            test_function_name = test_function_name,

            question_type = "problem_set",
            problem_set_part = pdict['part'],
            problem_set_number = problem_set_number,

            lecture_main_object_id = lecture_main_object.id,
        )
        db.add(ps_lecture_question_obj)
        db.commit()
        db.refresh(ps_lecture_question_obj)
