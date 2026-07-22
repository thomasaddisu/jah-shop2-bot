"""
Text Formatting Utilities — MarkdownV2 safe helpers.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


# Characters that must be escaped in MarkdownV2
_MDV2_SPECIAL = r"\_*[]()~`>#+-=|{}.!"


def escape_md(text: str) -> str:
    """Escape all MarkdownV2 special characters."""
    if not text:
        return ""
    return re.sub(r"([_\*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


def bold(text: str) -> str:
    return f"*{escape_md(text)}*"


def italic(text: str) -> str:
    return f"_{escape_md(text)}_"


def code(text: str) -> str:
    return f"`{escape_md(text)}`"


def link(text: str, url: str) -> str:
    return f"[{escape_md(text)}]({url})"


def fmt_price(amount: float, currency: str = "USD") -> str:
    return f"${amount:.2f} {currency}"


def fmt_date(iso_str: str) -> str:
    """Format ISO datetime string to human-readable."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return iso_str


def fmt_date_short(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return iso_str


def paginate(items: list, page: int, page_size: int) -> tuple[list, int, int]:
    """
    Returns (page_items, total_pages, current_page).
    page is 0-indexed.
    """
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return items[start:start + page_size], total_pages, page


def truncate(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def status_emoji(status: str) -> str:
    mapping = {
        "pending": "⏳",
        "processing": "🔄",
        "completed": "✅",
        "cancelled": "❌",
        "refunded": "↩️",
        "approved": "✅",
        "rejected": "❌",
        "open": "📬",
        "replied": "💬",
        "closed": "🔒",
        "active": "🟢",
        "inactive": "🔴",
    }
    return mapping.get(status, "❓")


def number_to_emoji(n: int) -> str:
    emojis = ["0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    result = ""
    for ch in str(n):
        if ch.isdigit():
            result += emojis[int(ch)]
        else:
            result += ch
    return result
