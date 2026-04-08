# =============================================================================
# TALASH - FastAPI Application Entry Point
# app/main.py
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.db.database import init_db
import app.db.models  # Ensure models are loaded before init_db
from app.api.cv_upload import router as cv_router
from app.api.analysis import router as analysis_router


# =============================================================================
# LIFESPAN
# Runs once on startup and once on shutdown
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — initialize database tables
    print("Starting TALASH backend...")
    await init_db()
    print("Database connected and tables ready.")
    yield
    # Shutdown
    print("Shutting down TALASH backend...")


# =============================================================================
# APP INSTANCE
# =============================================================================

app = FastAPI(
    title="TALASH - Smart HR Recruitment",
    description="Talent Acquisition & Learning Automation for Smart Hiring",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# CORS
# Allows React frontend (running on port 5173) to talk to this backend
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # allowing all for now since frontend might be on different hosts
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cv_router)
app.include_router(analysis_router)


# =============================================================================
# ROUTES
# Each module will have its own router — registered here
# =============================================================================

# Health check — always useful for demos
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "running",
        "app": "TALASH Backend",
        "version": "1.0.0"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


# =============================================================================
# HOW TO RUN
# From the backend/ directory with venv activated:
#
#   uvicorn app.main:app --reload
#
# Then open: http://localhost:8000
# API Docs:  http://localhost:8000/docs
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
