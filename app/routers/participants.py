# app/routers/participant.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import schemas, crud
from app.database import get_db

router = APIRouter(
    prefix="/participants",
    tags=["Participants"]
)


# ---------------------------
# Add a participant to a room
# ---------------------------
@router.post("/", response_model=schemas.ParticipantResponse)
async def add_participant(
    participant: schemas.ParticipantCreate, db: AsyncSession = Depends(get_db)
):
    # Check if room exists
    db_room = await crud.get_room(db, room_id=participant.room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    return await crud.create_participant(db, participant)


# ---------------------------
# Get all participants in a room
# ---------------------------
@router.get("/room/{room_id}", response_model=List[schemas.ParticipantResponse])
async def get_participants_by_room(room_id: int, db: AsyncSession = Depends(get_db)):
    db_room = await crud.get_room(db, room_id=room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    return await crud.get_participants_by_room(db, room_id=room_id)


# ---------------------------
# Remove a participant from a room
# ---------------------------
@router.delete("/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_participant(participant_id: int, db: AsyncSession = Depends(get_db)):
    db_participant = await crud.get_participant(db, participant_id=participant_id)
    if not db_participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    await crud.delete_participant(db, participant_id)
    return {"message": "Participant removed successfully"}
