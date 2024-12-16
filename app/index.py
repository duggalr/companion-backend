import os
from typing import Optional, Generator
import ast
import json
from json import JSONDecodeError
import docker
from celery import Celery
from celery.result import AsyncResult
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect

from app.database import SessionLocal
from app.llm import prompts, openai_wrapper
from app.models import InitialPlaygroundQuestion, UserCreatedPlaygroundQuestion, PlaygroundCode, UserCreatedPlaygroundQuestion, PlaygroundChatConversation, LandingPageEmail
from app.pydantic_schemas import RequiredAnonUserSchema, UpdateQuestionSchema, CodeExecutionRequestSchema, SaveCodeSchema, SaveLandingPageEmailSchema
from app.config import settings
from app.utils import create_anon_user_object, get_anon_custom_user_object, _get_random_initial_pg_question


app = FastAPI(
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json"
)

# Dependency for database
def get_db() -> Generator[Session, None, None]:
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database connection failed")
    finally:
        db.close()

# Open Wrapper
def get_openai_wrapper() -> openai_wrapper.OpenAIWrapper:
    return openai_wrapper.OpenAIWrapper(
        api_key=settings.openai_key,
        model="gpt-4o-mini"
    )

# Initialize Celery
celery_app = Celery(
    __name__,
    backend = f"{os.environ['REDIS_BACKEND_URL']}",
    broker = f"{os.environ['REDIS_BACKEND_URL']}/0",
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


## Views

@app.post("/save_landing_page_email")
def save_landing_page_email(
    data: SaveLandingPageEmailSchema,
    db: Session = Depends(get_db)
):
    user_email = data.email.strip()
    lp_email_object = LandingPageEmail(
        email = user_email
    )
    db.add(lp_email_object)
    db.commit()
    db.refresh(lp_email_object)

    return {'success': True}


@app.get("/get_number_of_lp_email_submissions")
def get_number_of_registered_emails(
    db: Session = Depends(get_db)
):
    number_of_email_submissions = db.query(LandingPageEmail).count()
    print(f"Number of submissions:", number_of_email_submissions)
    return {
        'success': True,
        'number_of_email_submissions': number_of_email_submissions
    }


@app.post("/validate-anon-user")
def validate_anon_user(
    data: RequiredAnonUserSchema,
    db: Session = Depends(get_db)
):
    anon_user_id = data.user_id
    custom_user_object_id = create_anon_user_object(
        anon_user_id = anon_user_id,
        db = db
    )
    return {
        'success': True,
        'custom_user_object_dict': custom_user_object_id
    }


@app.post("/create-anon-user")
def create_anon_user(
    data: RequiredAnonUserSchema,
    db: Session = Depends(get_db)
):
    anon_user_id = data.user_id
    custom_user_object_id = create_anon_user_object(
        anon_user_id = anon_user_id,
        db = db
    )
    return {
        'success': True,
        'custom_user_object_dict': custom_user_object_id
    }


@app.post("/get_random_initial_pg_question")
def get_random_initial_playground_question(
    data: RequiredAnonUserSchema,
    db: Session = Depends(get_db)
):
    # Get Anon User Object
    user_id = data.user_id
    current_custom_user_object = get_anon_custom_user_object(
        anon_user_id = user_id,
        db = db
    )
    if current_custom_user_object is None:
        raise HTTPException(status_code=400, detail="User object not found.")

    # Get Random Question Object
    random_initial_question_object = _get_random_initial_pg_question(
        db = db
    )

    # Create New Question Object
    new_pg_question_object = UserCreatedPlaygroundQuestion(
        name = random_initial_question_object.name,
        text = random_initial_question_object.text,
        example_io_list = random_initial_question_object.example_io_list,
        custom_user_id = current_custom_user_object.id
    )
    db.add(new_pg_question_object)
    db.commit()
    db.refresh(new_pg_question_object)

    to_return = {
        'question_id': new_pg_question_object.id,
        'name': new_pg_question_object.name,
        'text': new_pg_question_object.text,
        'starter_code': random_initial_question_object.starter_code,
        'example_io_list': ast.literal_eval(random_initial_question_object.example_io_list)
    }
    # return response_utils.success_response(data = to_return)
    return {
        'success': True,
        'data': to_return
    }


@app.post("/update_user_question")
def update_user_question(
    data: UpdateQuestionSchema,
    db: Session = Depends(get_db),
    # openai_wrapper: get_openai_wrapper()
    op_ai_wrapper: openai_wrapper.OpenAIWrapper = Depends(get_openai_wrapper)
):
    # Get Anon User Object
    user_id = data.user_id
    current_custom_user_object = get_anon_custom_user_object(
        anon_user_id = user_id,
        db = db
    )
    if current_custom_user_object is None:
        raise HTTPException(status_code=400, detail="User object not found.")

    existing_pg_question_object = db.query(UserCreatedPlaygroundQuestion).filter(
        UserCreatedPlaygroundQuestion.id == data.question_id,
        UserCreatedPlaygroundQuestion.custom_user_id == current_custom_user_object.id 
    ).first()

    if not existing_pg_question_object:
        raise HTTPException(status_code=404, detail="Question object not found or unauthorized.")

    # Generate AI Response
    try:
        prompt = f"{prompts.GENERATE_INPUT_OUTPUT_EXAMPLE_PROMPT}Question: {data.question_text.strip()}\n\n## Output:\n"
        ai_response = op_ai_wrapper.generate_sync_response(
            prompt = prompt
        )
        ai_response_json_dict = json.loads(ai_response.choices[0].message.content)
        example_io_list = ai_response_json_dict["input_output_example_list"]
    except (KeyError, JSONDecodeError):
        raise HTTPException(status_code=500, detail="Invalid AI response format.")


    question_input_output_example_list_string = str(ai_response_json_dict['input_output_example_list'])
    question_input_output_example_list_json_representation = json.dumps(ai_response_json_dict['input_output_example_list'])

    existing_pg_question_object.name = data.question_name
    existing_pg_question_object.text = data.question_text
    existing_pg_question_object.example_io_list = question_input_output_example_list_string
    db.commit()
    db.refresh(existing_pg_question_object)
    
    final_rv = {
        'unique_question_id': existing_pg_question_object.id,
        'question_name': data.question_name,
        'question_text': data.question_text,
        'example_io_list': question_input_output_example_list_json_representation
    }
    return {
        'success': True,
        'data': final_rv
    }


## Celery Tasks ##

@celery_app.task
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


@app.post("/execute_user_code")
async def execute_code(
    request: CodeExecutionRequestSchema
):
    """
    Endpoint to submit code for execution.
    """
    user_language = request.language
    user_code = request.code
    task = execute_code_in_container.delay(
        language = user_language,
        code = user_code
    )
    return {"task_id": task.id}
  

@app.get("/task/status/{task_id}")
async def get_status(
    task_id: str
):
    task_result = AsyncResult(task_id)
    return {"task_id": task_id, "status": task_result.status}


@app.get("/result/{task_id}")
def get_result(
    task_id: str
):
    """
    Endpoint to check the result of the execution.
    """
    task_result = celery_app.AsyncResult(task_id)
    result_data = task_result.get()

    result_output_status = result_data['success']
    result_output_value = result_data['output']
    return {
        "result_output_status": result_output_status,
        "result_output_value": result_output_value
    }


@app.post("/save_user_code")
def save_user_code(
    data: SaveCodeSchema,
    db: Session = Depends(get_db)
):
    user_id = data.user_id
    question_id = data.question_id
    current_code = data.code
    print('full data', data)

    pg_code_object = PlaygroundCode(
        programming_language = 'python',
        code = current_code,
        question_object_id = question_id
    )
    db.add(pg_code_object)
    db.commit()
    db.refresh(pg_code_object)

    return {
        'success': True,
    }



def _prepate_tutor_prompt(user_current_problem_name, user_current_problem_text, user_question, student_code, student_chat_history):
    prompt = """##Task:
You will be assisting a student, who will be asking questions on a specific Python Programming Problem.
Your will be their upbeat, encouraging tutor.
- Even though you are encouraging and upbeat, maintain a natural conversation flow. Don't overcompliment in each message. Keep it natural like a good tutor.
Your primary goal is to guide and mentor them, helping them solve their problem effectively, but also to become a great individual thinker. Please adhere to these guidelines. Further instructions are provided below. Also, an example is provided below.
- In addition, if the student has correctly solved the problem, end the conversation.
- Do not try to make the conversation going along, especially when the student has already successfully solved the problem.
- Instead, ask the student if they have any other questions or other concepts/problems they would like to explore.
- Please don't guide the student to using any libraries that need pip install as the remote code execution environment doesn't support those libraries.
    - Native python libraries (ie. like math) are completely fine and are supported.

##Instructions:
- Ask or Gauge their pre-requisite knowledge:
    - Try to understand or gauge the student's understanding of the concept or problem they have asked, before jumping in and providing them with further information or hints.
    - By understanding the student's current understanding of the concept or problem, it will make it easier for you to determine which level of abstraction you should start with, when generating your answer.
- No Over Information:
    - Do not provide over information, for a student's question.
    - Instead, focus on trying to create a conversation with the student.
    - Do not provide the student with the answer in any way. Instead, focus on providing valuable but concise explanations, hints, and follow-up questions, forcing the student to think of the answer on their own.
- No Direct Answers:
    - Do not provide any direct code solutions to the students questions or challenges.
    - Instead, focus on providing high-quality hints, with very concrete examples or detailed explanations.
    - Your goal as a tutor is to provide concrete and detailed guidance to help the student solve the problem on their own.
    - Thus, for questions students ask, don't simply provide the answer. Instead, provide a hint and try to ask the student a follow-up question/suggestion. Under no circumstance should you provide the student a direct answer to their problem/question.
- Encourage Problem Solving:
    - Always encourage the students to think through the problems themselves. Ask leading questions that guide them toward a solution, and provide feedback on their thought processes.
    - Make sure you consider both correctness and efficiency. You want to help the student write optimal code, that is also correct for their given problem.
- Only ask one question or offer only one suggestion at a time for the student:
    - Wait for the students response before asking a new question or offering a new suggestion.
- If the student has successfully answered the question in an optimal manner, don't continue "nit-picking" or continuning to suggest code improvements.
    - Instead, tell the student they have successfully answered the question and either encourage them to ask another one or suggest code improvements or new related concepts the student can learn or might be interested in.

##Example:

#Example Student Question:
#Find the total product of the list

list_one = [2,23,523,1231,32,9]
total_product = 0
for idx in list_one:
    total_product = idx * idx

I'm confused here. I am multiplying idx and setting it to total_product but getting the wrong answer. What is wrong?

##Example Bad Answer (Avoid this type of answer):
You are correct in iterating through the list with the for loop but at the moment, your total_product is incorrectly setup. Try this instead:
list_one = [2,23,523,1231,32,9]
total_product = 1
for idx in list_one:
    total_product = total_product * idx

##Example Good Answer: (this is a good answer because it identifies the mistake the student is making but instead of correcting it for the student, it asks the student a follow-up question as a hint, forcing the student to think on their own)
You are on the right track. Pay close attention to the operation you are performing in the loop. You're currently multiplying the number with itself, but you want to find the product of all numbers. What operation should you use instead to continuously update 'total_product'?

##Student Current Working Problem:

Name: {user_current_problem_name}

Question: {user_current_problem_text}


##Previous Chat History:
{student_chat_history}

##Student Current Chat Message:
{question}


##Student Code:
{student_code}

##Your Answer:
"""
    
    prompt = prompt.format(
        question=user_question,
        student_code=student_code,
        student_chat_history=student_chat_history,
        user_current_problem_name=user_current_problem_name,
        user_current_problem_text=user_current_problem_text,
    )
    print(prompt)
    return prompt


## Websocket 

@app.websocket("/ws_handle_chat_response")
async def websocket_handle_chat_response(
    websocket: WebSocket,
    db: Session = Depends(get_db),
    op_ai_wrapper: openai_wrapper.OpenAIWrapper = Depends(get_openai_wrapper)
):
    await websocket.accept()
    try:
        while True:  # Keep receiving messages in a loop
            data = await websocket.receive_json()

            user_question = data['text'].strip()
            user_code = data['user_code']
            all_user_messages_str = data['all_user_messages_str']
            user_current_problem_name, user_current_problem_text = data['current_problem_name'], data['current_problem_question']

            parent_question_object_id = data['parent_question_object_id']
            parent_question_object = db.query(UserCreatedPlaygroundQuestion).filter(
                UserCreatedPlaygroundQuestion.id == parent_question_object_id
            ).first()

            if parent_question_object is None:
                return {'success': False, 'message': "Question object not found.", "status_code": 404}

            # Respond to the user
            full_response_message = ""

            model_prompt = _prepate_tutor_prompt(
                user_current_problem_name = user_current_problem_name,
                user_current_problem_text = user_current_problem_text,
                user_question=user_question,
                student_code=user_code,
                student_chat_history=all_user_messages_str
            )

            async for text in op_ai_wrapper.generate_async_response(
                prompt = model_prompt
            ):

                if text is None:
                    await websocket.send_text('MODEL_GEN_COMPLETE')

                    pg_chat_conversation_object = PlaygroundChatConversation(
                        question = user_question,
                        prompt = model_prompt,
                        response = full_response_message,
                        code = user_code,
                        question_object_id = parent_question_object_id
                        # playground_parent_object_id = parent_pg_object.id
                    )
                    db.add(pg_chat_conversation_object)
                    db.commit()
                    db.refresh(pg_chat_conversation_object)

                    break  # stop sending further text; just in case
                else:
                    full_response_message += text
                    await websocket.send_text(text)

    except WebSocketDisconnect:
        print("WebSocket connection closed")
        await websocket.close()


