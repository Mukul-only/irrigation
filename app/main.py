"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routes import router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB migrations on startup."""
    await init_db()
    yield


app = FastAPI(
    title="AI-Driven Smart Plant Care — Cloud & AI Layer",
    description=(
        "REST API for the Cloud & AI layer of the Smart Irrigation System.\n\n"
        "**Modules:**\n"
        "- 🌱 **Plant Classification** — maps sensor env to plant category thresholds\n"
        "- 📈 **Moisture Prediction** — polynomial regression on historical readings\n"
        "- 🚨 **Anomaly Detection** — 9-rule engine for over/under-watering, sensor faults, temp stress\n"
        "- 💡 **Decision Engine** — pump ON/OFF with duration, rain deferral, insights\n"
        "- 🗄️ **Data Storage** — SQLite (async) with full reading, prediction, anomaly history\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow all origins in dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "AI Irrigation Cloud Layer",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return JSONResponse({"status": "ok"})
