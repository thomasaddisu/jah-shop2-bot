"""
Admin Wallet Requests Handler
"""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_wallet_requests_keyboard, admin_wallet_request_actions_keyboard
from services.wallet_service import (
    get_all_wallet_requests, get_wallet_request,
    approve_wallet_request, reject_wallet_request,
)
from utils.formatting import escape_md, fmt_date, paginate
from utils.logger import log_admin_action
from config import ADMIN_IDS, PAGE_SIZE, PAYMENT_METHODS

logger = logging.getLogger("jah_shop.handlers.admin_wallet")
_state: dict[int, dict] = {}


async def _safe_edit(
    query,
    text: str,
    parse_mode: str = "MarkdownV2",
    reply_markup=None,
) -> None:
    """Edit the current message safely regardless of whether it is a photo or text message.

    Telegram raises BadRequest if you call edit_message_text on a photo/media message.
    When the message has media (e.g. the screenshot notification sent via send_photo),
    we instead strip the inline keyboard from the caption and send a new text reply.
    """
    msg = query.message
    is_media = bool(msg and (msg.photo or msg.video or msg.document or msg.audio or msg.voice))

    if is_media:
        # Remove the inline keyboard from the photo caption so it's clear the admin acted
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        # Reply with the new text as a fresh message
        await msg.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    else:
        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)


async def admin_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    data = query.data

    if data == "admin:wallet_requests":
        await _safe_edit(
            query, "💳 *Wallet Requests*",
            reply_markup=admin_wallet_requests_keyboard(),
        )

    elif data.startswith("admin_wr:list:"):
        parts = data.split(":")
        filter_type = parts[2]  # "pending" or "all"
        page = int(parts[3])
        await _list_requests(query, filter_type, page)

    elif data.startswith("admin_wr:view:"):
        rid = data.split(":")[2]
        await _view_request(query, rid)

    elif data.startswith("admin_wr:approve:"):
        rid = data.split(":")[2]
        req = approve_wallet_request(rid)
        if req:
            log_admin_action(admin_id, "approve_wallet_request", rid)
            await _notify_user_wallet(context, req.user_id, req.amount, "approved")
        await _view_request(query, rid)

    elif data.startswith("admin_wr:reject:"):
        rid = data.split(":")[2]
        _state[admin_id] = {"action": "reject", "req_id": rid}
        context.user_data["admin_wr_state"] = True
        await _safe_edit(
            query,
            "❌ *Reject Request*\n\nEnter the rejection reason \\(or type `none` to skip\\):",
        )

    elif data.startswith("admin_wr:note:"):
        rid = data.split(":")[2]
        _state[admin_id] = {"action": "note", "req_id": rid}
        context.user_data["admin_wr_state"] = True
        await _safe_edit(query, "📝 Enter your note for this request:")

    elif data == "admin_wr:search":
        _state[admin_id] = {"action": "search"}
        context.user_data["admin_wr_state"] = True
        await _safe_edit(query, "🔍 Enter user ID or request ID:")


