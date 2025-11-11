from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from jose import jwt, JWTError
from app.core.connection_manager import ConnectionManager
from app import crud, models
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.schemas import WSMessageIn, WSMessageOut
from app.core.config import settings  # SECRET_KEY lives here

router = APIRouter(prefix="/ws", tags=["WebSockets"])
manager = ConnectionManager()



@router.websocket("/rooms/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    db: AsyncSession = Depends(get_db),
):
    # 1️⃣ Extract token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    await websocket.accept()
    # 2️⃣ Verify JWT and extract user ID
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    # 3️⃣ Ensure room exists
    room = await crud.get_room(db, room_id)
    if not room:
        await websocket.close(code=1008, reason="Room not found")
        return

    # 4️⃣ Ensure user is a participant
    participant = await crud.get_participant_by_username_and_room(db, username, room_id)
    if not participant:
        await websocket.close(code=1008, reason="You are not a participant of this room")
        return

    # Fetch recent messages for context
    recent_messages = await crud.get_recent_messages(db, room_id)

    # Send them in chronological order (oldest first)
    for msg in reversed(recent_messages):
        await websocket.send_json({
            "event": "previous_message",
            "message": {
                "id": msg.id,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "user_id": msg.user_id,
                "room_id": msg.room_id,
            }
        })


    # 5️⃣ Connect WebSocket
    await manager.connect(room_id, websocket)
    print(f"User {user_id} connected to room {room_id}")

    try:
        while True:
            # 6️⃣ Receive and validate incoming message
            try:
                data = await websocket.receive_json()
                msg_in = WSMessageIn(**data)
            except Exception as e:
                await websocket.send_json({"error": f"Invalid message format: {str(e)}"})
                continue

            # 7️⃣ Persist to DB
            try:
                new_message = await crud.create_message_for_websocket(
                    db=db,
                    content=msg_in.content,
                    room_id=room_id,
                    user_id=user_id)
            except SQLAlchemyError:
                await websocket.send_json({"error": "Database error"})
                continue

            user = await crud.get_user_by_id(db, user_id)
            if not user:
                await websocket.send_json({"error": "User not found"})
                continue

            # 8️⃣ Broadcast to room participants
            message_out = WSMessageOut(
                id=new_message.id,
                content=new_message.content,
                timestamp=new_message.timestamp,
                user_id=user_id,
                username=user.username,
                room_id=room_id,
            )

            await manager.broadcast(
                room_id,
                {
                    "event": "new_message",
                    "message": message_out.model_dump()
                },
            )

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(
            room_id,
            {"event": "user_left", "user_id": user_id, "username": user.username}
        )

        print(f"User {user_id} disconnected from room {room_id}")
