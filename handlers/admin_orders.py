"""
Admin Orders Handler
"""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_orders_keyboard, admin_order_actions_keyboard
from services.order_service import (
    get_all_orders, get_order, update_order_status, complete_order,
    refund_order, search_orders,
)
from services.wallet_service import credit_wallet
from utils.formatting import escape_md, fmt_date, paginate
from utils.logger import log_admin_action
from config import ADMIN_IDS, PAGE_SIZE, ORDER_STATUS

logger = logging.getLogger("jah_shop.handlers.admin_orders")
_state: dict[int, dict] = {}


async def admin_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    data = query.data

    if data == "admin:orders":
        await query.edit_message_text(
            "📦 *Order Management*", parse_mode="MarkdownV2",
            reply_markup=admin_orders_keyboard()
        )

    elif data.startswith("admin_ord:list:"):
        parts = data.split(":")
        status = parts[2]
        page = int(parts[3])
        await _list_orders(query, status if status != "all" else None, page)

    elif data.startswith("admin_ord:view:"):
        oid = data.split(":")[2]
        await _view_order(query, oid)

    elif data.startswith("admin_ord:complete:"):
        oid = data.split(":")[2]
        _state[admin_id] = {"action": "complete", "order_id": oid}
        context.user_data["admin_ord_state"] = True
        await query.edit_message_text(
            "✅ Enter delivery data \\(credentials, link, etc\\.\\) to send to customer\\.\n"
            "Or type `skip` to complete without delivery data:",
            parse_mode="MarkdownV2",
        )

    elif data.startswith("admin_ord:processing:"):
        oid = data.split(":")[2]
        order = update_order_status(oid, "processing")
        log_admin_action(admin_id, "order_processing", oid)
        await _notify_user_order_update(context, order)
        await _view_order(query, oid)

    elif data.startswith("admin_ord:cancel:"):
        oid = data.split(":")[2]
        order = update_order_status(oid, "cancelled")
        log_admin_action(admin_id, "order_cancel", oid)
        await _notify_user_order_update(context, order)
        await _view_order(query, oid)

    elif data.startswith("admin_ord:refund:"):
        oid = data.split(":")[2]
        order = get_order(oid)
        if order and order.status == "completed":
            refund_order(oid)
            credit_wallet(order.user_id, order.final_price, f"Refund for order {oid}", oid)
            log_admin_action(admin_id, "order_refund", oid)
            await _notify_user_order_update(context, get_order(oid))
        await _view_order(query, oid)

    elif data == "admin_ord:search":
        _state[admin_id] = {"action": "search"}
        context.user_data["admin_ord_state"] = True
        await query.edit_message_text("🔍 Enter order ID, user ID, or product name:")


async def _list_orders(query, status: str | None, page: int) -> None:
    orders = get_all_orders(status)
    page_items, total_pages, current_page = paginate(orders, page, PAGE_SIZE)

    if not orders:
        label = ORDER_STATUS.get(status, "All") if status else "All"
        await query.edit_message_text(
            f"📦 No {label} orders found.",
            reply_markup=admin_orders_keyboard(),
        )
        return

    buttons = []
    for o in page_items:
        status_icon = {"pending": "⏳", "processing": "🔄", "completed": "✅", "cancelled": "❌"}.get(o.status, "❓")
        buttons.append([InlineKeyboardButton(
            f"{status_icon} {o.product_name[:20]} — ${o.final_price:.2f} | {o.id[:8]}",
            callback_data=f"admin_ord:view:{o.id}"
        )])

    nav = []
    s = status or "all"
    if current_page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin_ord:list:{s}:{current_page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin_ord:list:{s}:{current_page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:orders")])

    await query.edit_message_text(
        f"📦 *Orders* \\({len(orders)} total\\)",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _view_order(query, oid: str) -> None:
    order = get_order(oid)
    if not order:
        await query.edit_message_text("❌ Order not found.", reply_markup=admin_orders_keyboard())
        return
    status_label = ORDER_STATUS.get(order.status, order.status)
    promo = f"\n🎟 Promo: `{escape_md(order.promo_code)}`" if order.promo_code else ""
    delivery = f"\n📬 Delivery: `{escape_md(order.delivery_data)}`" if order.delivery_data else ""
    note = f"\n📝 Note: _{escape_md(order.admin_note)}_" if order.admin_note else ""
    text = (
        f"📦 *Order Details*\n\n"
        f"🆔 `{escape_md(order.id)}`\n"
        f"👤 User: `{order.user_id}`\n"
        f"📦 Product: {escape_md(order.product_name)}\n"
        f"💰 Price: `${order.price:.2f}` → `${order.final_price:.2f}`"
        f"{promo}\n"
        f"📊 Status: {status_label}"
        f"{delivery}{note}\n"
        f"📅 {escape_md(fmt_date(order.created_at))}"
    )
    await query.edit_message_text(
        text, parse_mode="MarkdownV2",
        reply_markup=admin_order_actions_keyboard(order.id, order.status),
    )


async def _notify_user_order_update(context, order) -> None:
    if not order:
        return
    status_label = ORDER_STATUS.get(order.status, order.status)
    try:
        await context.bot.send_message(
            chat_id=order.user_id,
            text=(
                f"📦 *Order Update*\n\n"
                f"Your order `{escape_md(order.id)}` status:\n"
                f"*{status_label}*"
                + (f"\n\n📬 *Delivery:*\n`{escape_md(order.delivery_data)}`" if order.delivery_data else "")
            ),
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.warning(f"Could not notify user {order.user_id}: {e}")


async def handle_admin_order_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return False
    if not context.user_data.get("admin_ord_state"):
        return False
    state = _state.get(admin_id)
    if not state:
        context.user_data.pop("admin_ord_state", None)
        return False

    text = update.message.text.strip()
    action = state.get("action")

    if action == "search":
        results = search_orders(text)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_ord_state", None)
        if not results:
            await update.message.reply_text("🔍 No orders found.", reply_markup=admin_orders_keyboard())
            return True
        buttons = [[InlineKeyboardButton(
            f"{o.id[:8]} — {o.product_name[:20]} | {o.status}",
            callback_data=f"admin_ord:view:{o.id}"
        )] for o in results[:10]]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:orders")])
        await update.message.reply_text(
            f"🔍 Found {len(results)} result(s):",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return True

    if action == "complete":
        oid = state.get("order_id")
        delivery = "" if text.lower() == "skip" else text
        order = complete_order(oid, delivery_data=delivery)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_ord_state", None)
        log_admin_action(admin_id, "order_complete", oid)
        if order:
            await _notify_user_order_update(context, order)
        await update.message.reply_text("✅ Order marked as completed\\.", parse_mode="MarkdownV2")
        return True

    return False
