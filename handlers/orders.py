"""
Orders Handler — Display user orders.
"""

from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from keyboards.menus import main_menu_keyboard
from middlewares.auth import check_banned, register_user, rate_limit
from services.order_service import get_user_orders
from utils.formatting import escape_md, fmt_date, paginate
from utils.logger import log_user_action
from config import PAGE_SIZE, ORDER_STATUS

logger = logging.getLogger("jah_shop.handlers.orders")


@register_user
@check_banned
@rate_limit
async def orders_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    log_user_action(user.id, "my_orders")
    await _show_orders(update.message, user.id, status_filter=None, page=0)


async def _show_orders(message_or_query, user_id: int, status_filter: str | None, page: int) -> None:
    all_orders = get_user_orders(user_id)

    # Build status filter buttons
    status_buttons = [
        [
            InlineKeyboardButton("⏳ Pending", callback_data="orders:filter:pending:0"),
            InlineKeyboardButton("🔄 Processing", callback_data="orders:filter:processing:0"),
        ],
        [
            InlineKeyboardButton("✅ Completed", callback_data="orders:filter:completed:0"),
            InlineKeyboardButton("❌ Cancelled", callback_data="orders:filter:cancelled:0"),
        ],
        [InlineKeyboardButton("📋 All Orders", callback_data="orders:filter:all:0")],
    ]

    if status_filter and status_filter != "all":
        filtered = [o for o in all_orders if o.status == status_filter]
    else:
        filtered = all_orders

    if not filtered:
        filter_label = ORDER_STATUS.get(status_filter, "All") if status_filter else "All"
        text = (
            f"📦 *My Orders*\n\n"
            f"_No {escape_md(filter_label)} orders found\\._"
        )
        kb = InlineKeyboardMarkup(status_buttons)
        if hasattr(message_or_query, "edit_message_text"):
            await message_or_query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)
        else:
            await message_or_query.reply_text(text, parse_mode="MarkdownV2", reply_markup=kb)
        return

    page_items, total_pages, current_page = paginate(filtered, page, PAGE_SIZE)

    lines = [f"📦 *My Orders* \\({len(filtered)} orders\\)\n"]
    for order in page_items:
        status_label = ORDER_STATUS.get(order.status, order.status)
        lines.append(
            f"─────────────────\n"
            f"📦 *{escape_md(order.product_name)}*\n"
            f"💰 `${order.final_price:.2f}` | {status_label}\n"
            f"🆔 `{escape_md(order.id)}`\n"
            f"📅 {escape_md(fmt_date(order.created_at))}"
        )

    nav = []
    if current_page > 0:
        prev_data = f"orders:filter:{status_filter or 'all'}:{current_page - 1}"
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=prev_data))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        next_data = f"orders:filter:{status_filter or 'all'}:{current_page + 1}"
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=next_data))

    all_buttons = list(status_buttons)
    if nav:
        all_buttons.append(nav)

    kb = InlineKeyboardMarkup(all_buttons)
    text = "\n".join(lines)

    if hasattr(message_or_query, "edit_message_text"):
        await message_or_query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)
    else:
        await message_or_query.reply_text(text, parse_mode="MarkdownV2", reply_markup=kb)


async def orders_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data.startswith("orders:filter:"):
        parts = data.split(":")
        status_filter = parts[2] if parts[2] != "all" else None
        page = int(parts[3])
        await _show_orders(query, user.id, status_filter, page)

    elif data == "noop":
        pass
