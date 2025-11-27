# models.py

#Had to generate models in order to test the setup

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, func
from sqlalchemy.orm import relationship
from .database import Base


# -----------------------------
# USERS (for authentication)
# -----------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    role = Column(String, default="user")  # 👈 Added column (default is "user")

    rooms = relationship("Room", back_populates="creator")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    participants = relationship("Participant", back_populates="user", cascade="all, delete-orphan")


# -----------------------------
# ROOMS
# -----------------------------
class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    creator = relationship("User", back_populates="rooms")
    participants = relationship("Participant", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")
    timers = relationship("Timer", back_populates="room", cascade="all, delete-orphan")

# -----------------------------
# PARTICIPANTS
# -----------------------------
class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))

    user = relationship("User", back_populates="participants")
    room = relationship("Room", back_populates="participants")


# -----------------------------
# MESSAGES
# -----------------------------
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user_id = Column(Integer, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))

    user = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")


# -----------------------------
# TIMERS (Pomodoro sessions)
# -----------------------------

class Timer(Base):
    __tablename__ = "timers"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), unique=True, nullable=False)
    room = relationship("Room", back_populates="timers")
    duration = Column(Integer, nullable=False)         # total seconds configured (e.g., 1500)
    remaining = Column(Integer, nullable=False)        # remaining seconds
    is_running = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())