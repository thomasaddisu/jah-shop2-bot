"""
Support Service — Customer support message management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import SUPPORT_MESSAGES_FILE
from models.models import SupportMessage
from services.database import get_db

logger = logging.getLogger("jah_shop.support_service")
_db = get_db(SUPPORT_MESSAGES_FILE, {"support_messages": []})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict]:
    return _db.read().get("support_messages", [])


def _save(messages: list[dict]) -> None:
    _db.write({"support_messages": messages})


# ─── Public API ──────────────────────────────────────────────

def create_support_message(user_id: int, message: str) -> SupportMessage:
    messages = _load()
    msg = SupportMessage(user_id=user_id, message=message)
    messages.append(msg.to_dict())
    _save(messages)
    logger.info(f"Support message created: {msg.id} from user {user_id}")
    return msg


def get_support_message(msg_id: str) -> SupportMessage | None:
    for m in _load():
        if m.get("id") == msg_id:
            return SupportMessage.from_dict(m)
    return None


def get_open_messages() -> list[SupportMessage]:
    return [SupportMessage.from_dict(m) for m in _load() if m.get("status") == "open"]


def get_all_messages() -> list[SupportMessage]:
    msgs = [SupportMessage.from_dict(m) for m in _load()]
    return sorted(msgs, key=lambda m: m.created_at, reverse=True)


def get_user_messages(user_id: int) -> list[SupportMessage]:
    msgs = [SupportMessage.from_dict(m) for m in _load() if m.get("user_id") == user_id]
    return sorted(msgs, key=lambda m: m.created_at, reverse=True)


def reply_to_message(msg_id: str, reply: str, admin_id: int) -> SupportMessage | None:
    messages = _load()
    for m in messages:
        if m.get("id") == msg_id:
            m["reply"] = reply
            m["status"] = "replied"
            m["admin_id"] = admin_id
            m["replied_at"] = _now()
            _save(messages)
            logger.info(f"Support message {msg_id} replied by admin {admin_id}")
            return SupportMessage.from_dict(m)
    return None


def close_message(msg_id: str) -> bool:
    messages = _load()
    for m in messages:
        if m.get("id") == msg_id:
            m["status"] = "closed"
            _save(messages)
            return True
    return False
