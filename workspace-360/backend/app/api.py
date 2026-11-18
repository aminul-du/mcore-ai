from fastapi import APIRouter
from .services.stt import router as stt_router
from .services.execution import router as exec_router

router = APIRouter()
router.include_router(stt_router, prefix="/stt", tags=["Speech-to-Text"])
router.include_router(exec_router, prefix="/execute", tags=["Execution Adapters"])
