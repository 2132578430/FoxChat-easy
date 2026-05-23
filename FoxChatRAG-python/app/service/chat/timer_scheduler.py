"""
Timer Scheduler Module

Background timer service that checks all active conversations periodically
and triggers summary when minimum threshold is reached after timer interval.

Hybrid Trigger Mechanism:
- Timer-based trigger: check every 45s, execute if ≥18 messages accumulated
- Max threshold trigger: forced execution when ≥30 messages (in chat_msg_service)
- Max retention limit: hard cap at 40 messages

Timer State Storage (Redis):
- Key: summary_timer:{user_id}:{llm_id}
- Value: Unix timestamp of last summary completion
- TTL: 7200s (2 hours) - auto-cleanup inactive sessions
"""

import asyncio
import time
from typing import List, Tuple

from loguru import logger

from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.core.db.redis_client import redis_client

# Constants for hybrid trigger mechanism
TIMER_CHECK_INTERVAL = 45  # Timer interval in seconds (how often to check)
SUMMARY_MIN_TRIGGER_THRESHOLD = 18  # Minimum messages for timer trigger
SUMMARY_MAX_TRIGGER_THRESHOLD = 30  # Max threshold (handled in chat_msg_service)
MAX_RECENT_MSG_SIZE = 40  # Hard cap to prevent extreme accumulation


def get_last_summary_time(user_id: str, llm_id: str) -> float:
    """
    Get last summary completion time from Redis.

    Args:
        user_id: User ID
        llm_id: LLM/character ID

    Returns:
        Unix timestamp (float) of last summary, or 0.0 if never summarized
    """
    key = f"summary_timer:{user_id}:{llm_id}"
    value = redis_client.get(key)
    return float(value) if value else 0.0


def reset_timer(user_id: str, llm_id: str) -> None:
    """
    Reset timer state after summary completion.

    Updates Redis key with current timestamp and TTL.

    Args:
        user_id: User ID
        llm_id: LLM/character ID
    """
    key = f"summary_timer:{user_id}:{llm_id}"
    current_time = time.time()
    redis_client.set(key, str(current_time), ex=7200)  # TTL 2 hours
    logger.debug(f"[Timer] Reset timer for {user_id}:{llm_id}")


def get_active_sessions() -> List[Tuple[str, str]]:
    """
    Discover all active conversations by scanning Redis keys.

    Pattern: chat:memory:*:recent_msg

    Returns:
        List of (user_id, llm_id) tuples for active sessions
    """
    pattern = "chat:memory:*:recent_msg"
    keys = redis_client.keys(pattern)

    sessions = []
    for key in keys:
        # Parse key format: chat:memory:{user_id}:{llm_id}:recent_msg
        parts = key.split(":")
        if len(parts) >= 4:
            user_id = parts[2]
            llm_id = parts[3]
            sessions.append((user_id, llm_id))

    # Only log when sessions found (avoid spamming empty checks)
    if sessions:
        logger.debug(f"[Timer] Found {len(sessions)} active sessions")

    return sessions


async def timer_summary_check_single(user_id: str, llm_id: str) -> None:
    """
    Check single conversation for timer trigger.

    Trigger condition:
    - recent_msg_size >= SUMMARY_MIN_TRIGGER_THRESHOLD (18 messages)
    - elapsed time since last summary >= TIMER_CHECK_INTERVAL (45s)

    Args:
        user_id: User ID
        llm_id: LLM/character ID
    """
    recent_msg_key = build_memory_key(LLMChatConstant.RECENT_MSG, user_id, llm_id)
    recent_msg_size = redis_client.llen(recent_msg_key)

    # Empty call optimization: skip if insufficient messages
    # Skip logging to avoid spamming DEBUG logs every 5s
    if recent_msg_size < SUMMARY_MIN_TRIGGER_THRESHOLD:
        return

    # Check timer interval elapsed
    current_time = time.time()
    last_summary_time = get_last_summary_time(user_id, llm_id)
    elapsed = current_time - last_summary_time

    if elapsed < TIMER_CHECK_INTERVAL:
        # Skip logging to avoid spamming DEBUG logs every 5s
        return

    # Timer interval elapsed, trigger summary (log this important event)
    logger.info(f"[Timer] {user_id}:{llm_id} elapsed {elapsed:.1f}s >= {TIMER_CHECK_INTERVAL}s, trigger summary (size={recent_msg_size})")

    # Import here to avoid circular dependency
    from app.service.chat.memory_summary_service import trigger_summary_with_counter

    await trigger_summary_with_counter(
        recent_msg_key,
        recent_msg_size,
        user_id,
        llm_id,
        trigger_source="timer"
    )


async def timer_scheduler() -> None:
    """
    Timer scheduler main loop.

    Runs continuously as background task, checking active sessions
    every TIMER_CHECK_INTERVAL (45s) for elapsed timer intervals.

    This scheduler implements the timer-based half of the hybrid trigger:
    - Slow-chat scenarios: trigger when ≥18 messages accumulated after 45s interval
    - Fast-chat scenarios: max threshold trigger (handled elsewhere) fires first

    Resource optimization:
    - Only scans Redis every 45s (not every 5s) to save CPU/Redis resources
    - ±45s timing precision is acceptable for slow-chat scenarios
    """
    logger.info("[Timer Scheduler] Starting timer scheduler background task")

    while True:
        try:
            # Sleep for check interval (45s - resource optimization)
            await asyncio.sleep(TIMER_CHECK_INTERVAL)

            # Discover all active sessions
            active_sessions = get_active_sessions()

            # Check each session
            for user_id, llm_id in active_sessions:
                try:
                    await timer_summary_check_single(user_id, llm_id)
                except Exception as e:
                    logger.warning(f"[Timer] Error checking {user_id}:{llm_id}: {e}")
                    # Continue checking other sessions even if one fails

        except Exception as e:
            logger.error(f"[Timer Scheduler] Loop error: {e}")
            # Sleep a bit longer on error, then continue
            await asyncio.sleep(60)