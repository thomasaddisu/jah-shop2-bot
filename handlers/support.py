"""
Support Handler — User support messaging.
"""

from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from keyboards.menus import main_menu_keyboard
from middlewares.auth import check_banned, register_user, rate_limit
from services.support_service import (
    create_support_message, get_user_messages, reply_to_message,
)
from services.settings_service import get_support_username
from utils.formatting import escape_md, fmt_date
from utils.logger import log_user_action, log_support
from config import ADMIN_IDS

logger = logging.getLogger("jah_shop.handlers.support")

# State: user_id → msg_id (for admin reply tracking)
_reply_state: dict[int, str] = {}


@register_user
@check_banned
@rate_limit
async def support_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    log_user_action(user.id, "support_menu")

    support_username = get_support_username()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Send Message", callback_data="support:send")],
        [InlineKeyboardButton("📜 My Messages", callback_data="support:my_messages")],
    ])

    await update.message.reply_text(
        f"📞 *Support Center*\n\n"
        f"We're here to help\\! Send us a message and we'll get back to you\\.\n\n"
        f"👤 *Support:* @{escape_md(support_username)}\n"
        f"⏰ *Response Time:* Usually within a few hours\n\n"
        f"_Tap the button below to send us a message\\._",
        parse_mode="MarkdownV2",
        reply_markup=kb,
    )


async def support_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data == "support:send":
        context.user_data["awaiting_support_message"] = True
        await query.edit_message_text(
            "📩 *Send Support Message*\n\n"
            "Please type your message below\\.\n"
            "Include as much detail as possible\\.",
            parse_mode="MarkdownV2",
        )

    elif data == "support:my_messages":
        messages = get_user_messages(user.id)
        if not messages:
            from keyboards.menus import back_button
            await query.edit_message_text(
                "📜 *My Support Messages*\n\n_No messages yet\\._",
                parse_mode="MarkdownV2",
                reply_markup=back_button("support:send"),
            )
            return

        lines = ["📜 *My Support Messages*\n"]
        for msg in messages[:5]:
            status_icon = {"open": "📬", "replied": "💬", "closed": "🔒"}.get(msg.status, "❓")
            lines.append(
                f"─────────────────\n"
                f"{status_icon} *{escape_md(msg.status.title())}*\n"
                f"💬 {escape_md(msg.message[:80])}\\.\\.\\.\n"
                f"📅 {escape_md(fmt_date(msg.created_at))}"
            )
            if msg.reply:
                lines.append(f"↩️ *Reply:* _{escape_md(msg.reply[:100])}_")

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="support:back")]
            ]),
        )

    elif data == "support:back":
        await support_menu_handler.__wrapped__(update, context) if hasattr(support_menu_handler, '__wrapped__') else None


async def handle_support_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Process user support message input. Returns True if handled."""
    if not context.user_data.get("awaiting_support_message"):
        return False

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if len(text) < 5:
        await update.message.reply_text("❌ Message too short. Please be more descriptive.")
        return True

    if len(text) > 2000:
        await update.message.reply_text("❌ Message too long (max 2000 characters).")
        return True

    context.user_data.pop("awaiting_support_message", None)
    msg = create_support_message(user_id, text)
    log_support(user_id, msg.id, "created")

    await update.message.reply_text(
        f"✅ *Message Sent\\!*\n\n"
        f"🆔 *Message ID:* `{escape_md(msg.id)}`\n\n"
        f"Our support team will respond as soon as possible\\.",
        parse_mode="MarkdownV2",
    )

    # Notify admins
    from services.user_service import get_user
    user_obj = get_user(user_id)
    user_display = escape_md(user_obj.display_name if user_obj else str(user_id))

    notify_msg = (
        f"📩 *New Support Message\\!*\n\n"
        f"👤 *From:* {user_display} \\(`{user_id}`\\)\n"
        f"🆔 *Msg ID:* `{escape_md(msg.id)}`\n\n"
        f"💬 *Message:*\n_{escape_md(text[:500])}_"
    )

    reply_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Reply", callback_data=f"admin_sup:reply:{msg.id}:{user_id}")]
    ])

    for admin_id in ADMIN_IDS:
        try:
            await update.get_bot().send_message(
                chat_id=admin_id,
                text=notify_msg,
                parse_mode="MarkdownV2",
                reply_markup=reply_kb,
            )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")

    return True


async def handle_admin_support_reply_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Admin replying to a support message. Returns True if handled."""
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return False

    state = context.user_data.get("admin_reply_state")
    if not state:
        return False

    msg_id = state.get("msg_id")
    target_user_id = state.get("user_id")
    reply_text = update.message.text.strip()

    if not reply_text:
        return False

    context.user_data.pop("admin_reply_state", None)

    # Save reply
    result = reply_to_message(msg_id, reply_text, admin_id)
    if not result:
        await update.message.reply_text("❌ Message not found or already replied.")
        return True

    log_support(target_user_id, msg_id, f"replied_by_admin_{admin_id}")

    await update.message.reply_text(
        f"✅ Reply sent to user `{target_user_id}`\\.",
        parse_mode="MarkdownV2",
    )

    # Deliver reply to user
    try:
        await update.get_bot().send_message(
            chat_id=target_user_id,
            text=(
                f"💬 *Support Reply*\n\n"
                f"Your support message has received a reply:\n\n"
                f"_{escape_md(reply_text)}_"
            ),
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.warning(f"Could not deliver reply to user {target_user_id}: {e}")

    return True


async def admin_support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin reply button."""
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id

    if admin_id not in ADMIN_IDS:
        await query.answer("⛔ Admins only.", show_alert=True)
        return

    data = query.data
    if data.startswith("admin_sup:reply:"):
        parts = data.split(":")
        msg_id = parts[2]
        user_id = int(parts[3])
        context.user_data["admin_reply_state"] = {"msg_id": msg_id, "user_id": user_id}
        await query.edit_message_text(
            f"↩️ *Replying to message* `{escape_md(msg_id)}`\n\n"
            f"Type your reply message:",
            parse_mode="MarkdownV2",
        )
