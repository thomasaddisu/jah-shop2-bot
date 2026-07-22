"""
Wallet Keyboards — Top-up, payment method, transaction keyboards.
"""

from __future__ import annotations

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from config import PAYMENT_METHODS


def wallet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Top Up", callback_data="wallet:topup")],
        [InlineKeyboardButton("📜 Transactions", callback_data="wallet:transactions")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")],
    ])


def payment_method_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for method_key, method_name in PAYMENT_METHODS.items():
        buttons.append([InlineKeyboardButton(method_name, callback_data=f"topup_method:{method_key}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="wallet:menu")])
    return InlineKeyboardMarkup(buttons)


def transactions_keyboard(page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"txn_page:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"txn_page:{page + 1}"))

    buttons = []
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="wallet:menu")])
    return InlineKeyboardMarkup(buttons)
