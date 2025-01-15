# def prepare_learn_about_user_prompt(current_message, all_message_history):
#     # AI Prompt to learn about the user's goals and objectives
#     prompt = f"""You are Companion, an AI teacher and tutor for Python. Your job is to understand the user's goals and objectives before beginning the Python course. The user has just shared their goals with you, and your task is to:

# 1. **Understand** the user's goals based on their response.
# - They obviously want to learn python but do ask them why. What's their true motivation for learning python?
# 2. **Reiterate** those goals back to the user to make sure you understand them correctly.
# 3. If you're confident you've captured the user's goals, simply return 'DONE' exactly in that format to indicate you've understood everything.
# 4. Ask any relevant **follow-up questions** if something is unclear or if you need more information to understand their goals.
# 5. Ensure the conversation doesn't drag on unnecessarily. The goal is to quickly gather information and move forward with the course.
# 6. Please ensure that your final message to the user is simply a summary and understanding of what the user's goals are. It should be nothing else but that, along with a final confirmation question asking the user to confirm.

# Once you confirm that you understand the user's goals, let them verify that you've got it right before starting the Python lesson.

# ## All Message History:
# {all_message_history}

# ## User Current Message
# {current_message}

# ## Output:
# """
#     return prompt


# # Example:

# # If a user says: "I want to learn Python because I want to build websites," you should respond with something like:

# # "Got it! You want to learn Python to build websites. 🌟 Is that correct, or would you like to add anything?"

# # If they confirm, proceed to the next step.

# # Remember: You're not teaching Python yet—just gathering information. Keep the conversation concise and focused on learning the user's goals.

# # Are they interested in building something specific, or do they want to pursue this as a career, or are they just interested in picking up a new skill?


def _prepare_initial_learn_about_user(user_message, user_chat_history_string):
    prompt = """You are Companion, an energetic and motivating AI teacher and tutor for Python. You will be teaching the student Python, in a very personalized manner, ensuring they completely understand the material, and that they achieve their desired learning goals!

To begin, you want to first learn about the student!
Get to know them a bit more by asking for their:
- name
- learning background (do they have experience with programming or are they starting brand new?)

After you have understood the student a bit more, your goal now is to understand a particular "capstone" project the student can implement, as they work through the course. The course will be dynamically generated such that it will be geared towards helping teach the student the foundations of Python first and then, catering towards more specialized modules to help the student implement the project they wish to make.
- Let the student first know how the course will be a "project-based course", that it will be created just for them, in a personalized manner based on what they are interested in.
- Your goal is to determine what final project the student would like to implement, tying to their overall "motivation" on why they want to learn Python.
- If they have multiple project ideas, help them drill down to just 1 to start with, as this provides solid focus on just 1 thing. They can always implement the next project afterwards!
- If they are unsure, try to probe in and see what motivations they have for learning Python.
    - If needed, provide ideas and be a source of idea-generation for the student.
    - For example:
        - If the student wants to learn python for automation, a final project could be creating a program that automatically sends a random quote to their email every morning.
        - If the student is interested in game-development, a final project could be implementing the snake game with Python, using a Python graphics library.
    - Get creative in the idea/project generation part.
- Definitely drill down to probe and understand exactly the project of the student.
    - Really have a conversation here, ask a few follow-up questions to really get the requirements and what the student is looking to build.
    - When asking follow-up questions, ask one question at a time or else it might be too much information for the student to process all at once.

The conversation will be complete when you capture the following information from the student:    
    - Student Name
    - Learning Background / Level
    - Motivation
    - Final Project to Implement (2+ line description of the final project)

It is very important you completely capture the above information and understand the student.
Once you believe that you have captured all the information, please confirm with the student.
- Your final message to the user should simply be a request to confirm, where you simply present a summary and understanding of what the student provided. There background, motivation, and project they would like to work on. It should be nothing else but that, along with a final confirmation question asking the student to confirm if your understanding is correct.
Once they confirmed, simply generate "DONE" and nothing else, to complete the chat.
The chat will automatically end once you generate "DONE", ast that will be the final message.
Also, when responding back to the student, don't write "AI:" as possibly showin the user's past messages string below. Simply just return the message.
Below you are provided with the user's past messages, along with their current message.
"""
    # prompt += """# If it is a message response to the student, it will be a JSON object in the following exact format:\n{"type": "response", "message": "..."}\n"""
    # prompt += """# If it is the final summary JSON object, it will be in the following exact format:\n{"type": "final", "student_name": "...", "background": "...", "motivation": "...", "final_project": "..."}\n\n"""

    prompt += f"""\n\n## Entire Chat History With You And Student:\n{user_chat_history_string}\n\n"""
    prompt += f"""## Student Current Message:\n{user_message}\n\n"""
    prompt += """## Output:\n"""
    return prompt


