from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.auth import router as auth_router

app = FastAPI(
    title="PureMusic API",
    description="Backend API for PureMusic application",
    version="0.1.0"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])

@app.get("/")
async def root():
    return {"message": "Welcome to PureMusic API"}
