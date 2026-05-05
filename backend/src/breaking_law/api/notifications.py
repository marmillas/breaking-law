"""
SSE notifications stream for the legal platform.

Provides a Server-Sent Events endpoint that subscribes to a Redis
pub/sub channel per user and forwards messages as SSE events.
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from breaking_law.api.deps import get_config, get_current_user_from_query_token, UserContext

router = APIRouter(
    prefix="/api/notifications",
    tags=["notifications"],
)


async def _event_stream(user: UserContext) -> AsyncGenerator[str, None]:
    """Yield SSE events from Redis pub/sub for the given user."""
    cfg = get_config()
    redis = Redis.from_url(cfg.REDIS_URL, decode_responses=True)
    channel = f"user:{user.user_id}:notifications"
    pubsub = redis.pubsub()

    try:
        await pubsub.subscribe(channel)
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=30.0
            )
            if message is not None:
                data = message.get("data", "")
                if data:
                    try:
                        payload = json.loads(data)
                        event_type = payload.get("type", "message")
                    except json.JSONDecodeError:
                        event_type = "message"
                        payload = {"message": data}
                    yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
            else:
                # Heartbeat to keep connection alive through proxies
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        # Client disconnected — re-raise so FastAPI cleans up the response
        raise
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            pass
        await redis.close()


@router.get("/stream")
async def notifications_stream(
    token: str = Query(..., description="JWT access token"),
    user: UserContext = Depends(get_current_user_from_query_token),
):
    """
    Subscribe to real-time notifications via Server-Sent Events.

    The client must provide the JWT access token as a query parameter
    because browser EventSource cannot send custom Authorization headers.
    """
    return StreamingResponse(
        _event_stream(user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
