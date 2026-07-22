"""
Admin Broadcast Handler
"""
from __future__ import annotations
import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_broadcast_keyboard
from services.user_service import get_all_users
from utils.formatting import escape_md
from utils.logger import log_admin_action, log_broadcast
from config import ADMIN_IDS

logger = logging.getLogger("jah_shop.handlers.admin_broadcast")
_state: dict[int, dict] = {}


async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    data = query.data

    if data == "admin:broadcast":
        await query.edit_message_text(
            "📢 *Broadcast Message*\n\nSelect message type:",
            parse_mode="MarkdownV2",
            reply_markup=admin_broadcast_keyboard(),
        )

    elif data.startswith("admin_bc:"):
        msg_type = data.split(":")[1]
        _state[admin_id] = {"type": msg_type}
        context.user_data["admin_bc_state"] = True
        prompts = {
            "text": "📝 Enter the text message to broadcast:",
            "photo": "🖼 Send the photo to broadcast:",
            "document": "📄 Send the document to broadcast:",
            "video": "🎥 Send the video to broadcast:",
        }
        await query.edit_message_text(prompts.get(msg_type, "Send your content:"))


async def handle_admin_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return False
    if not context.user_data.get("admin_bc_state"):
        return False
    state = _state.get(admin_id)
    if not state:
        context.user_data.pop("admin_bc_state", None)
        return False

    msg_type = state.get("type")
    context.user_data.pop("admin_bc_state", None)
    _state.pop(admin_id, None)

    users = get_all_users()
    active_users = [u for u in users if not u.is_banned]
    total = len(active_users)

    progress_msg = await update.message.reply_text(
        f"📢 *Broadcasting to {total} users\\.\\.\\.*\n\n⏳ Progress: 0/{total}",
        parse_mode="MarkdownV2",
    )

    success, failed = 0, 0

    for i, user in enumerate(active_users):
        try:
            if msg_type == "text" and update.message.text:
                await context.bot.send_message(chat_id=user.user_id, text=update.message.text)
            elif msg_type == "photo" and update.message.photo:
                await context.bot.send_photo(
                    chat_id=user.user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption or "",
                )
            elif msg_type == "document" and update.message.document:
                await context.bot.send_document(
                    chat_id=user.user_id,
                    document=update.message.document.file_id,
                    caption=update.message.caption or "",
                )
            elif msg_type == "video" and update.message.video:
                await context.bot.send_video(
                    chat_id=user.user_id,
                    video=update.message.video.file_id,
                    caption=update.message.caption or "",
                )
            success += 1
        except Exception:
            failed += 1

        # Update progress every 10 users
        if (i + 1) % 10 == 0 or i + 1 == total:
            try:
                await progress_msg.edit_text(
                    f"📢 *Broadcasting\\.\\.\\.*\n\n"
                    f"⏳ Progress: {i+1}/{total}\n"
                    f"✅ Success: {success} | ❌ Failed: {failed}",
                    parse_mode="MarkdownV2",
                )
            except Exception:
                pass

        await asyncio.sleep(0.05)  # Avoid flood limits

    log_broadcast(admin_id, total, success, failed)
    log_admin_action(admin_id, "broadcast", f"total={total}, success={success}, failed={failed}")

    await progress_msg.edit_text(
        f"📢 *Broadcast Complete\\!*\n\n"
        f"👥 Total: `{total}`\n"
        f"✅ Success: `{success}`\n"
        f"❌ Failed: `{failed}`",
        parse_mode="MarkdownV2",
    )
    return True
