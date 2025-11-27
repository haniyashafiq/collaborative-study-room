# schemas.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import List, Optional, Literal, Any

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
# class MessageBase(BaseModel):
#     content: str

# class MessageCreate(MessageBase):
#     sender: str
#     room_id: int

# class MessageResponse(MessageBase):
#     id: int
#     sender: str
#     timestamp: datetime
#     room_id: int

#     class Config:
#         orm_mode = True

class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    room_id: int


class MessageResponse(BaseModel):
    id: int
    content: str
    timestamp: datetime
    user: dict
    room_id: int

    class Config:
        from_attributes = True


#Websockets
class WSMessageIn(BaseModel):
    type: Literal["message", "timer"]  # allow two types safely

    # content can now be:
    # - string for chat
    # - dict for timer commands
    content: Optional[Any] = Field(...)

class WSMessageOut(BaseModel):
    id: int
    content: str
    timestamp: datetime
    room_id: int
    user_id: int
    username: str
    type: Literal["message"] = "message"
    model_config = ConfigDict(from_attributes=True)


# TIMERS (Pomodoro)

class TimerStartRequest(BaseModel):
    duration: int  # seconds

class TimerResponse(BaseModel):
    room_id: int
    duration: int
    remaining: int
    is_running: bool

    class Config:
        orm_mode = True