from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import TimerStartRequest, TimerResponse
from app import crud, models
from app.core.timer_manager import timer_manager

router = APIRouter(prefix="/timer", tags=["Timer"])

@router.post("/{room_id}/start", response_model=TimerResponse)
async def start_timer_rest(room_id: int, req: TimerStartRequest, db: AsyncSession = Depends(get_db)):
    # optional: check room exists
    timer = await crud.create_or_update_timer(db, room_id, req.duration, req.duration, True)
    return TimerResponse(room_id=timer.room_id, duration=timer.duration, remaining=timer.remaining, is_running=timer.is_running)

@router.post("/{room_id}/stop", response_model=TimerResponse)
async def stop_timer_rest(room_id: int, db: AsyncSession = Depends(get_db)):
    await crud.update_timer_state(db, room_id, remaining=0, is_running=False)
    t = await crud.get_timer_by_room(db, room_id)
    return TimerResponse(room_id=t.room_id, duration=t.duration, remaining=t.remaining, is_running=t.is_running)
