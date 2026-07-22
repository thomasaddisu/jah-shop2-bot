"""
User Service — CRUD operations for users.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import USERS_FILE
from models.models import User
from services.database import get_db

logger = logging.getLogger("jah_shop.user_service")
_db = get_db(USERS_FILE, {"users": []})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_users() -> list[dict]:
    return _db.read().get("users", [])


def _save_users(users: list[dict]) -> None:
    _db.write({"users": users})


# ─── Public API ──────────────────────────────────────────────

def get_user(user_id: int) -> User | None:
    for u in _load_users():
        if u.get("user_id") == user_id:
            return User.from_dict(u)
    return None


def get_all_users() -> list[User]:
    return [User.from_dict(u) for u in _load_users()]


def upsert_user(tg_user) -> User:
    """Create or update user from a Telegram User object."""
    users = _load_users()
    uid = tg_user.id
    existing = next((u for u in users if u.get("user_id") == uid), None)

    if existing:
        existing["username"] = tg_user.username or ""
        existing["first_name"] = tg_user.first_name or ""
        existing["last_name"] = tg_user.last_name or ""
        existing["last_active"] = _now()
        existing["language_code"] = getattr(tg_user, "language_code", "en") or "en"
        _save_users(users)
        return User.from_dict(existing)
    else:
        user = User(
            user_id=uid,
            username=tg_user.username or "",
            first_name=tg_user.first_name or "",
            last_name=tg_user.last_name or "",
            language_code=getattr(tg_user, "language_code", "en") or "en",
        )
        users.append(user.to_dict())
        _save_users(users)
        logger.info(f"New user registered: {uid} (@{user.username})")
        return user


def ban_user(user_id: int) -> bool:
    users = _load_users()
    for u in users:
        if u.get("user_id") == user_id:
            u["is_banned"] = True
            _save_users(users)
            return True
    return False


def unban_user(user_id: int) -> bool:
    users = _load_users()
    for u in users:
        if u.get("user_id") == user_id:
            u["is_banned"] = False
            _save_users(users)
            return True
    return False


def is_banned(user_id: int) -> bool:
    user = get_user(user_id)
    return user.is_banned if user else False


def search_users(query: str) -> list[User]:
    query = query.lower().strip()
    results = []
    for u in _load_users():
        if (
            query in str(u.get("user_id", ""))
            or query in (u.get("username", "") or "").lower()
            or query in (u.get("first_name", "") or "").lower()
            or query in (u.get("last_name", "") or "").lower()
        ):
            results.append(User.from_dict(u))
    return results


def get_user_count() -> int:
    return len(_load_users())
