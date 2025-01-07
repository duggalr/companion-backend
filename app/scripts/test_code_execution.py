import json
import sys
sys.path.append('/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend')
from app.code_execution_utils import run_test_cases_without_function, run_test_cases_with_function, run_test_cases_with_class

lecture_exercises_json_fp = '/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend/app/mit_6.100_course/lecture_exercises.json'
with open(lecture_exercises_json_fp, 'r') as f:
    data = json.load(f)

for rw in data:
    if 'test_case_list' not in rw:
        print(f'No test cases for {rw['name']}')

    else:
        function_name = rw.get('function_name', "").strip()
        class_name = rw.get('class_name', None)
        
        if len(function_name) > 0:  # function testing
            correct_solution = rw['mit_correct_solution'].strip()
            test_case_list = rw['test_case_list']
            value = run_test_cases_with_function(
                user_code = correct_solution,
                function_name = function_name,
                test_case_list = test_case_list
            )
            total_count = len(value)
            total_correct = 0
            for result in value:
                if result['correct'] == 'yes':
                    total_correct += 1

            print(f"For Function: {function_name} | Results: {total_correct / total_count}")

        else:
            if function_name == "" and class_name is None:
                correct_solution = rw['mit_correct_solution'].strip()
                test_case_list = rw['test_case_list']
                value = run_test_cases_without_function(
                    user_code = correct_solution,
                    test_case_list = test_case_list
                )
                total_count = len(value)
                total_correct = 0
                for result in value:
                    if result['correct'] == 'yes':
                        total_correct += 1

                print(f"For Exercise: {rw['name']} | Results: {total_correct / total_count}")

            else:
                if class_name is not None:
                    class_name = class_name.strip()
                    # print(f"On Class Name: {class_name}")
                    test_case_list = rw['test_case_list']
                    correct_solution = rw['mit_correct_solution'].strip()
                    # print(f"Solution: {correct_solution}")

                    value = run_test_cases_with_class(
                        user_code = correct_solution,
                        class_name = class_name,
                        test_case_list = test_case_list
                    )
                    total_count = len(value)
                    total_correct = 0
                    for result in value:
                        if result['correct'] == 'yes':
                            total_correct += 1

                    print(f"For Class: {class_name} | Results: {total_correct / total_count}")
