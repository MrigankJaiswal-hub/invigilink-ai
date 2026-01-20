import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
insp = inspect(engine)

cols = insp.get_columns("users")
print("\nusers columns:")
for c in cols:
    print(f" - {c['name']} ({c.get('type')}) nullable={c.get('nullable')}")

print("\nunique constraints:", insp.get_unique_constraints("users"))
print("primary key:", insp.get_pk_constraint("users"))
