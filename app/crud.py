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
async def create_room(db: AsyncSession, room: schemas.RoomCreate) -> models.Room:
    new_room = models.Room(name=room.name)
    db.add(new_room)
    await db.commit()
    await db.refresh(new_room)
    return new_room


async def list_rooms(db: AsyncSession) -> List[models.Room]:
    result = await db.execute(select(models.Room))
    return result.scalars().all()


async def get_room(db: AsyncSession, room_id: int) -> Optional[models.Room]:
    result = await db.execute(
        select(models.Room)
        .options(joinedload(models.Room.participants).joinedload(models.Participant.user))
        .where(models.Room.id == room_id)
    )
    return result.scalar_one_or_none()


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


async def get_room_participants(db: AsyncSession, room_id: int) -> List[models.User]:
    result = await db.execute(
        select(models.User)
        .join(models.Participant, models.Participant.user_id == models.User.id)
        .where(models.Participant.room_id == room_id)
    )
    return result.scalars().all()


# -----------------------------
# MESSAGES
# -----------------------------
async def create_message(db: AsyncSession, msg: schemas.MessageCreate) -> models.Message:
    """
    Create a message from a MessageCreate (which contains sender: str and room_id: int).
    Resolves sender (username) -> user_id. Raises 404 if user or room missing.
    """
    # ensure room exists
    room = await get_room(db, msg.room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # resolve user by username
    user = await get_user_by_username(db, msg.sender)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_message = models.Message(
        content=msg.content,
        user_id=user.id,
        room_id=msg.room_id,
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    return new_message


# Backwards-compatible alias if any code calls save_message
async def save_message(db: AsyncSession, msg: schemas.MessageCreate) -> models.Message:
    return await create_message(db, msg)


async def get_messages(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.Message]:
    result = await db.execute(
        select(models.Message)
        .order_by(models.Message.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    # return ascending order (oldest first)
    return list(reversed(result.scalars().all()))


async def get_messages_by_room(db: AsyncSession, room_id: int, limit: int = 50) -> List[models.Message]:
    # ensure room exists
    room = await get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    result = await db.execute(
        select(models.Message)
        .where(models.Message.room_id == room_id)
        .order_by(models.Message.timestamp.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


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