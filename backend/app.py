from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.dal import init_db
from routes.auth_routes import router as auth_r
from routes.admin_routes import router as admin_r
from routes.faculty_routes import router as faculty_r
from routes.import_routes import router as import_r
from routes.export_routes import router as export_r
from routes.public_routes import router as public_r     # NEW
from routes.student_routes import router as student_r   # NEW

app = FastAPI(title="InvigiLink AI")


origins = [
    "http://10.215.91.252:3000",
    "http://localhost:3000",
    "http://10.0.0.0/8",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # or ["*"] during local dev ONLY
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def start():
    init_db()

app.include_router(auth_r)
app.include_router(admin_r)
app.include_router(faculty_r)
app.include_router(import_r)
app.include_router(export_r)
app.include_router(public_r)     # NEW
app.include_router(student_r)    # NEW


@app.get("/health")
def health():
    return {"ok": True}