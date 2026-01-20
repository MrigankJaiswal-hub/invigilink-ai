import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from .models import Base
from sqlalchemy.exc import OperationalError
import time

load_dotenv()
# engine = create_engine(os.getenv("DATABASE_URL"), future=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# psycopg2 expects postgresql:// not postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, future=True)

# def init_db():
#     Base.metadata.create_all(engine)

from sqlalchemy.exc import OperationalError
import time

def init_db(retries=5, delay=3):
    for i in range(retries):
        try:
            Base.metadata.create_all(engine)
            return
        except OperationalError as e:
            if i == retries - 1:
                raise
            print(f"DB not ready, retrying ({i+1}/{retries})...")
            time.sleep(delay)
