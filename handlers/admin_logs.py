"""
Admin Logs Handler
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_logs_keyboard
from utils.logger import read_log_file, export_log
from utils.formatting import escape_md
from utils.logger import log_admin_action
from config import ADMIN_IDS

logger = logging.getLogger("jah_shop.handlers.admin_logs")


async def admin_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    data = query.data

    if data == "admin:logs":
        await query.edit_message_text(
            "📝 *Logs*\n\nSelect log category:",
            parse_mode="MarkdownV2",
            reply_markup=admin_logs_keyboard(),
        )
        return

    if not data.startswith("admin_log:"):
        return

    category = data.split(":", 1)[1]
    log_admin_action(admin_id, "view_logs", category)

    entries = read_log_file(category, lines=20)
    if not entries:
        from keyboards.menus import back_button
        await query.edit_message_text(
            f"📝 *{escape_md(category.replace('_', ' ').title())}*\n\n_No log entries yet\\._",
            parse_mode="MarkdownV2",
            reply_markup=admin_logs_keyboard(),
        )
        return

    lines = [f"📝 *{escape_md(category.replace('_', ' ').title())}* \\(last {len(entries)}\\)\n"]
    for entry in entries[-10:]:
        ts = escape_md(entry.get("ts", "")[:16].replace("T", " "))
        # Format based on category
        if "user_id" in entry:
            detail = f"`{entry.get('user_id')}` — {escape_md(str(entry.get('action', entry.get('operation', ''))))[:50]}"
        elif "error" in entry:
            detail = f"❌ {escape_md(str(entry.get('error', ''))[:60])}"
        elif "order_id" in entry:
            detail = f"`{escape_md(str(entry.get('order_id', ''))[:8])}` {escape_md(str(entry.get('status', '')))}"
        else:
            detail = escape_md(str(list(entry.values())[-1])[:60])
        lines.append(f"• `{ts}` {detail}")

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    export_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Export Full Log", callback_data=f"admin_log_export:{category}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:logs")],
    ])

    await query.edit_message_text(
        "\n".join(lines), parse_mode="MarkdownV2", reply_markup=export_kb,
    )


async def admin_log_export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return
    category = query.data.split(":", 1)[1]
    log_file = export_log(category)
    if log_file:
        with open(log_file, "rb") as f:
            await context.bot.send_document(
                chat_id=admin_id,
                document=f,
                filename=f"{category}.log",
                caption=f"📥 Export: {category}",
            )
    else:
        await query.answer("No log file found.", show_alert=True)
