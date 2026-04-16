import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

import models
from database import Base, engine
from routes.auth import router as auth_router
from routes.datasets import router as datasets_router
from routes.query import router as query_router
from services.api_errors import build_error_response
from services.schema_migration_service import (
    count_orphan_datasets,
    ensure_dataset_registry_user_id_column,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("aida_api")
SLOW_REQUEST_SECONDS = 1.0

app = FastAPI(title="AI Data Analyst API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://172.16.20.29:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Create metadata tables at app startup if they do not exist."""
    Base.metadata.create_all(bind=engine)
    ensure_dataset_registry_user_id_column()
    orphan_count = count_orphan_datasets()
    if orphan_count > 0:
        logger.warning(
            "Found %s dataset rows with NULL user_id. Backfill is required for ownership.",
            orphan_count,
        )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request outcomes and flag slow requests for debugging."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = time.perf_counter() - start
        logger.exception(
            "Unhandled request failure: %s %s in %.3fs",
            request.method,
            request.url.path,
            elapsed,
        )
        raise

    elapsed = time.perf_counter() - start
    level = logging.WARNING if elapsed >= SLOW_REQUEST_SECONDS else logging.INFO
    logger.log(
        level,
        "%s %s -> %s in %.3fs",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return structured HTTP errors."""
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(
            code=f"HTTP_{exc.status_code}",
            message=message,
            details=exc.detail if not isinstance(exc.detail, str) else None,
            path=request.url.path,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured 422 validation errors."""
    return JSONResponse(
        status_code=422,
        content=build_error_response(
            code="VALIDATION_ERROR",
            message="Invalid request data.",
            details=exc.errors(),
            path=request.url.path,
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all structured error response for unexpected failures."""
    logger.exception("Unhandled server error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=build_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="Unexpected server error.",
            details=str(exc),
            path=request.url.path,
        ),
    )


@app.get("/health")
def health_check():
    """Health-check endpoint for service availability."""
    return {"status": "ok"}


app.include_router(datasets_router)
app.include_router(query_router)
app.include_router(auth_router)



