# app/crud.py
"""
CRUD operations for Users, Rooms, Participants, Messages, and Timers.
Uses SQLAlchemy AsyncSession (from app.database).
"""

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from . import models, schemas
from .utils import hash_password


# -----------------------------
# USERS
# -----------------------------
async def create_user(db: AsyncSession, user: schemas.UserCreate, hash_pw: bool = True) -> models.User:
    """
    Create a new user. By default the password will be hashed.
    If you pass hash_pw=False the password will be stored as-is (not recommended).
    """
    if hash_pw:
        hashed = hash_password(user.password)
    else:
        hashed = user.password

    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalar_one_or_none()


# -----------------------------
# ROOMS
# -----------------------------
async def create_room(db: AsyncSession, room: schemas.RoomCreate, user_id: int) -> models.Room:
    new_room = models.Room(name=room.name, creator_id=user_id)
    db.add(new_room)
    await db.commit()

    # Refresh with relationships loaded
    await db.refresh(new_room)

    # Explicitly re-fetch the room with eager-loaded relationships
    result = await db.execute(
        select(models.Room)
        .options(selectinload(models.Room.participants))
        .where(models.Room.id == new_room.id)
    )
    return result.scalar_one()


async def get_rooms(db: AsyncSession, skip: int = 0, limit: int = 10) -> List[models.Room]:
    result = await db.execute(
        select(models.Room)
        .options(
            selectinload(models.Room.participants).selectinload(models.Participant.user),
            selectinload(models.Room.creator)
        )
        .offset(skip)
        .limit(limit)
    )
    # .unique() is useful when joins might duplicate parent rows; safe to keep
    return result.scalars().unique().all()


async def get_room(db: AsyncSession, room_id: int) -> Optional[models.Room]:
    result = await db.execute(
        select(models.Room)
        .options(joinedload(models.Room.participants).joinedload(models.Participant.user))
        .where(models.Room.id == room_id)
    )
    return result.unique().scalar_one_or_none()

async def get_room_by_name(db: AsyncSession, name: str):
    result = await db.execute(select(models.Room).filter(models.Room.name == name))
    return result.scalars().first()


async def delete_room(db: AsyncSession, room_id: int, current_user: models.User) -> bool:
    result = await db.execute(select(models.Room).where(models.Room.id == room_id))
    room = result.scalars().first()

    if not room:
        raise ValueError("Room not found")

    # Authorization check
    if room.creator_id != current_user.id and current_user.role != "admin":
        raise PermissionError("You are not authorized to delete this room")

    await db.delete(room)
    await db.commit()
    return True

