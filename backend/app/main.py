import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine, get_db
from app.models import entities
from fastapi import Depends

from app.routers import shipments
from app.routers import documents
from app.routers import processing
from app.routers import review

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CargoCheck AI",
    description="AI-powered Shipment Document Verification Platform",
    version="1.0.0"
)

app.include_router(shipments.router)
app.include_router(documents.router)
app.include_router(processing.router)
app.include_router(review.router)

allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Welcome to CargoCheck AI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/health/database")
def database_health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "database": "connected",
        "status": "healthy"
    }
