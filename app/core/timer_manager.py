# app/core/timer_manager.py
import asyncio
from typing import Callable, Dict, Optional

class TimerInfo:
    def __init__(self, duration: int, remaining: int, is_running: bool):
        self.duration = duration
        self.remaining = remaining
        self.is_running = is_running

class TimerManager:
    """
    Manages one timer per room (in-memory). Each running timer runs in its own asyncio.Task.
    The manager calls a callback every second with (room_id, remaining, is_running, duration).
    """

    def __init__(self):
        # room_id -> TimerInfo
        self.timers: Dict[int, TimerInfo] = {}
        # room_id -> asyncio.Task
        self.tasks: Dict[int, asyncio.Task] = {}
        # protect concurrent operations if needed
        self._lock = asyncio.Lock()

    async def start(self, room_id: int, duration: int, broadcast_cb: Callable[[int, int, bool, int], asyncio.Future]):
        """
        Start or restart a timer for a room.
        broadcast_cb(room_id, remaining, is_running, duration) will be awaited every second.
        """
        async with self._lock:
            info = self.timers.get(room_id)
            # If a task exists and is running, cancel it and replace
            if info and self.tasks.get(room_id):
                # stop current before restart
                task = self.tasks.get(room_id)
                if task:
                    task.cancel()
                self.timers.pop(room_id, None)
                self.tasks.pop(room_id, None)

            self.timers[room_id] = TimerInfo(duration=duration, remaining=duration, is_running=True)

            # create background task
            task = asyncio.create_task(self._run(room_id, duration, broadcast_cb))
            self.tasks[room_id] = task

    async def _run(self, room_id: int, duration: int, broadcast_cb: Callable[[int, int, bool, int], asyncio.Future]):
        try:
            while True:
                async with self._lock:
                    info = self.timers.get(room_id)
                    if not info or not info.is_running:
                        # send final state
                        remaining = info.remaining if info else 0
                        dur = info.duration if info else duration
                        await broadcast_cb(room_id, remaining, False, dur)
                        break
                    if info.remaining <= 0:
                        info.is_running = False
                        await broadcast_cb(room_id, 0, False, info.duration)
                        break

                await asyncio.sleep(1)
                async with self._lock:
                    info = self.timers.get(room_id)
                    if not info or not info.is_running:
                        break
                    info.remaining = max(0, info.remaining - 1)
                    # broadcast update
                    await broadcast_cb(room_id, info.remaining, True, info.duration)
        except asyncio.CancelledError:
            # broadcast stopped state
            async with self._lock:
                info = self.timers.get(room_id)
            if info:
                await broadcast_cb(room_id, info.remaining, info.is_running, info.duration)
            raise
        finally:
            # cleanup task entry
            async with self._lock:
                self.tasks.pop(room_id, None)

    async def pause(self, room_id: int):
        async with self._lock:
            info = self.timers.get(room_id)
            if info:
                info.is_running = False

    async def resume(self, room_id: int, broadcast_cb: Callable[[int, int, bool, int], asyncio.Future]):
        async with self._lock:
            info = self.timers.get(room_id)
            if not info:
                return
            if info.is_running:
                return  # already running
            info.is_running = True
            task = asyncio.create_task(self._run(room_id, info.duration, broadcast_cb))
            self.tasks[room_id] = task

    async def stop(self, room_id: int):
        async with self._lock:
            task = self.tasks.get(room_id)
            if task:
                task.cancel()
            self.timers.pop(room_id, None)
            self.tasks.pop(room_id, None)

    async def reset(self, room_id: int, duration: Optional[int], broadcast_cb: Callable[[int, int, bool, int], asyncio.Future]):
        async with self._lock:
            if duration is not None:
                self.timers[room_id] = TimerInfo(duration=duration, remaining=duration, is_running=False)
            else:
                info = self.timers.get(room_id)
                if info:
                    info.remaining = info.duration
                    info.is_running = False
        # broadcast reset state (outside lock)
        info = self.timers.get(room_id)
        if info:
            await broadcast_cb(room_id, info.remaining, info.is_running, info.duration)

    async def get_state(self, room_id: int):
        async with self._lock:
            info = self.timers.get(room_id)
            if not info:
                return None
            return {"duration": info.duration, "remaining": info.remaining, "is_running": info.is_running}

# Singleton instance to import from other modules
timer_manager = TimerManager()
