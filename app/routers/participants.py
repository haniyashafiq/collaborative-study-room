# app/routers/participants.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import schemas, crud, models
from app.database import get_db
from app.routers.auth import get_current_user  # ✅ Require authentication

router = APIRouter(
    prefix="/participants",
    tags=["Participants"]
)


# ---------------------------
# Add a participant to a room
# ---------------------------
@router.post(
    "/",
    response_model=schemas.ParticipantResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_participant(
    participant: schemas.ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1️⃣ Ensure room exists
    db_room = await crud.get_room(db, participant.room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    # 2️⃣ Determine who is being added
    if participant.username:
        # Admin (or room creator) is adding someone else
        user = await crud.get_user_by_username(db, participant.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 🔒 Authorization check:
        # Only room creator or admin can add other users
        if db_room.creator_id != current_user.id and not getattr(current_user, "is_admin", False):
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to add other users to this room"
            )

        user_id = user.id
    else:
        # Regular user adding themselves
        user_id = current_user.id

    # 3️⃣ Create participant entry
    participant_obj = await crud.create_participant(db, participant.room_id, user_id)

    return participant_obj


# ---------------------------
# Get all participants in a room
# ---------------------------
@router.get(
    "/room/{room_id}",
    response_model=List[schemas.ParticipantResponse]
)
async def get_participants(
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

    participants = await crud.get_participants_by_room(db, room_id=room_id)
    return participants


# ---------------------------
# Remove a participant from a room
# ---------------------------

# Option A: delete by room + user (preferred)
@router.delete("/rooms/{room_id}/users/{user_id}", status_code=status.HTTP_200_OK)
async def remove_participant_from_room(
    room_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    room = await crud.get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # allow if self or room creator or admin
    if user_id != current_user.id and room.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to remove this participant")

    success = await crud.delete_participant_by_room_and_user(db, room_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {"detail": f"User {user_id} removed from room {room_id}"}