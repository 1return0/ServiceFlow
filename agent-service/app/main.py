from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import create_router
from app.api.public_knowledge_report_api import build_public_knowledge_report_router
from app.bootstrap import build_application_lifespan
from app.config import load_settings


settings = load_settings()
app = FastAPI(
    title="EduOps Agent Service",
    version=settings.version,
    description=(
        "A bounded LangGraph orchestration service for synthetic campus IT "
        "and teaching-service cases."
    ),
    lifespan=build_application_lifespan(settings),
)
allowed_origins = tuple(
    origin.strip()
    for origin in os.getenv(
        "SERVICEFLOW_CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Import-Token"],
)
app.include_router(create_router(settings))
app.include_router(build_public_knowledge_report_router(settings))
