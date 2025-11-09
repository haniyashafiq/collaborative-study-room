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

# ---------- CREATE MESSAGE ----------
@router.post("/", response_model=schemas.MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message: schemas.MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if room exists
    room = await crud.get_room(db, message.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Check if user is participant in that room
    is_participant = await crud.is_user_participant(db, message.room_id, current_user.id)
    if not is_participant:
        raise HTTPException(status_code=403, detail="You are not a participant of this room")

    new_message = await crud.create_message(db, message, current_user.id)

    # Prepare response manually to include user data
    return schemas.MessageResponse(
        id=new_message.id,
        content=new_message.content,
        timestamp=new_message.timestamp,
        user={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at
        },
        room_id=new_message.room_id
    )


# ---------- GET MESSAGES BY ROOM ----------
@router.get("/rooms/{room_id}", response_model=List[schemas.MessageResponse])
async def get_room_messages(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if room exists
    room = await crud.get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    messages = await crud.get_messages_by_room(db, room_id)
    return [
        schemas.MessageResponse(
            id=m.id,
            content=m.content,
            timestamp=m.timestamp,
            user={
                "id": m.user.id,
                "username": m.user.username,
                "email": m.user.email,
                "created_at": m.user.created_at
            },
            room_id=m.room_id
        )
        for m in messages
    ]