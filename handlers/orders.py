"""
Orders Handler — Display user orders and order details.
"""

from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from keyboards.menus import main_menu_keyboard
from middlewares.auth import check_banned, register_user, rate_limit
from services.order_service import get_user_orders, get_order
from utils.formatting import escape_md, fmt_date, paginate
from utils.logger import log_user_action
from config import PAGE_SIZE, ORDER_STATUS

logger = logging.getLogger("jah_shop.handlers.orders")

# Status icon map
_STATUS_ICON = {
    "pending":    "⏳",
    "processing": "🔄",
    "completed":  "✅",
    "cancelled":  "❌",
    "refunded":   "↩️",
}


# ─── Entry Point ──────────────────────────────────────────────

@register_user
@check_banned
@rate_limit
async def orders_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    log_user_action(user.id, "my_orders")
    await _show_orders(update.message, user.id, status_filter=None, page=0)


# ─── Callback Router ──────────────────────────────────────────

async def orders_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data.startswith("orders:filter:"):
        # orders:filter:<status>:<page>
        parts = data.split(":")
        status_filter = parts[2] if parts[2] != "all" else None
        page = int(parts[3])
        await _show_orders(query, user.id, status_filter, page)

    elif data.startswith("orders:view:"):
        # orders:view:<order_id>
        order_id = data.split(":", 2)[2]
        await _show_order_detail(query, user.id, order_id)

    elif data.startswith("orders:back:"):
        # orders:back:<status_filter>:<page>
        parts = data.split(":")
        status_filter = parts[2] if parts[2] != "all" else None
        page = int(parts[3])
        await _show_orders(query, user.id, status_filter, page)

    elif data == "noop":
        pass


# ─── Order List ───────────────────────────────────────────────

async def _show_orders(
    message_or_query,
    user_id: int,
    status_filter: str | None,
    page: int,
) -> None:
    all_orders = get_user_orders(user_id)

    # Filter
    if status_filter and status_filter != "all":
        filtered = [o for o in all_orders if o.status == status_filter]
    else:
        filtered = all_orders

    # Build filter tab buttons (always shown at top)
    filter_buttons = [
        [
            InlineKeyboardButton("⏳ Pending",    callback_data="orders:filter:pending:0"),
            InlineKeyboardButton("🔄 Processing", callback_data="orders:filter:processing:0"),
        ],
        [
            InlineKeyboardButton("✅ Completed",  callback_data="orders:filter:completed:0"),
            InlineKeyboardButton("❌ Cancelled",  callback_data="orders:filter:cancelled:0"),
        ],
        [InlineKeyboardButton("📋 All Orders", callback_data="orders:filter:all:0")],
    ]

    if not filtered:
        filter_key = status_filter or "all"
        filter_label = ORDER_STATUS.get(filter_key, "All") if filter_key != "all" else "All"
        text = (
            f"📦 *My Orders*\n\n"
            f"_No {escape_md(filter_label)} orders found\\._"
        )
        kb = InlineKeyboardMarkup(filter_buttons)
        if hasattr(message_or_query, "edit_message_text"):
            await message_or_query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)
        else:
            await message_or_query.reply_text(text, parse_mode="MarkdownV2", reply_markup=kb)
        return

    page_items, total_pages, current_page = paginate(filtered, page, PAGE_SIZE)

    # Header
    active_filter = status_filter or "all"
    lines = [f"📦 *My Orders* \\({len(filtered)} order{'s' if len(filtered) != 1 else ''}\\)\n"]

    # Order rows as inline buttons (tappable for detail)
    order_buttons: list[list[InlineKeyboardButton]] = []
    for order in page_items:
        icon = _STATUS_ICON.get(order.status, "❓")
        label = f"{icon} {order.product_name[:22]} — ${order.final_price:.2f}"
        order_buttons.append([
            InlineKeyboardButton(label, callback_data=f"orders:view:{order.id}")
        ])

    # Pagination nav
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(
            "◀️ Prev",
            callback_data=f"orders:filter:{active_filter}:{current_page - 1}",
        ))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(
            f"{current_page + 1}/{total_pages}",
            callback_data="noop",
        ))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "Next ▶️",
            callback_data=f"orders:filter:{active_filter}:{current_page + 1}",
        ))

    all_buttons = list(filter_buttons) + order_buttons
    if nav:
        all_buttons.append(nav)

    text = (
        f"📦 *My Orders*\n\n"
        f"Showing *{escape_md(ORDER_STATUS.get(active_filter, 'All'))}* "
        f"\\({len(filtered)} total\\)\n\n"
        f"_Tap an order to see details_"
    )

    kb = InlineKeyboardMarkup(all_buttons)

    if hasattr(message_or_query, "edit_message_text"):
        await message_or_query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)
    else:
        await message_or_query.reply_text(text, parse_mode="MarkdownV2", reply_markup=kb)


# ─── Order Detail ─────────────────────────────────────────────

async def _show_order_detail(query, user_id: int, order_id: str) -> None:
    order = get_order(order_id)

    # Security: users can only view their own orders
    if not order or order.user_id != user_id:
        await query.edit_message_text(
            "❌ Order not found\\.",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="orders:filter:all:0")
            ]]),
        )
        return

    icon = _STATUS_ICON.get(order.status, "❓")
    status_label = ORDER_STATUS.get(order.status, order.status)

    promo_line = ""
    if order.promo_code and order.discount > 0:
        promo_line = (
            f"\n🎟 *Promo Code:* `{escape_md(order.promo_code)}`"
            f"\n🏷 *Discount:* `\\-${escape_md(f'{order.discount:.2f}')}`"
        )

    note_line = ""
    if order.admin_note:
        note_line = f"\n📝 *Note:* _{escape_md(order.admin_note)}_"

    delivery_section = ""
    if order.status == "completed" and order.delivery_data:
        delivery_section = (
            f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📬 *Delivery Information*\n\n"
            f"`{escape_md(order.delivery_data)}`"
        )
    elif order.status == "completed":
        delivery_section = (
            f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📬 *Delivery:* _Contact support for delivery details_"
        )

    text = (
        f"📦 *Order Details*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 *Product:* {escape_md(order.product_name)}\n"
        f"💰 *Price:* `${escape_md(f'{order.price:.2f}')}`"
        f"{promo_line}\n"
        f"✅ *Total Paid:* `${escape_md(f'{order.final_price:.2f}')}`\n"
        f"💱 *Currency:* {escape_md(order.currency)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order ID:* `{escape_md(order.id)}`\n"
        f"📊 *Status:* {icon} {escape_md(status_label)}"
        f"{note_line}\n"
        f"📅 *Placed:* {escape_md(fmt_date(order.created_at))}"
        f"{delivery_section}"
    )

    back_cb = "orders:filter:all:0"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Back to Orders", callback_data=back_cb)
    ]])

    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)
