from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router

app = FastAPI(title="MCORE Workspace 360 Control Plane", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ais.mcorecare.com",
        "https://ais.mcoreai.dev"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "workspace-360-control-plane"}
