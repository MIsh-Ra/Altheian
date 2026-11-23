from contextlib import asynccontextmanager

from app.api import admin, ai_detection, auth, documents, health, reports
from app.core.exceptions import (
    AlethianException,
    alethian_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Activate structured logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.models import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Alethian API", version="2.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(AlethianException, alethian_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(ai_detection.router, prefix="/api/v1/ai-detection", tags=["AI Detection"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(health.router, prefix="/health", tags=["Health"])

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.exists():
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        index_html = _frontend_dist / "index.html"
        if index_html.exists():
            return FileResponse(index_html)
        raise HTTPException(status_code=404, detail="Not Found")
else:
    @app.get("/")
    def read_root():
        return {"message": "Alethian API is running"}
