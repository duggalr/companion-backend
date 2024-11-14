import os
ENV_FILE = find_dotenv()
load_dotenv(ENV_FILE)

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


if 'LOCAL' in os.environ:
    from dotenv import load_dotenv, find_dotenv
    ENV_FILE = find_dotenv()
    load_dotenv(ENV_FILE)

    DATABASE_URL = f"postgresql://{os.environ['LOCAL_DB_USER']}:{os.environ['LOCAL_DB_USER']}@localhost/{os.environ['LOCAL_DB_NAME']}"
else:
    DATABASE_URL = f"postgresql://{os.environ['PRODUCTION_DB_USERNAME']}:{os.environ['PRODUCTION_DB_PASSWORD']}@{os.environ['PRODUCTION_DB_URL']}:5432/postgres"

#     DATABASE_URL = f"postgresql://{os.environ['PRODUCTION_DB_USERNAME']}:{os.environ['PRODUCTION_DB_PASSWORD']}@{os.environ['PRODUCTION_DB_URL']}/{os.environ['PRODUCTION_DB_NAME']}"

# DATABASE_URL = f"postgresql://{os.environ['PRODUCTION_DB_USERNAME']}:{os.environ['PRODUCTION_DB_PASSWORD']}@{os.environ['PRODUCTION_DB_URL']}/{os.environ['PRODUCTION_DB_NAME']}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
