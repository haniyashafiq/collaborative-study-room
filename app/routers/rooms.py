# app/routers/room.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import schemas, models, crud
from app.database import get_db

router = APIRouter(
    prefix="/rooms",
    tags=["Rooms"]
)


# ---------------------------
# Create a new room
# ---------------------------
@router.post("/", response_model=schemas.RoomResponse)
async def create_room(room: schemas.RoomCreate, db: AsyncSession = Depends(get_db)):
    db_room = await crud.get_room_by_name(db, name=room.name)
    if db_room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room already exists"
        )
    return await crud.create_room(db, room)


# ---------------------------
# Get all rooms
# ---------------------------
@router.get("/", response_model=List[schemas.RoomResponse])
async def get_rooms(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    rooms = await crud.get_rooms(db, skip=skip, limit=limit)
    return rooms


# ---------------------------
# Get a specific room by ID
# ---------------------------
@router.get("/{room_id}", response_model=schemas.RoomResponse)
async def get_room(room_id: int, db: AsyncSession = Depends(get_db)):
    db_room = await crud.get_room(db, room_id=room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    return db_room


# ---------------------------
# Delete a room
# ---------------------------
@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db)):
    db_room = await crud.get_room(db, room_id=room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    await crud.delete_room(db, room_id=room_id)
    return {"message": f"Room {room_id} deleted successfully"}