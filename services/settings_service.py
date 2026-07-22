"""
Settings Service — Bot-wide configuration management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from config import SETTINGS_FILE
from services.database import get_db

logger = logging.getLogger("jah_shop.settings_service")
_db = get_db(SETTINGS_FILE, {
    "bot_name": "Jah Shop",
    "currency": "USD",
    "support_username": "support",
    "usdt_address": "",
    "bank_details": "",
    "maintenance_mode": False,
    "order_notifications": True,
    "admin_notifications": True,
    "welcome_message": "Welcome to Jah Shop! 🛍️",
    "min_topup_amount": 1.0,
    "max_topup_amount": 10000.0,
    "updated_at": datetime.now(timezone.utc).isoformat(),
})


def get_all() -> dict:
    return _db.read()


def get(key: str, default: Any = None) -> Any:
    return _db.read().get(key, default)


def set(key: str, value: Any) -> None:
    data = _db.read()
    data[key] = value
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _db.write(data)
    logger.info(f"Setting updated: {key} = {value}")


def update_many(updates: dict) -> dict:
    data = _db.read()
    data.update(updates)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _db.write(data)
    return data


def is_maintenance() -> bool:
    return bool(get("maintenance_mode", False))


def get_currency() -> str:
    return get("currency", "USD")


def get_bot_name() -> str:
    return get("bot_name", "Jah Shop")


def get_welcome_message() -> str:
    return get("welcome_message", "Welcome to Jah Shop! 🛍️")


def get_usdt_address() -> str:
    from config import USDT_ADDRESS
    return get("usdt_address", "") or USDT_ADDRESS


def get_bank_details() -> str:
    from config import BANK_DETAILS
    return get("bank_details", "") or BANK_DETAILS


def get_support_username() -> str:
    from config import SUPPORT_USERNAME
    return get("support_username", "") or SUPPORT_USERNAME
