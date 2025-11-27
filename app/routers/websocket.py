from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.core.connection_manager import ConnectionManager
from app.core.timer_manager import timer_manager
from app.database import get_db
from app.core.config import settings
from app import crud
from app.schemas import WSMessageIn, WSMessageOut

router = APIRouter(prefix="/ws", tags=["WebSockets"])
manager = ConnectionManager()


@router.websocket("/rooms/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    db: AsyncSession = Depends(get_db),
):

    # ----------------------------
    # 1️⃣ Extract token from query
    # ----------------------------
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    # Must accept BEFORE sending anything
    await websocket.accept()

    # ----------------------------
    # 2️⃣ Verify JWT
    # ----------------------------
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        username = payload.get("sub")
    except JWTError:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    # Get user_id from database (not from JWT)
    user = await crud.get_user_by_username(db, username)
    if not user:
        await websocket.close(code=1008, reason="User not found")
        return

    user_id = user.id
    print(f"Decoded JWT: username={username}, user_id={user_id}")

    # ----------------------------
    # 3️⃣ Confirm room exists
    # ----------------------------
    room = await crud.get_room(db, room_id)
    if not room:
        await websocket.close(code=1008, reason="Room not found")
        return

    # ----------------------------
    # 4️⃣ Confirm user is a participant
    # ----------------------------
    participant = await crud.get_participant_by_username_and_room(db, username, room_id)
    if not participant:
        await websocket.close(code=1008, reason="You are not a participant of this room")
        return

    # ----------------------------
    # 5️⃣ Send previous chat messages
    # ----------------------------
    recent_messages = await crud.get_recent_messages(db, room_id)

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

    # ----------------------------
    # 6️⃣ Connect to room
    # ----------------------------
    await manager.connect(room_id, websocket)
    print(f"User {user_id} connected to room {room_id}")

    # Callback used by TimerManager to broadcast timer updates
    async def timer_broadcast(room_id: int, remaining: int, is_running: bool):
        # Debug log to observe timer updates in server logs
        print(f"[TIMER] room={room_id} remaining={remaining} running={is_running}")
        # Keep track of disconnected connections
        disconnected = []

        # Get active connections for this room
        connections = manager.active_connections.get(room_id, [])

        for conn in connections:
            try:
                await conn.send_json(
                    {
                        "event": "timer_update",
                        "timer": {
                            "room_id": room_id,
                            "remaining": remaining,
                            "is_running": is_running,
                        },
                    }
                )
            except Exception:
                # WebSocket is closed, mark it for removal
                disconnected.append(conn)

        # Remove disconnected sockets from the manager
        for conn in disconnected:
            manager.disconnect(room_id, conn)

    # ----------------------------
    # 7️⃣ Main WebSocket loop
    # ----------------------------
    try:
        while True:
            data = await websocket.receive_json()

            # -----------------------
            # Timer events
            # -----------------------
            # TIMER FLOW
            if data.get("type") == "timer":
                content = data.get("content", {})
                event = content.get("event")

                try:
                    if event == "start_timer":
                        await timer_manager.start(
                            room_id, 
                            content.get("duration", 1500),
                            timer_broadcast
                        )
                        continue
                    # PAUSE
                    if event == "pause_timer":
                        await timer_manager.pause(room_id)
                        continue

                    # RESUME
                    if event == "resume_timer":
                        await timer_manager.resume(room_id, timer_broadcast)
                        continue

                    # RESET
                    if event == "reset_timer":
                        await timer_manager.reset(room_id, content.get("duration"), timer_broadcast)
                        continue

                    # If unknown timer event
                    await websocket.send_json({"error": "Unknown timer command"})
                    continue
                except Exception as e:
                    await websocket.send_json({"error": f"Timer error: {str(e)}"})
                    continue

            

            # -----------------------
            # Chat messages
            # -----------------------
            try:
                msg_in = WSMessageIn(**data)
            except Exception as e:
                await websocket.send_json({"error": f"Invalid message format: {str(e)}"})
                continue

            try:
                new_message = await crud.create_message_for_websocket(
                    db=db,
                    content=msg_in.content,
                    room_id=room_id,
                    user_id=user_id,
                )
            except SQLAlchemyError:
                await websocket.send_json({"error": "Database error"})
                continue

            user = await crud.get_user_by_id(db, user_id)

            message_out = WSMessageOut(
                id=new_message.id,
                content=new_message.content,
                timestamp=new_message.timestamp,
                user_id=user_id,
                username=user.username,
                room_id=room_id,
            )

            # Broadcast final formatted message
            await manager.broadcast(
                room_id,
                {
                    "event": "new_message",
                    "message": message_out.model_dump(),
                },
            )

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        # cancel timer task if no clients are left
        if not manager.active_connections.get(room_id):
            await timer_manager.stop(room_id)

        user = await crud.get_user_by_id(db, user_id)

        await manager.broadcast(
            room_id,
            {
                "event": "user_left",
                "user_id": user_id,
                "username": user.username if user else "Unknown"
            },
        )

        print(f"User {user_id} disconnected from room {room_id}")
