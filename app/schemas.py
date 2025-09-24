# schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional

# AUTH / USER
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str  # only required at creation

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# JWT response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None


# ROOMS
class RoomBase(BaseModel):
    name: str

class RoomCreate(RoomBase):
    pass

class RoomResponse(RoomBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# PARTICIPANTS
class ParticipantBase(BaseModel):
    username: str

class ParticipantCreate(ParticipantBase):
    room_id: int

class ParticipantResponse(ParticipantBase):
    id: int
    room_id: int

    class Config:
        orm_mode = True


# MESSAGES
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    sender: str
    room_id: int

class MessageResponse(MessageBase):
    id: int
    sender: str
    timestamp: datetime
    room_id: int

    class Config:
        orm_mode = True


# TIMERS (Pomodoro)
class TimerBase(BaseModel):
    duration_minutes: int

class TimerCreate(TimerBase):
    room_id: int

class TimerResponse(TimerBase):
    id: int
    room_id: int
    started_at: datetime
    is_active: bool

    class Config:
        orm_mode = True
