"""
Admin Users Handler
"""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_users_keyboard, admin_user_actions_keyboard
from services.user_service import get_all_users, get_user, ban_user, unban_user, search_users
from services.wallet_service import get_wallet, admin_set_balance, get_user_transactions
from services.order_service import get_user_orders
from utils.formatting import escape_md, fmt_date, paginate
from utils.validators import validate_amount
from utils.logger import log_admin_action
from config import ADMIN_IDS, PAGE_SIZE

logger = logging.getLogger("jah_shop.handlers.admin_users")
_state: dict[int, dict] = {}


async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    data = query.data

    if data == "admin:users":
        await query.edit_message_text(
            "👥 *User Management*", parse_mode="MarkdownV2",
            reply_markup=admin_users_keyboard()
        )

    elif data == "admin_usr:search":
        _state[admin_id] = {"action": "search"}
        context.user_data["admin_usr_state"] = True
        await query.edit_message_text("🔍 Enter username, name or user ID:")

    elif data.startswith("admin_usr:list:"):
        page = int(data.split(":")[2])
        await _list_users(query, page)

    elif data.startswith("admin_usr:view:"):
        uid = int(data.split(":")[2])
        await _view_user(query, uid)

    elif data.startswith("admin_usr:ban:"):
        uid = int(data.split(":")[2])
        ban_user(uid)
        log_admin_action(admin_id, "ban_user", str(uid))
        await _view_user(query, uid)

    elif data.startswith("admin_usr:unban:"):
        uid = int(data.split(":")[2])
        unban_user(uid)
        log_admin_action(admin_id, "unban_user", str(uid))
        await _view_user(query, uid)

    elif data.startswith("admin_usr:edit_wallet:"):
        uid = int(data.split(":")[2])
        wallet = get_wallet(uid)
        _state[admin_id] = {"action": "edit_wallet", "user_id": uid}
        context.user_data["admin_usr_state"] = True
        await query.edit_message_text(
            f"💰 Current balance: `${wallet.balance:.2f}`\n\nEnter new balance amount:",
            parse_mode="MarkdownV2",
        )

    elif data.startswith("admin_usr:orders:"):
        uid = int(data.split(":")[2])
        orders = get_user_orders(uid)
        if not orders:
            await query.edit_message_text(f"📦 No orders for user `{uid}`\\.", parse_mode="MarkdownV2",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"admin_usr:view:{uid}")]]))
            return
        lines = [f"📦 *Orders for user `{uid}`*\n"]
        for o in orders[:8]:
            lines.append(f"• `{escape_md(o.id[:8])}` — {escape_md(o.product_name[:20])} | {o.status} | `${o.final_price:.2f}`")
        await query.edit_message_text(
            "\n".join(lines), parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"admin_usr:view:{uid}")]]),
        )

    elif data.startswith("admin_usr:txns:"):
        uid = int(data.split(":")[2])
        txns = get_user_transactions(uid, limit=8)
        if not txns:
            await query.edit_message_text(f"📜 No transactions for user `{uid}`\\.", parse_mode="MarkdownV2",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"admin_usr:view:{uid}")]]))
            return
        lines = [f"📜 *Transactions for user `{uid}`*\n"]
        for t in txns:
            icon = "📥" if t.type == "credit" else "📤"
            lines.append(f"{icon} `{'+'if t.type=='credit' else '-'}${t.amount:.2f}` — {escape_md(t.description or t.type)}")
        await query.edit_message_text(
            "\n".join(lines), parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"admin_usr:view:{uid}")]]),
        )


async def _list_users(query, page: int) -> None:
    users = get_all_users()
    page_items, total_pages, current_page = paginate(users, page, PAGE_SIZE)

    if not users:
        await query.edit_message_text("👥 No users found.", reply_markup=admin_users_keyboard())
        return

    buttons = []
    for u in page_items:
        ban_icon = "🚫" if u.is_banned else "👤"
        name = (u.username or u.first_name or str(u.user_id))[:20]
        buttons.append([InlineKeyboardButton(
            f"{ban_icon} {name} | {u.user_id}",
            callback_data=f"admin_usr:view:{u.user_id}"
        )])

    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin_usr:list:{current_page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin_usr:list:{current_page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:users")])

    await query.edit_message_text(
        f"👥 *All Users* \\({len(users)} total\\)",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _view_user(query, uid: int) -> None:
    user = get_user(uid)
    if not user:
        await query.edit_message_text("❌ User not found.", reply_markup=admin_users_keyboard())
        return
    wallet = get_wallet(uid)
    ban_status = "🚫 Banned" if user.is_banned else "✅ Active"
    text = (
        f"👤 *User Profile*\n\n"
        f"🆔 ID: `{uid}`\n"
        f"👤 Name: {escape_md(user.display_name)}\n"
        f"📱 Username: @{escape_md(user.username or 'N/A')}\n"
        f"💰 Balance: `${wallet.balance:.2f}`\n"
        f"📥 Deposited: `${wallet.total_deposited:.2f}`\n"
        f"📤 Spent: `${wallet.total_spent:.2f}`\n"
        f"📅 Joined: {escape_md(fmt_date(user.joined_at))}\n"
        f"Status: {ban_status}"
    )
    await query.edit_message_text(
        text, parse_mode="MarkdownV2",
        reply_markup=admin_user_actions_keyboard(uid, user.is_banned),
    )


async def handle_admin_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return False
    if not context.user_data.get("admin_usr_state"):
        return False
    state = _state.get(admin_id)
    if not state:
        context.user_data.pop("admin_usr_state", None)
        return False

    text = update.message.text.strip()
    action = state.get("action")

    if action == "search":
        results = search_users(text)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_usr_state", None)
        if not results:
            await update.message.reply_text("🔍 No users found.", reply_markup=admin_users_keyboard())
            return True
        buttons = [[InlineKeyboardButton(
            f"{'🚫' if u.is_banned else '👤'} {u.display_name[:20]} | {u.user_id}",
            callback_data=f"admin_usr:view:{u.user_id}"
        )] for u in results[:10]]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:users")])
        await update.message.reply_text(
            f"🔍 Found {len(results)} user(s):",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return True

    if action == "edit_wallet":
        uid = state.get("user_id")
        valid, amount, err = validate_amount(text, 0, 1_000_000)
        if not valid:
            await update.message.reply_text(err)
            return True
        admin_set_balance(uid, amount)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_usr_state", None)
        log_admin_action(admin_id, "edit_wallet", f"user={uid} balance={amount}")
        await update.message.reply_text(f"✅ Wallet balance set to `${amount:.2f}`\\.", parse_mode="MarkdownV2")
        return True

    return False
