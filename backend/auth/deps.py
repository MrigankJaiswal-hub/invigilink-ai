import os
from fastapi import Depends, HTTPException, Header, status
from .jwt import decode

# =========================
# Utility: Get current user
# =========================
def get_current_user(authorization: str = Header(None)):
    # 🧩 Bypass authentication entirely if DISABLE_AUTH=1
    if os.getenv("DISABLE_AUTH") == "1":
        return {"email": "demo@local", "role": "ADMIN"}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )

    token = authorization.split()[1]
    try:
        payload = decode(token)
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

# =========================
# Role-based requirements
# =========================
def require_admin(user=Depends(get_current_user)):
    # 🧩 Bypass restriction if DISABLE_AUTH=1
    if os.getenv("DISABLE_AUTH") == "1":
        return {"email": "demo@local", "role": "ADMIN"}

    role = (user.get("role") or "").upper()
    if role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user


def require_faculty(user=Depends(get_current_user)):
    if os.getenv("DISABLE_AUTH") == "1":
        return {"email": "demo@local", "role": "FACULTY"}

    role = (user.get("role") or "").upper()
    if role != "FACULTY":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty only",
        )
    return user
