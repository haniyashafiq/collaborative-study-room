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


# @router.post(
#     "/",
#     response_model=schemas.ParticipantResponse,
#     status_code=status.HTTP_201_CREATED
# )
# async def add_participant(
#     participant: schemas.ParticipantCreate,
#     db: AsyncSession = Depends(get_db),
#     current_user: models.User = Depends(get_current_user)
# ):
#     # Check if room exists
#     db_room = await crud.get_room(db, participant.room_id)
#     if not db_room:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Room not found"
#         )

#     # Check if participant already in room
#     existing = await crud.get_participant_by_username_and_room(
#         db, username=participant.username, room_id=participant.room_id
#     )
#     if existing:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Participant already in this room"
#         )

#     return await crud.create_participant(db, participant)


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
@router.delete(
    "/{participant_id}",
    status_code=status.HTTP_200_OK
)
async def remove_participant(
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_participant = await crud.get_participant(db, participant_id)
    if not db_participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    await crud.delete_participant(db, participant_id)
    return {"detail": f"Participant {participant_id} removed successfully"}