async def _list_requests(query, filter_type: str, page: int) -> None:
    all_reqs = get_all_wallet_requests()
    if filter_type == "pending":
        reqs = [r for r in all_reqs if r.status == "pending"]
    else:
        reqs = all_reqs

    reqs.sort(key=lambda r: r.created_at, reverse=True)
    page_items, total_pages, current_page = paginate(reqs, page, PAGE_SIZE)

    if not reqs:
        label = "pending" if filter_type == "pending" else "wallet"
        await _safe_edit(query, f"💳 No {label} requests found.", parse_mode=None, reply_markup=admin_wallet_requests_keyboard())
        return

    buttons = []
    for r in page_items:
        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(r.status, "❓")
        method = PAYMENT_METHODS.get(r.method, r.method)
        buttons.append([InlineKeyboardButton(
            f"{status_icon} ${r.amount:.2f} | {r.user_id} | {method[:10]}",
            callback_data=f"admin_wr:view:{r.id}"
        )])

    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin_wr:list:{filter_type}:{current_page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin_wr:list:{filter_type}:{current_page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:wallet_requests")])

    await _safe_edit(
        query,
        f"💳 *Wallet Requests* \\({len(reqs)} total\\)",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _view_request(query, rid: str) -> None:
    req = get_wallet_request(rid)
    if not req:
        await _safe_edit(query, "❌ Request not found.", parse_mode=None, reply_markup=admin_wallet_requests_keyboard())
        return
    method = PAYMENT_METHODS.get(req.method, req.method)
    status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(req.status, "❓")
    note = f"\n📝 Note: _{escape_md(req.admin_note)}_" if req.admin_note else ""
    screenshot_info = "\n📸 _Screenshot attached below_" if req.screenshot_file_id else "\n📸 _No screenshot provided_"
    text = (
        f"💳 *Wallet Request*\n\n"
        f"🆔 `{escape_md(req.id)}`\n"
        f"👤 User: `{req.user_id}`\n"
        f"💰 Amount: `${req.amount:.2f}`\n"
        f"💳 Method: {escape_md(method)}\n"
        f"Status: {status_icon} {req.status.title()}"
        f"{note}\n"
        f"📅 {escape_md(fmt_date(req.created_at))}"
        f"{screenshot_info}"
    )
    kb = admin_wallet_request_actions_keyboard(rid) if req.status == "pending" else \
        InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_wr:list:all:0")]])

    # If there is a screenshot, send it as a new photo message with action buttons
    if req.screenshot_file_id:
        try:
            # Remove keyboard from whichever message the admin tapped
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await query.message.reply_photo(
                photo=req.screenshot_file_id,
                caption=text,
                parse_mode="MarkdownV2",
                reply_markup=kb,
            )
            return
        except Exception as e:
            logger.warning(f"Could not send screenshot for request {rid}: {e}")

    await _safe_edit(query, text, reply_markup=kb)


async def _notify_user_wallet(context, user_id: int, amount: float, action: str) -> None:
    try:
        msg = (
            f"💳 *Wallet Request {action.title()}*\n\n"
            f"Your top\\-up request of `${amount:.2f}` has been *{escape_md(action)}*\\."
        )
        if action == "approved":
            msg += f"\n\n✅ `${amount:.2f}` has been added to your wallet\\."
        await context.bot.send_message(chat_id=user_id, text=msg, parse_mode="MarkdownV2")
    except Exception as e:
        logger.warning(f"Could not notify user {user_id}: {e}")


async def handle_admin_wallet_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return False
    if not context.user_data.get("admin_wr_state"):
        return False
    state = _state.get(admin_id)
    if not state:
        context.user_data.pop("admin_wr_state", None)
        return False

    text = update.message.text.strip()
    action = state.get("action")

    if action == "reject":
        rid = state.get("req_id")
        note = "" if text.lower() == "none" else text
        req = reject_wallet_request(rid, note)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_wr_state", None)
        log_admin_action(admin_id, "reject_wallet_request", rid)
        if req:
            await _notify_user_wallet(context, req.user_id, req.amount, "rejected")
        await update.message.reply_text("✅ Request rejected\\.", parse_mode="MarkdownV2")
        return True

    if action == "note":
        rid = state.get("req_id")
        from services.wallet_service import get_all_wallet_requests
        data = get_wallet_request(rid)
        if data:
            from services.database import get_db
            from config import WALLETS_FILE
            from datetime import datetime, timezone
            db = get_db(WALLETS_FILE, {"wallets": [], "wallet_requests": []})
            raw = db.read()
            for r in raw.get("wallet_requests", []):
                if r.get("id") == rid:
                    r["admin_note"] = text
                    r["updated_at"] = datetime.now(timezone.utc).isoformat()
            db.write(raw)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_wr_state", None)
        log_admin_action(admin_id, "add_wallet_note", rid)
        await update.message.reply_text("✅ Note added\\.", parse_mode="MarkdownV2")
        return True

    if action == "search":
        all_reqs = get_all_wallet_requests()
        results = [r for r in all_reqs if text in str(r.user_id) or text in r.id]
        _state.pop(admin_id, None)
        context.user_data.pop("admin_wr_state", None)
        if not results:
            await update.message.reply_text("🔍 No requests found.")
            return True
        buttons = [[InlineKeyboardButton(
            f"${r.amount:.2f} | {r.user_id} | {r.status}",
            callback_data=f"admin_wr:view:{r.id}"
        )] for r in results[:10]]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:wallet_requests")])
        await update.message.reply_text(
            f"🔍 Found {len(results)} result(s):",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return True

    return False