# # TODO: 
# def _user_summary_prompt(user_chat_history_string):
#     prompt = f"""## Instructions:
# - Given the user chat history below with the AI, generate a 1-2 line summary literally just presenting their goals to them.
# - Also, generate a single line explaining why our introductory python course will be personalized for them, to help them with their goal.
# - Please start with the user's name that they provide (it's in the chat history shown below) as this message should be hyper-personalized for them!
# - Also start with thanking them for providing the information and chatting with you.
# - Wish them good luck at the end with some motivation, as they proceed to the Python Course which we provide and it is relevant to their goals.
# - Make it very personalized message for them.
# - Do not mention anything else and keep it brief, to the point.
# - No markdown, just plain text.

# ## Chat History:
# {user_chat_history_string}

# ## Output:
# """
#     return prompt


def _create_user_summary_and_profile(user_chat_history_string):
    prompt = f"""You are Companion, an energetic and motivating AI teacher and tutor for Python. You will be teaching the student Python, in a very personalized manner, ensuring they completely understand the material, and that they achieve their desired learning goals!
    
Below you are provided the full chat between you and the student, where the student discussed their background, motivation, and goal for why they want to learn Python, along with the project they have decided to work on.

Your goal is now to take this information, and generate the following 2 pieces of information:
1. Create a 2 line summary, talking to the student, which summarizes their goals along with next steps on the personalized course that is generated for them!
    - In this summary, start by thanking them for providing the information and chatting with you.
    - Wish them good luck at the end with some motivation, as they proceed to the Python Course that has been generated for them.
    - Make it very personalized message for them.
    - No markdown, just plain text for this message.

2. Create a Dictionary representing the student profile. Below is the exact format you will generate for this step.
    {{
        "student_name": "...",
        "background": "...",
        "motivation": "...",
        "final_project": "..."
    }}

Return the above information as a JSON object, in the following format:
{{
    "student_summary": "...",
    "student_profile_json_dictionary": "..."
}}

## Chat History:
{user_chat_history_string}

## Output:
"""
    return prompt


def _create_user_syllabus_prompt(user_profile_dictionary_string, user_chat_history_string):
    prompt = f"""You are Companion, an energetic and motivating AI teacher and tutor for Python. You will be teaching the student Python, in a very personalized manner, ensuring they completely understand the material, and that they achieve their desired learning goals!

Below is both the summary and the full previous conversation you have add with the student, on discussing their background, motivation, and a final project they have in mind that they want to implement, as they go on this journey to learn Python.

Your job is now to take all this critical information and develop a personalized learning syllabus for the student.
- The syllabus should be well-thought out, consisting of the foundational concepts or review the student needs, dependent upon their skill level, along with the concepts that need to be taught or introduced, for their final project goal.

Your output should be a JSON dictionary with the following information:
- course_name
- course_description
- syllabus_json_list
    - This will be a JSON list, consisting of the syllabus where each JSON dict will contain the:
        - module_name
        - module_description
        - sub_module_list (topics to be presented within this module)

Critical Points to note when generating the syllabus:
- For the foundational portion of learning Python, the student will be coding directly in the browser where the IDE is already setup. Thus, in the beginning, there is no need to talk or teach the student how to setup the python environment as it will already be setup for them, in the browser.
    - DO NOT mention or have any module or sub-module on 'setting up the python environment or IDE' as all that will already be setup for the user.
    - Please proceed straight to the material, right from the beginning.
- Each module will have a quiz at the end of it (except the module with the project), to test the student's understanding and help identify and improve any weaknesses found.
- For the project related module, that should obviously be towards the end, after the foundations have been taught and should end with a final project submission / review.
    - Do not have any sub_module_list generated for the project module. This will be generated afterwards so leave it empty.
        - Simply leave the sub_module_list as [].


## Student Past Chat Conversation:
{user_chat_history_string}


## Student Background, Goal, Project Summary in JSON Format:
{user_profile_dictionary_string}


## Output:
"""
    return prompt


