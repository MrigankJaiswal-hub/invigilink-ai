import os, datetime, jwt
SECRET = os.getenv("JWT_SECRET","dev_secret")
ALGO = "HS256"

def create_access_token(sub: str, role: str):
    payload = {"sub": sub, "role": role, "exp": datetime.datetime.utcnow()+datetime.timedelta(hours=8)}
    return jwt.encode(payload, SECRET, algorithm=ALGO)

def decode(token:str):
    return jwt.decode(token, SECRET, algorithms=[ALGO])
