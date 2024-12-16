
GENERATE_INPUT_OUTPUT_EXAMPLE_PROMPT = """## Instructions:
For the given question below, your task is to generate:
- 3 Distinct Input / Output Examples with a 1-2 line description / explanation for each example to be shown to the user, to help them better understand the question.

Return the following JSON dictionary, with the specified format below.
- For cases where you need to generate an input / output dictionary containing multiple parameters or value, please encapsulate the dictionary as a string.

## Example Output Format:
{
    "input_output_example_list": [{"input": "...", "output": "...", "explanation": "..."}, ...]
}

## Data:
"""