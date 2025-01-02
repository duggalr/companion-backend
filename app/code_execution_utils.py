import os
import ast
import math
import docker


def execute_code_in_container(language: str, code: str):
    """
    Task to run user-submitted code inside a Docker container.
    """
    # Set up language-specific Docker image
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

    with open(host_code_file, "w") as f:
        f.write(code)

    # The code will be placed in the /app directory inside the container
    container_code_file = f"/app/{code_file_name}"

    MAX_EXECUTION_TIME_IN_SECONDS = 10

    # Initialize Docker client
    client = docker.from_env()

    # Command to run inside the container
    exec_cmd = {
        "python": f"python {container_code_file}",
    }.get(language)

    result = None
    try:
        container = client.containers.run(
            image = docker_image,
            command = exec_cmd,
            volumes = {host_code_dir: {"bind": "/app", "mode": "rw"}}, # Mount directory
            working_dir = "/app",
            detach = True,
            user = "nobody",
            read_only = True,
            network_mode = "none",
            mem_limit = "256m",
            cpu_period = 100000,
            cpu_quota = 50000,
            pids_limit = 64,
            security_opt = ["no-new-privileges"]
        )
        result = container.wait(
            timeout = MAX_EXECUTION_TIME_IN_SECONDS
        )
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
        # Clean up the container
        container.remove(force=True)

    if result is not None:
        if result["StatusCode"] == 0:
            return {"success": True, "output": logs}
        else:
            return {"success": False, "output": logs}
    else:
        return {"success": False, "output": logs}


def _compute_eval_result_dict(execution_result, code_expected_output, function_params_string):
    rv_dict = {}

    if execution_result["success"]:
        # Extract and sanitize the actual output
        actual_output = execution_result["output"].strip()

        # Attempt to convert actual_output to match the expected type
        try:
 
            # Convert to boolean if the actual output is a boolean-like string
            if actual_output.lower() == "true":
                actual_output = True
            elif actual_output.lower() == "false":
                actual_output = False
            elif actual_output.lower() == "none":
                actual_output = None
            else:
                # Attempt numeric conversion
                try:
                    actual_output = int(actual_output)
                except ValueError:
                    actual_output = float(actual_output)
        except ValueError:
            # Leave as string if no conversion applies
            pass


        if isinstance(actual_output, str) and (actual_output.startswith("(") or actual_output.startswith("[")):
            actual_output = ast.literal_eval(actual_output)

        if isinstance(code_expected_output, str) and (code_expected_output.startswith("(") or code_expected_output.startswith("[")):
            code_expected_output = ast.literal_eval(code_expected_output)


        # Populate the result dictionary
        rv_dict['program_output'] = actual_output
        rv_dict['expected_output'] = code_expected_output
        rv_dict['test_input_to_code'] = function_params_string

        # Compare actual and expected output with type consideration
        if isinstance(code_expected_output, list):
            # Handle list comparison
            if isinstance(actual_output, list) and len(actual_output) == len(code_expected_output):
                rv_dict['correct'] = 'yes' if all(a == b for a, b in zip(actual_output, code_expected_output)) else 'no'
            else:
                rv_dict['correct'] = 'no'
        else:
            if isinstance(actual_output, float):
                if math.isclose(actual_output, code_expected_output) is True:
                    rv_dict['correct'] = 'yes'
                else:
                    rv_dict['correct'] = 'no'
            else:
                # Handle scalar and boolean comparison
                if actual_output == code_expected_output:
                    rv_dict['correct'] = 'yes'
                else:
                    rv_dict['correct'] = 'no'
                    print(f"Type Mismatch: Actual ({type(actual_output)}), Expected ({type(code_expected_output)})")
                    print(f"Value Mismatch: Actual ({actual_output}), Expected ({code_expected_output})")
    else:
        # Mark as failed if execution didn't succeed
        rv_dict['correct'] = 'no'
        rv_dict['error'] = execution_result.get("error", "Unknown error")

    return rv_dict


def run_test_cases_without_function(user_code: str, test_case_list: list):
    """
    Run test cases for the given code and return results as a list of 'yes' or 'no'.

    For this, the variables will be inserted at the top of the user's code.
    From there, the code will execute and run.

    Critical the user's code does not have pre-hardcoded variables.
    """
    results = []
    for tc_dict in test_case_list:
        code_input = tc_dict['input']
        code_expected_output = tc_dict['expected_output']
        code_input_string = '\n'.join([f"{k} = {repr(code_input[k])}" for k in code_input])
        full_code = code_input_string + '\n' + user_code

        execution_result = execute_code_in_container(
            language = 'python',
            code = full_code
        )

        rv_dict = _compute_eval_result_dict(
            execution_result=execution_result,
            code_expected_output=code_expected_output,
            function_params_string=code_input_string
        )
        results.append(rv_dict)

    return results


