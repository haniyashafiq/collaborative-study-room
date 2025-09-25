# Entry point (FastAPI app, routes mounted here)

#testing to confirm setup:

from fastapi import FastAPI
from app.routers import auth

app = FastAPI()

app.include_router(auth.router)
@app.get("/")
def read_root():
    return {"message": "Collaborative Study Room API is running 🚀"}
