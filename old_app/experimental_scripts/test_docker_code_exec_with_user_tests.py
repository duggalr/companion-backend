import os
import ast
import json
import docker


def execute_code_with_tests(language: str, code: str, test_cases: list, function_name: str):
    """
    Task to run user-submitted code with test cases inside a Docker container.
    """
    docker_image = {
        "python": "python:3.12-slim",
    }.get(language)

    if not docker_image:
        raise ValueError("Unsupported language")

    language_file_extension = {
        "python": ".py",
    }
    current_file_extension = language_file_extension.get(language)
    if not current_file_extension:
        raise ValueError("Unsupported language")

    # Write the user's code to a temporary file
    host_code_dir = "/tmp"  # Directory on the host
    code_file_name = f"submission_code{current_file_extension}"
    host_code_file = os.path.join(host_code_dir, code_file_name)

    # f"            output = func(*case['input']) if isinstance(case['input'], list) else func(case['input'])",

    # Generate a test harness for Python
    if language == "python":
        test_harness = "\n".join([
            "import json",
            "from typing import Any",
            f"def run_tests():",
            "    test_cases = " + json.dumps(test_cases),
            "    results = []",
            "    for case in test_cases:",
            f"        try:",
            f"            if '{function_name}' not in globals():",
            f"                raise NameError(f'Function \"{function_name}\" is not defined.')",
            f"            func = globals()['{function_name}']",
            f"            output = func(*case['input']) if isinstance(case['input'], list) else func(case['input'].strip(\"\\\"\"))",
            f"            results.append({{'input': case['input'], 'expected': case['expected_output'], 'actual': output, 'success': output == case['expected_output']}})",
            f"        except Exception as e:",
            f"            results.append({{'input': case['input'], 'expected': case['expected_output'], 'actual': None, 'error': str(e), 'success': False}})",
            "    print(json.dumps(results))",
            "run_tests()"
        ])
    else:
        raise ValueError("Currently, only Python is supported for test case execution.")

    # Combine user code and the test harness
    with open(host_code_file, "w") as f:
        f.write(code)
        if language == "python":
            f.write("\n")
            f.write(test_harness)

    container_code_file = f"/app/{code_file_name}"

    MAX_EXECUTION_TIME_IN_SECONDS = 10

    client = docker.from_env()

    exec_cmd = {
        "python": f"python {container_code_file}",
    }.get(language)

    result = None
    logs = ""
    try:
        container = client.containers.run(
            image=docker_image,
            command=exec_cmd,
            volumes={host_code_dir: {"bind": "/app", "mode": "rw"}},
            working_dir="/app",
            detach=True,
            user="nobody",
            read_only=True,
            network_mode="none",
            mem_limit="256m",
            cpu_period=100000,
            cpu_quota=50000,
            pids_limit=64,
            security_opt=["no-new-privileges"]
        )
        result = container.wait(timeout=MAX_EXECUTION_TIME_IN_SECONDS)
        logs = container.logs().decode("utf-8")
    except docker.errors.ContainerError as e:
        logs = f"Error: {str(e)}"
    except docker.errors.APIError as e:
        logs = f"Docker API Error: {str(e)}"
    except docker.errors.DockerException as e:
        logs = f"Docker Execution Error: {str(e)}"
    except Exception as e:
        logs = f"Unexpected Error: {str(e)}"
    finally:
        container.remove(force=True)

    if result is not None and result["StatusCode"] == 0:
        try:
            # Parse the JSON results from the logs
            test_results = json.loads(logs)
            return {"success": True, "test_results": test_results}
        except json.JSONDecodeError:
            return {"success": False, "error": "Failed to parse test results", "logs": logs}
    else:
        return {"success": False, "error": "Code execution failed", "logs": logs}



def extract_function_names(code):
    """
    Parse the code and extract top-level function names.
    """
    try:
        tree = ast.parse(code)
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        return functions
    except SyntaxError as e:
        return {"error": f"Code contains a syntax error: {str(e)}"}


def infer_main_function(functions):
    """
    Infer the main function from a list of function names.
    """
    if not functions:
        return None
    if len(functions) == 1:
        return functions[0]
    # Heuristics for selecting the main function
    likely_main = [f for f in functions if not f.startswith('_')]  # Exclude private/helper functions
    return likely_main[0] if likely_main else functions[0]


code = """
def is_prime_trial_division(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
"""

test_cases_list = [
    { 'input': 11, 'expected_output': 'True' },
    { 'input': 7, 'expected_output': 'True' },
    { 'input': 4, 'expected_output': 'False' },
]

function_names = extract_function_names(
    code = code
)
print(f"Function Names: {function_names}")
function_name = infer_main_function(function_names)

