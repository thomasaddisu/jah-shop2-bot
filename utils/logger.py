"""
Logger Utility — Structured action logging to file and memory.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from config import LOGS_DIR

_action_logger = logging.getLogger("jah_shop.actions")


def _log_to_file(category: str, data: dict) -> None:
    log_file = LOGS_DIR / f"{category}.log"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def log_user_action(user_id: int, action: str, details: str = "") -> None:
    _log_to_file("user_activity", {"user_id": user_id, "action": action, "details": details})
    _action_logger.info(f"USER {user_id} | {action} | {details}")


def log_admin_action(admin_id: int, action: str, details: str = "") -> None:
    _log_to_file("admin_activity", {"admin_id": admin_id, "action": action, "details": details})
    _action_logger.info(f"ADMIN {admin_id} | {action} | {details}")


def log_order(order_id: str, user_id: int, product: str, amount: float, status: str) -> None:
    _log_to_file("orders", {
        "order_id": order_id, "user_id": user_id,
        "product": product, "amount": amount, "status": status,
    })


def log_wallet(user_id: int, op: str, amount: float, balance: float) -> None:
    _log_to_file("wallet", {
        "user_id": user_id, "operation": op,
        "amount": amount, "new_balance": balance,
    })


def log_support(user_id: int, msg_id: str, action: str) -> None:
    _log_to_file("support", {"user_id": user_id, "msg_id": msg_id, "action": action})


def log_broadcast(admin_id: int, total: int, success: int, failed: int) -> None:
    _log_to_file("broadcast", {
        "admin_id": admin_id, "total": total,
        "success": success, "failed": failed,
    })


def log_error(context: str, error: str) -> None:
    _log_to_file("errors", {"context": context, "error": error})
    _action_logger.error(f"ERROR | {context} | {error}")


def read_log_file(category: str, lines: int = 50) -> list[dict]:
    """Read the last N lines from a log file."""
    log_file = LOGS_DIR / f"{category}.log"
    if not log_file.exists():
        return []
    results = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        for line in all_lines[-lines:]:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    results.append({"raw": line})
    except Exception:
        pass
    return results


def export_log(category: str) -> Path | None:
    log_file = LOGS_DIR / f"{category}.log"
    return log_file if log_file.exists() else None