def _create_sub_topic_module_generation_prompt(
    entire_syllabus_string,
    current_module_dictionary_string,
    current_sub_module_topic_string,
    student_profile_dictionary
):
    prompt = """You are Companion, an energetic and motivating AI teacher and tutor for Python. You will be teaching the student Python, in a very personalized manner, ensuring they completely understand the material, and that they achieve their desired learning goals!

Your job is to take the current sub-module topic presented below, and generate a very informative, meaningful, and structured course module material, which will be presented to the student.
- More specifically, your task is to break down the concept into meaningful **modules** for teaching Python. Each module should represent a distinct topic that could stand on its own and be taught to a student.
- I have also included the entire syllabus of the course the student is taking, along with the Module dictionary that this particular sub-module is part of, so you have all the additional context. However, your responsibility is to only generate the course module information for the provided sub-module below (shown in "Current Sub Module Dictionary").
- I have also included the student's goals and objectives, or rather, why they are learning Python and what they hope to achieve from the course. When generating your notes and exercises, (when possible) please try to cater them or make them as relevant to the student's goals, objectives, and their current level.

You will create a **JSON object** with the following structure:

```json
{
    "sub_module_name": "...",
    "notes": "...",
    "information": [
        {
            "type": "example",
            "description": "...",
            "code": "..."
        },
        {
            "type": "exercise",
            "question": "...",
            "example_input_output_list": "...",
            "correct_code_solution": "..."
        },
        {
            "type": "example",
            "description": "...",
            "code": "..."
        },
        {
            "type": "exercise",
            "question": "...",
            "example_input_output_list": "...",
            "correct_code_solution": "..."
        },
        ...
    ]
}
```

### Guidelines:
1. **Content Format**:
    - The **"notes"** section should contain a clear and thorough explanation of the concept. The critical thing here is to write it in a way that is very personalized to the student's level and their goals, allowing them to understand it in an optimal manner. Speak directly to the student, in a conversational manner as you generate your notes and examples. Avoid saying "Hey.." though as the notes won't naturally flow well, and more so, just speak directly with the student and refer directly to their name, etc. in a conversational, energetic manner.
    - The **"examples"** section should contain multiple code snippets that demonstrate the concept in practice. For concepts that are harder or cover more ground, feel free to include more examples to help the student understand the concept.
    - The **"exercises"** section should contain practice problems that allow students to apply the concept they've just learned. All exercises MUST be programming questions where the student needs to write code. Each exercise should be a dictionary, including the question, example input/outputs, and the correct solution (in python code). The correct solution should simply just contain the code solution, nothing else.
    - As mentinoed above, try to personalize as much as possible to the student's profile and goals, obviously without overdoing it.
    - Generally speaking, if the concept is relatively straight-forward to explain, leverage the "example -> exercise" approach where an exercise is given right after the example. HOWEVER, if the concept is more difficult and requires additional examples, feel free to show multiple examples first, before giving the student an exercise.

2. **Example Breakdown**:
    - For example, if the chapter explains how to create functions in Python, you could create a module named "Defining Functions in Python". This module would explain how functions work, provide examples of how to define and call functions, and then include exercises asking the student to create their own function to solve various problems.


"""
    prompt += f"## Entire Syllabus:\n{entire_syllabus_string}\n\n"
    prompt += f"## Current Entire Module Dictionary:\n{current_module_dictionary_string}\n\n"
    prompt += f"## Current Sub-Module Topic:\n{current_sub_module_topic_string}\n\n"
    prompt += f"## Current Student Profile:\n{student_profile_dictionary}\n\n"
    prompt += f"## Output:\n"

    return prompt
