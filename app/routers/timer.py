# app/routers/timer.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import schemas, crud
from app.database import get_db

router = APIRouter(
    prefix="/timers",
    tags=["Timers"]
)


# ---------------------------
# Create a new timer for a room
# ---------------------------
@router.post("/", response_model=schemas.TimerResponse)
async def create_timer(timer: schemas.TimerCreate, db: AsyncSession = Depends(get_db)):
    db_room = await crud.get_room(db, room_id=timer.room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    return await crud.create_timer(db, timer)


# ---------------------------
# Get all timers for a room
# ---------------------------
@router.get("/room/{room_id}", response_model=List[schemas.TimerResponse])
async def get_timers_by_room(room_id: int, db: AsyncSession = Depends(get_db)):
    db_room = await crud.get_room(db, room_id=room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    return await crud.get_timers_by_room(db, room_id=room_id)


# ---------------------------
# Stop (deactivate) a timer
# ---------------------------
@router.put("/{timer_id}/stop", response_model=schemas.TimerResponse)
async def stop_timer(timer_id: int, db: AsyncSession = Depends(get_db)):
    db_timer = await crud.get_timer(db, timer_id=timer_id)
    if not db_timer:
        raise HTTPException(status_code=404, detail="Timer not found")

    return await crud.stop_timer(db, timer_id)
