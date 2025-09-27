# app/routers/messages.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import schemas, crud, models
from app.database import get_db
from app.routers.auth import get_current_user  # ✅ Require authentication

router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)


# ---------------------------
# Send a new message
# ---------------------------
@router.post(
    "/",
    response_model=schemas.MessageResponse,
    status_code=status.HTTP_201_CREATED
)
async def send_message(
    message: schemas.MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if room exists
    db_room = await crud.get_room(db, message.room_id)
    if not db_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    # Optionally: check if user is a participant of the room
    participant = await crud.get_participant_by_username_and_room(
        db, username=current_user.username, room_id=message.room_id
    )
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this room"
        )

    return await crud.create_message(db, message, sender_id=current_user.id)


# ---------------------------
# Get all messages
# ---------------------------
@router.get(
    "/",
    response_model=List[schemas.MessageResponse]
)
async def get_messages(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    messages = await crud.get_messages(db)
    return messages


# ---------------------------
# Get messages from a specific room
# ---------------------------
@router.get(
    "/room/{room_id}",
    response_model=List[schemas.MessageResponse]
)
async def get_room_messages(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_room = await crud.get_room(db, room_id)
    if not db_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    # Optionally: ensure user is a participant of the room
    participant = await crud.get_participant_by_username_and_room(
        db, username=current_user.username, room_id=room_id
    )
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this room"
        )

    return await crud.get_messages_by_room(db, room_id=room_id)
