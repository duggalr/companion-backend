import os
from dotenv import load_dotenv, find_dotenv
ENV_FILE = find_dotenv()
load_dotenv(ENV_FILE)

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@localhost/{os.environ['DB_NAME']}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# if 'LOCAL' in os.environ:
#     from dotenv import load_dotenv, find_dotenv
#     ENV_FILE = find_dotenv()
#     load_dotenv(ENV_FILE)
#     DATABASE_URL = f"postgresql://{os.environ['LOCAL_DB_USER']}:{os.environ['LOCAL_DB_USER']}@localhost/{os.environ['LOCAL_DB_NAME']}"

# else:
#     import subprocess
#     import ast
#     def get_environ_vars():
#         completed_process = subprocess.run(
#             ['/opt/elasticbeanstalk/bin/get-config', 'environment'],
#             stdout=subprocess.PIPE,
#             text=True,
#             check=True
#         )
#         return ast.literal_eval(completed_process.stdout)

#     env_vars = get_environ_vars()
#     DATABASE_URL = f"postgresql://{env_vars['PRODUCTION_DB_USERNAME']}:{env_vars['PRODUCTION_DB_PASSWORD']}@{env_vars['PRODUCTION_DB_URL']}:5432/postgres"



# from dotenv import load_dotenv, find_dotenv
# ENV_FILE = find_dotenv()
# load_dotenv(ENV_FILE)
# # DATABASE_URL = f"postgresql://{os.environ['LOCAL_DB_USER']}:{os.environ['LOCAL_DB_USER']}@localhost/{os.environ['LOCAL_DB_NAME']}"
# DATABASE_URL = os.environ['DATABASE_URL']

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()