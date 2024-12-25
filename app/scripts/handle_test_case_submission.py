import os
import docker
import pprint
import json


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
    # code_file_name = "submission_code.py"  # Name of the file
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


def run_test_cases(language: str, code: str, test_cases: list):
    """
    Run test cases for the given code and return results as a list of 'yes' or 'no'.
    """
    results = []
    for test in test_cases:
        # Prepare the test inputs as Python variables
        input_code = "\n".join([
    f"{key} = {repr(value)}" for key, value in test.items() if key != "expected_output"
])

        # Combine the test inputs with the solution code
        full_code = input_code + "\n" + code

        # Execute the code in the container
        execution_result = execute_code_in_container(language, full_code)
        
        rv_dict = {}
        if execution_result["success"]:
            # Extract the output and compare with the expected output
            actual_output = execution_result["output"].strip()
            # print('actual_output:', actual_output)
            
            # Try to convert the actual output to a numeric type first (integer or float)
            try:
                actual_output = int(actual_output)  # Try converting to int
            except ValueError:
                try:
                    actual_output = float(actual_output)  # Try converting to float
                except ValueError:
                    pass  # If it's not a number, leave as string
            
            expected_output = test["expected_output"]

            rv_dict['program_output'] = actual_output
            rv_dict['expected_output'] = expected_output
            rv_dict['test_input_to_code'] = input_code

            # Compare actual and expected output, considering possible data type mismatches
            if isinstance(expected_output, list):
                # If the expected output is a list, compare the lists element by element
                if isinstance(actual_output, list) and len(actual_output) == len(expected_output):
                    if all(a == b for a, b in zip(actual_output, expected_output)):
                        # results.append("yes")
                        rv_dict['correct'] = 'yes'
                    else:
                        # results.append("no")
                        rv_dict['correct'] = 'no'
                else:
                    # results.append("no")
                    rv_dict['correct'] = 'no'
            else:
                # print(actual_output, expected_output, type(actual_output), type(expected_output))
                
                # Compare the outputs directly (for non-list types like int, float, string)
                if actual_output == expected_output:
                    # results.append("yes")
                    rv_dict['correct'] = 'yes'
                else:
                    rv_dict['correct'] = 'no'
                    # results.append("no")
                    # # print(actual_output, expected_output, type(actual_output), type(expected_output))
                    print(f"Actual: {actual_output}")
                    print(f"Expected: {expected_output}")
        
        else:
            # # If execution failed, mark the test as failed
            # results.append("no")
            rv_dict['correct'] = 'no'

        results.append(rv_dict)

    return results


# code_str = """a = 5
# b = 10
# c = 0
# print((a * b) + c)
# """

# question_literal_tc_list = [
#     {"input": {"a": 1, "b": 2, "c": 3}, "expected_output": 9},
#     {"input": {"a": -1, "b": 2, "c": 3}, "expected_output": 3},
#     {"input": {"a": -1, "b": -2, "c": -3}, "expected_output": 9},
#     {"input": {"a": 0, "b": 0, "c": 5}, "expected_output": 0},
#     {"input": {"a": 5, "b": 10, "c": 0}, "expected_output": 0},
#     {"input": {"a": 1000000, "b": 2000000, "c": 3000000}, "expected_output": 9000000000000},
#     {"input": {"a": 1.5, "b": 2.5, "c": 2}, "expected_output": 8.0},
#     {"input": {"a": 1, "b": 2.5, "c": 2}, "expected_output": 7.0},
#     {"input": {"a": 1, "b": 1, "c": 1}, "expected_output": 2}
# ]
# tc_return_list = []
# for tc_di in question_literal_tc_list:
#     input_tc_dict = tc_di['input']
#     tc_return_list.append({'input': input_tc_dict, "expected_output": tc_di["expected_output"]})

# # print(tc_return_list)

# output = run_test_cases(
#     language = 'python',
#     code = code_str,
#     test_cases = tc_return_list
# )
# print(output)

