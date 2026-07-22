"""
Start / Home Handler
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from config import ABOUT_INFO, VERSION
from keyboards.menus import main_menu_keyboard
from middlewares.auth import check_banned, register_user, rate_limit
from services.settings_service import get_welcome_message, is_maintenance, get_bot_name
from utils.formatting import escape_md
from utils.logger import log_user_action

logger = logging.getLogger("jah_shop.handlers.start")


@register_user
@check_banned
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    # Maintenance check (not for admins)
    from config import ADMIN_IDS
    if is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text(
            "🔧 *Jah Shop is currently under maintenance\\.*\n\n"
            "We'll be back shortly\\. Thank you for your patience\\!",
            parse_mode="MarkdownV2",
        )
        return

    log_user_action(user.id, "start")
    bot_name = escape_md(get_bot_name())
    welcome = escape_md(get_welcome_message())
    first = escape_md(user.first_name or "")

    text = (
        f"✨ *Welcome to {bot_name}\\!* ✨\n\n"
        f"Hello {first}\\! 👋\n\n"
        f"{welcome}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛍 *Shop* — Browse our digital products\n"
        f"👛 *Wallet* — Manage your balance\n"
        f"📦 *My Orders* — Track your purchases\n"
        f"🎁 *Promo Codes* — Get discounts\n"
        f"📞 *Support* — Get help anytime\n"
        f"ℹ️ *About* — Learn more about us\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Select an option below to get started\\!"
    )

    await update.message.reply_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=main_menu_keyboard(user.id),
    )


@register_user
@check_banned
async def home_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show home menu."""
    await start_handler(update, context)


@register_user
@check_banned
async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from config import ADMIN_IDS
    if is_maintenance() and update.effective_user.id not in ADMIN_IDS:
        return

    log_user_action(update.effective_user.id, "about")
    info = ABOUT_INFO
    text = (
        f"ℹ️ *About {escape_md(info['company'])}*\n\n"
        f"_{escape_md(info['tagline'])}_\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📧 *Contact:* {escape_md(info['contact_email'])}\n"
        f"⏰ *Working Hours:* {escape_md(info['working_hours'])}\n"
        f"📄 *Terms:* [View Terms]({info['terms_url']})\n"
        f"🔒 *Privacy:* [View Policy]({info['privacy_url']})\n"
        f"🤖 *Bot Version:* `{escape_md(info['version'])}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"_Built with ❤️ by Jah Shop Team_"
    )

    await update.message.reply_text(
        text,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
        reply_markup=main_menu_keyboard(update.effective_user.id),
    )
