# app/routers/message.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import schemas, crud
from app.database import get_db

router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)


# ---------------------------
# Send a new message
# ---------------------------
@router.post("/", response_model=schemas.MessageResponse)
async def create_message(message: schemas.MessageCreate, db: AsyncSession = Depends(get_db)):
    # Check if the room exists
    db_room = await crud.get_room(db, room_id=message.room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    return await crud.create_message(db, message)


# ---------------------------
# Get all messages (optionally paginated)
# ---------------------------
@router.get("/", response_model=List[schemas.MessageResponse])
async def get_messages(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    messages = await crud.get_messages(db, skip=skip, limit=limit)
    return messages


# ---------------------------
# Get messages from a specific room
# ---------------------------
@router.get("/room/{room_id}", response_model=List[schemas.MessageResponse])
async def get_messages_by_room(room_id: int, db: AsyncSession = Depends(get_db)):
    db_room = await crud.get_room(db, room_id=room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    return await crud.get_messages_by_room(db, room_id=room_id)