result = execute_code_with_tests(
    language = 'python',
    code = code,
    test_cases = test_cases_list,
    function_name = function_name
)
print(result)

# # TODO:
    # having dynamically generated test-cases that work robustly is challenging (a lot of cases we need to consider here and will take time...)
    # disable submission feature on "general-page" for next launch
    # focus only on pre-created test-cases and submission for MIT Course



# function_name = "find_palindromic_substrings"
# test_harness = "\n".join([
#     "import json",
#     "from typing import Any",
#     f"def run_tests():",
#     "    test_cases = " + json.dumps(test_cases_list),
#     "    results = []",
#     "    for case in test_cases:",
#     f"        try:",
#     f"            if '{function_name}' not in globals():",
#     f"                raise NameError(f'Function \"{function_name}\" is not defined.')",
#     f"            func = globals()['{function_name}']",
#     f"            output = func(*case['input']) if isinstance(case['input'], list) else func(case['input'].strip(\"\\\"\"))",
#     f"            results.append({{'input': case['input'], 'expected': case['expected_output'], 'actual': output, 'success': output == case['expected_output']}})",
#     f"        except Exception as e:",
#     f"            results.append({{'input': case['input'], 'expected': case['expected_output'], 'actual': None, 'error': str(e), 'success': False}})",
#     "    print(json.dumps(results))",
#     "run_tests()"
# ])
# print(test_harness)


# import json
# from typing import Any

# def run_tests():
#     test_cases = [{"input": "\"abba\"", "expected_output": ["a", "b", "bb", "abba"]}, {"input": "\"racecar\"", "expected_output": ["r", "a", "c", "e", "cec", "aceca", "racecar"]}, {"input": "\"abc\"", "expected_output": ["a", "b", "c"]}, {"input": "\"a\"", "expected_output": ["a"]}, {"input": "\"\"", "expected_output": []}, {"input": "\"madamimadam\"", "expected_output": ["m", "a", "d", "madam", "a", "m", "i", "madamimadam", "a", "d", "madam", "a", "m"]}, {"input": "\"xyzzyx\"", "expected_output": ["x", "y", "z", "zz", "yzz", "xyzzyx"]}, {"input": "\"noonracecar\"", "expected_output": ["n", "o", "noon", "o", "n", "r", "a", "c", "e", "cec", "aceca", "racecar"]}, {"input": "\"abcbabcba\"", "expected_output": ["a", "b", "c", "bcb", "abcba", "bcbabcba", "b", "a"]}, {"input": "\"xyzyxxyzz\"", "expected_output": ["x", "y", "z", "yzy", "xyzyx", "x", "y", "zz", "xyzz"]}]
#     results = []
#     for case in test_cases:
#         try:
#             if 'find_palindromic_substrings' not in globals():
#                 raise NameError(f'Function "find_palindromic_substrings" is not defined.')
#             func = globals()['find_palindromic_substrings']
#             output = func(*case['input']) if isinstance(case['input'], list) else func(case['input'].strip("\""))
#             results.append({'input': case['input'], 'expected': case['expected_output'], 'actual': output, 'success': output == case['expected_output']})
#         except Exception as e:
#             results.append({'input': case['input'], 'expected': case['expected_output'], 'actual': None, 'error': str(e), 'success': False})
#     print(json.dumps(results))

# run_tests()


# # { 'input': '"abba"', 'expected_output': ["a", "b", "bb", "abba"] },
# #     { 'input': '"racecar"', 'expected_output': ["r", "a", "c", "e", "cec", "aceca", "racecar"] },
# #     { 'input': '"abc"', 'expected_output': ["a", "b", "c"] },
# #     { 'input': '"a"', 'expected_output': ["a"] },
# #     { 'input': '""', 'expected_output': [] },
# #     { 'input': '"madamimadam"', 'expected_output': ["m", "a", "d", "madam", "a", "m", "i", "madamimadam", "a", "d", "madam", "a", "m"] },
# #     { 'input': '"xyzzyx"', 'expected_output': ["x", "y", "z", "zz", "yzz", "xyzzyx"] },
# #     { 'input': '"noonracecar"', 'expected_output': ["n", "o", "noon", "o", "n", "r", "a", "c", "e", "cec", "aceca", "racecar"] },
# #     { 'input': '"abcbabcba"', 'expected_output': ["a", "b", "c", "bcb", "abcba", "bcbabcba", "b", "a"] },
# #     { 'input': '"xyzyxxyzz"', 'expected_output': ["x", "y", "z", "yzy", "xyzyx", "x", "y", "zz", "xyzz"] }