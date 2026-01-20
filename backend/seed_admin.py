# backend/seed_admin.py
import os
from sqlalchemy import create_engine, text
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("❌ DATABASE_URL missing in .env")

pwd_hash = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("Admin@123")
engine = create_engine(DATABASE_URL, future=True)

# We know from your query that userrole enum has: ADMIN, FACULTY
ROLE_VALUE = "ADMIN"

SQL = """
INSERT INTO users (email, password_hash, role)
VALUES (:e, :p, :r)
ON CONFLICT (email) DO NOTHING;
"""

with engine.begin() as con:
    con.execute(
        text(SQL),
        {"e": "admin@cuj.edu", "p": pwd_hash, "r": ROLE_VALUE},
    )

print("✅ Seeded admin user:")
print("   Email: admin@cuj.edu")
print("   Password: Admin@123")
print("   Role: ADMIN")
