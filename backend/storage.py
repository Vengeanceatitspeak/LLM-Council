"""JSON-based storage for conversations and credit tracking."""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR, DAILY_CREDIT_LIMIT


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_conversation_path(conversation_id: str) -> str:
    """Get the file path for a conversation."""
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


def get_usage_path() -> str:
    """Get the file path for usage tracking."""
    return os.path.join(os.path.dirname(DATA_DIR), "usage.json")


# ─── Conversation CRUD ──────────────────────────────────────────────────────

def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    ensure_data_dir()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "New Conversation",
        "messages": []
    }

    # Save to file
    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict to save
    """
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Returns:
        List of conversation metadata dicts
    """
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    # Return metadata only
                    conversations.append({
                        "id": data["id"],
                        "created_at": data["created_at"],
                        "title": data.get("title", "New Conversation"),
                        "message_count": len(data["messages"])
                    })
            except (json.JSONDecodeError, KeyError):
                continue

    # Sort by creation time, newest first
    conversations.sort(key=lambda x: x["created_at"], reverse=True)

    return conversations


def delete_conversation(conversation_id: str) -> bool:
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation identifier

    Returns:
        True if deleted, False if not found
    """
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return False

    os.remove(path)
    return True


def add_user_message(conversation_id: str, content: str):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "user",
        "content": content
    })

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    })

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(conversation)


# ─── Credit / Usage Tracking ────────────────────────────────────────────────

def _load_usage() -> Dict[str, Any]:
    """Load the usage data from disk."""
    path = get_usage_path()
    if not os.path.exists(path):
        return {"date": "", "count": 0}

    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"date": "", "count": 0}


def _save_usage(usage: Dict[str, Any]):
    """Save usage data to disk."""
    # Ensure parent directory exists
    path = get_usage_path()
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        json.dump(usage, f, indent=2)


def get_daily_usage() -> Dict[str, Any]:
    """
    Get the current daily usage.

    Returns:
        Dict with 'used', 'limit', 'remaining', 'date', 'percentage'
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage = _load_usage()

    # Reset if it's a new day
    if usage.get("date") != today:
        usage = {"date": today, "count": 0}
        _save_usage(usage)

    count = usage.get("count", 0)
    return {
        "used": count,
        "limit": DAILY_CREDIT_LIMIT,
        "remaining": max(0, DAILY_CREDIT_LIMIT - count),
        "date": today,
        "percentage": min(100, round((count / DAILY_CREDIT_LIMIT) * 100, 1))
    }


def increment_usage() -> Dict[str, Any]:
    """
    Increment the daily usage counter.

    Returns:
        Updated usage dict (same format as get_daily_usage)
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage = _load_usage()

    # Reset if it's a new day
    if usage.get("date") != today:
        usage = {"date": today, "count": 0}

    usage["count"] = usage.get("count", 0) + 1
    _save_usage(usage)

    count = usage["count"]
    return {
        "used": count,
        "limit": DAILY_CREDIT_LIMIT,
        "remaining": max(0, DAILY_CREDIT_LIMIT - count),
        "date": today,
        "percentage": min(100, round((count / DAILY_CREDIT_LIMIT) * 100, 1))
    }


def check_credit_available() -> bool:
    """
    Check if there are credits remaining for today.

    Returns:
        True if credits available, False if limit reached
    """
    usage = get_daily_usage()
    return usage["remaining"] > 0
