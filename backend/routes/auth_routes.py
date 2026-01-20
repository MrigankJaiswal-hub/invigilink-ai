from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from db.dal import SessionLocal
from db.models import User
from auth.jwt import create_access_token
from auth.deps import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])

# ======================
# ✅ LOGIN route
# ======================
@router.post("/login")
def login(email: str, password: str):
    with SessionLocal() as s:
        user = s.query(User).filter(User.email == email).first()
        if not user or not bcrypt.verify(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        role_value = user.role.value if hasattr(user.role, "value") else user.role
        return {
            "access_token": create_access_token(user.email, role_value),
            "role": role_value,
        }


# ======================
# 🧪 AUTH TEST ROUTES
# ======================

@router.get("/me")
def get_me(user=Depends(get_current_user)):
    """Return decoded JWT payload"""
    return {"status": "ok", "user": user}


@router.get("/verify")
def verify_token(user=Depends(get_current_user)):
    """Simple token validity check"""
    return {"valid": True, "email": user.get("email"), "role": user.get("role")}


@router.get("/ping-admin")
def ping_admin(user=Depends(require_admin)):
    """Verifies ADMIN-only access"""
    return {"message": "✅ Admin access confirmed", "user": user}