def run_test_cases_with_function(user_code: str, function_name: str, test_case_list: list):
    results = []
    for tc_dict in test_case_list:
        code_input = tc_dict['input']
        code_expected_output = tc_dict['expected_output']

        # function_params_string = ", ".join([f"{k}={repr(code_input[k])}" for k in code_input])
        parsed_input = {
            k: eval(v) if isinstance(v, str) and v.startswith("[lambda") else
            ast.literal_eval(v) if isinstance(v, str) and (v.startswith("(") or v.startswith("[")) else
            v
            for k, v in code_input.items()
        }
        function_params_string = ", ".join([f"{k}={repr(parsed_input[k])}" for k in parsed_input])
        function_call = f"print({function_name}({function_params_string}))\n"
        full_code_to_call = user_code + '\n\n' + function_call

        execution_result = execute_code_in_container(
            'python',
            full_code_to_call
        )

        rv_dict = _compute_eval_result_dict(
            execution_result=execution_result,
            code_expected_output=code_expected_output,
            function_params_string=function_call
        )
        results.append(rv_dict)

    return results

# user_code = """def eval_quadratic(a, b, c, x):
#     """
#     Evaluates a quadratic equation at a given value.

#     Args:
#         a (float): Coefficient of the quadratic term (x^2).

#     # Your code here
#     """

#     return a * (x**2) + b * (x) + c
# """
# test_case_list = [{'input': {'a': 1, 'b': 1, 'c': 1, 'x': 1}, 'expected_output': 3}, {'input': {'a': 2, 'b': -4, 'c': 0, 'x': 2}, 'expected_output': 0}, {'input': {'a': 0, 'b': 0, 'c': 0, 'x': 0}, 'expected_output': 0}, {'input': {'a': 1, 'b': 0, 'c': -1, 'x': 0}, 'expected_output': -1}, {'input': {'a': 3, 'b': 2, 'c': 1, 'x': -1}, 'expected_output': 2}]
# run_test_cases_with_function(
#     user_code = user_code,
#     function_name = 'eval_quadratic',
#     test_case_list = test_case_list
# )

def run_test_cases_with_class(user_code: str, class_name: str, test_case_list: list):
    results = []
    for tc_dict in test_case_list:
        tc_method = tc_dict['method_to_test']
        tc_input_dict = tc_dict['input']

        class_initialization_value_dict = tc_dict['class_initialization_value']

        # class_initialization_value_string = ", ".join([repr(class_initialization_value_dict[k]) for k in class_initialization_value_dict]).strip()
        class_initialization_value_string = ", ".join([
            repr(value) if isinstance(value, (str, int, float, bool)) else str(value)
            for value in class_initialization_value_dict.values()
        ]).strip()
        class_call_string = f"{class_name}({class_initialization_value_string})"

        if 'input_type' in tc_dict:
            tc_input_type = tc_dict['input_type']
            # tc_output_type = tc_dict['output_type']
            if tc_input_type == 'class_object':
                
                input_class_param_initialization_string = ", ".join([
                    repr(tc_input_dict[k]) if isinstance(tc_input_dict[k], (str, int, float, bool)) else str(tc_input_dict[k])
                    for k in tc_input_dict
                ]).strip()
                input_class_object_initialization_string = f"{class_name}({input_class_param_initialization_string})"
                method_call_string = f"print({class_call_string}.{tc_method}({input_class_object_initialization_string}))"
                
                full_code = user_code + '\n\n' + method_call_string
                # print(full_code)

                # execution_result = execute_code_in_container(
                #     language = 'python',
                #     code = full_code
                # )
                # print(type(execution_result['output']))
                # rv_dict = _compute_eval_result_dict(
                #     execution_result = execution_result,
                #     code_expected_output = tc_dict['expected_output'],
                #     function_params_string = method_call_string
                # )
                # print(rv_dict)
        else:
            # method_call_input_param_string = ", ".join([repr(tc_input_dict[k]) for k in tc_input_dict]).strip()
            method_call_input_param_string = ", ".join([
                repr(value) if isinstance(value, (str, int, float, bool)) else str(value)
                for value in tc_input_dict.values()
            ]).strip()
            method_call_string = f"print({class_call_string}.{tc_method}({method_call_input_param_string}))"

            full_code = user_code + "\n\n" + method_call_string

        # code execution
        execution_result = execute_code_in_container(
            language = 'python',
            code = full_code
        )

        rv_dict = _compute_eval_result_dict(
            execution_result = execution_result,
            code_expected_output = tc_dict['expected_output'],
            function_params_string = method_call_string
        )
        results.append(rv_dict)

    return results
