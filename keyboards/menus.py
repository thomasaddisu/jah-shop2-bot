"""
Main Menu Keyboards — ReplyKeyboardMarkup and shared inline keyboards.
"""

from __future__ import annotations

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from config import ADMIN_IDS


def main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Build the main menu reply keyboard (admin-aware)."""
    buttons = [
        ["🛍 Shop", "👛 Wallet"],
        ["📦 My Orders", "🎁 Promo Codes"],
        ["📞 Support", "ℹ️ About"],
    ]
    if user_id in ADMIN_IDS:
        buttons.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, is_persistent=True)


def back_button(callback_data: str = "back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=callback_data)]])


def confirm_cancel_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=confirm_data),
            InlineKeyboardButton("❌ Cancel", callback_data=cancel_data),
        ]
    ])


def yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=yes_data),
            InlineKeyboardButton("❌ No", callback_data=no_data),
        ]
    ])
