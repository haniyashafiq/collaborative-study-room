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

class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True


# JWT response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None


# PARTICIPANTS
class ParticipantBase(BaseModel):
    pass

class ParticipantCreate(ParticipantBase):
    room_id: int
    username: Optional[str] = None  # Optional for self-join or admin add
    
class ParticipantResponse(ParticipantBase):
    id: int
    room_id: int
    user: UserResponse
    class Config:
        from_attributes = True

class ParticipantCreate(BaseModel):
    room_id: int
    username: Optional[str] = None  # Optional for self-join or admin add


#Rooms
class RoomCreate(BaseModel):
    name: str



class RoomBase(BaseModel):
    id: int
    name: str
    creator_id: Optional[int] = None  # can be null if user deleted

    class Config:
        from_attributes = True


class RoomResponse(RoomBase):
    participants: List[ParticipantResponse] = []

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
