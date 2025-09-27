# main.py
# Entry point (FastAPI app, routes mounted here)

import uvicorn
from fastapi import FastAPI
from app.database import Base, engine
from app.routers import rooms, messages, participants, timer, auth

# Create all database tables
# (in production you'd use Alembic migrations instead)
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Initialize FastAPI app
app = FastAPI(
    title="Collaborative Study Room API",
    description="Backend API for managing study rooms, participants, messages, and Pomodoro timers.",
    version="1.0.0"
)


# Include Routers (no extra prefix/tags, since defined inside each router)
app.include_router(rooms.router)
app.include_router(messages.router)
app.include_router(participants.router)
app.include_router(timer.router)
app.include_router(auth.router)


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to Collaborative Study Room API 🚀"}


# Startup Event
@app.on_event("startup")
async def on_startup():
    await init_models()


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)