# Entry point (FastAPI app, routes mounted here)

#testing to confirm setup:

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Collaborative Study Room API is running 🚀"}