# -----------------------------
# PARTICIPANTS
# -----------------------------
async def add_user_to_room(db: AsyncSession, room_id: int, user_id: int) -> bool:
    # Check if participant exists
    result = await db.execute(
        select(models.Participant).where(
            models.Participant.room_id == room_id,
            models.Participant.user_id == user_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant:
        return False  # already in room

    participant = models.Participant(room_id=room_id, user_id=user_id)
    db.add(participant)
    await db.commit()
    return True


async def remove_user_from_room(db: AsyncSession, room_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(models.Participant).where(
            models.Participant.room_id == room_id,
            models.Participant.user_id == user_id,
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        return False

    await db.delete(participant)
    await db.commit()
    return True


async def get_room_participants(db: AsyncSession, room_id: int) -> List[schemas.ParticipantResponse]:
    result = await db.execute(
        select(models.Participant, models.User.username)
        .join(models.User, models.Participant.user_id == models.User.id)
        .where(models.Participant.room_id == room_id)
    )
    rows = result.all()
    participants = []
    for participant, username in rows:
        participants.append(
            schemas.ParticipantResponse(
                id=participant.id,
                room_id=participant.room_id,
                username=username
            )
        )
    return participants

async def get_participant_by_username_and_room(db: AsyncSession, username: str, room_id: int):
    result = await db.execute(
        select(models.Participant, models.User.username)
        .join(models.User, models.User.id == models.Participant.user_id)
        .where(models.Participant.room_id == room_id, models.User.username == username)
    )
    row = result.first()
    if not row:
        return None
    participant, username = row
    return schemas.ParticipantResponse(
        id=participant.id,
        username=username,
        room_id=participant.room_id
    )

async def create_participant(db: AsyncSession, participant: schemas.ParticipantCreate):
    # resolve user_id by username
    user = await get_user_by_username(db, participant.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_participant = models.Participant(user_id=user.id, room_id=participant.room_id)
    db.add(new_participant)
    await db.commit()
    await db.refresh(new_participant)
    return schemas.ParticipantResponse(
        id=new_participant.id,
        username=user.username,
        room_id=new_participant.room_id
    )

async def get_participants_by_room(db: AsyncSession, room_id: int):
    result = await db.execute(
        select(models.Participant, models.User.username)
        .join(models.User, models.User.id == models.Participant.user_id)
        .where(models.Participant.room_id == room_id)
    )
    rows = result.all()
    return [
        schemas.ParticipantResponse(
            id=participant.id,
            username=username,
            room_id=participant.room_id
        )
        for participant, username in rows
    ]

async def get_participants_by_room(db: AsyncSession, room_id: int):
    result = await db.execute(
        select(models.Participant, models.User.username)
        .join(models.User, models.User.id == models.Participant.user_id)
        .where(models.Participant.room_id == room_id)
    )
    rows = result.all()
    return [
        schemas.ParticipantResponse(
            id=participant.id,
            username=username,
            room_id=participant.room_id
        )
        for participant, username in rows
    ]

async def delete_participant(db: AsyncSession, participant_id: int):
    result = await db.execute(select(models.Participant).where(models.Participant.id == participant_id))
    participant = result.scalar_one_or_none()
    if not participant:
        return False
    await db.delete(participant)
    await db.commit()
    return True

# -----------------------------
# MESSAGES
# -----------------------------
async def create_message(db: AsyncSession, message: schemas.MessageCreate, sender_id: int):
    db_message = models.Message(
        content=message.content,
        user_id=sender_id,
        room_id=message.room_id,
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return schemas.MessageResponse(
        id=db_message.id,
        content=db_message.content,
        timestamp=db_message.timestamp,
        sender=db_message.user.username,  # ✅ ensure username is returned
        room_id=db_message.room_id
    )


# ---------------------------
# Get all messages
# ---------------------------
async def get_messages(db: AsyncSession):
    result = await db.execute(
        select(models.Message).order_by(models.Message.timestamp)
    )
    messages = result.scalars().all()
    return [
        schemas.MessageResponse(
            id=m.id,
            content=m.content,
            timestamp=m.timestamp,
            sender=m.user.username,  # ✅ join with User
            room_id=m.room_id
        )
        for m in messages
    ]


# ---------------------------
# Get messages by room
# ---------------------------
async def get_messages_by_room(db: AsyncSession, room_id: int):
    result = await db.execute(
        select(models.Message)
        .where(models.Message.room_id == room_id)
        .order_by(models.Message.timestamp)
    )
    messages = result.scalars().all()
    return [
        schemas.MessageResponse(
            id=m.id,
            content=m.content,
            timestamp=m.timestamp,
            sender=m.user.username,  # ✅ show username not id
            room_id=m.room_id
        )
        for m in messages
    ]




# ---------------------------
# TIMER CRUD
# ---------------------------

async def create_timer(db: AsyncSession, timer: schemas.TimerCreate):
    db_timer = models.Timer(
        room_id=timer.room_id,
        duration_minutes=timer.duration_minutes,
        is_active=True
    )
    db.add(db_timer)
    await db.commit()
    await db.refresh(db_timer)
    return db_timer


async def get_timer(db: AsyncSession, timer_id: int):
    result = await db.execute(select(models.Timer).where(models.Timer.id == timer_id))
    return result.scalars().first()


async def get_timers_by_room(db: AsyncSession, room_id: int):
    result = await db.execute(select(models.Timer).where(models.Timer.room_id == room_id))
    return result.scalars().all()


async def stop_timer(db: AsyncSession, timer_id: int):
    db_timer = await get_timer(db, timer_id)
    if not db_timer:
        return None

    stmt = (
        update(models.Timer)
        .where(models.Timer.id == timer_id)
        .values(is_active=False)
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()

    await db.refresh(db_timer)
    return db_timer