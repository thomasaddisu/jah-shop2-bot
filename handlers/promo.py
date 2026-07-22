"""
Promo Code Handler — Apply promo codes.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards.menus import main_menu_keyboard, back_button
from middlewares.auth import check_banned, register_user, rate_limit
from services.promo_service import validate_promo_code, get_promo_code
from utils.formatting import escape_md
from utils.logger import log_user_action

logger = logging.getLogger("jah_shop.handlers.promo")


@register_user
@check_banned
@rate_limit
async def promo_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    log_user_action(user.id, "promo_menu")
    context.user_data["awaiting_promo_check"] = True

    await update.message.reply_text(
        "🎁 *Promo Codes*\n\n"
        "Enter your promo code to check its validity and see the discount:\n\n"
        "_Promo codes can be applied during checkout\\._",
        parse_mode="MarkdownV2",
    )


async def handle_promo_check_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check promo code validity. Returns True if handled."""
    if not context.user_data.get("awaiting_promo_check"):
        return False

    user_id = update.effective_user.id
    code = update.message.text.strip()
    context.user_data.pop("awaiting_promo_check", None)

    promo = get_promo_code(code)
    if not promo:
        await update.message.reply_text(
            "❌ *Promo code not found\\.*\n\n"
            "_Make sure you entered the code correctly\\._",
            parse_mode="MarkdownV2",
        )
        return True

    if not promo.active:
        await update.message.reply_text(
            f"❌ *Code `{escape_md(promo.code)}` is no longer active\\.*",
            parse_mode="MarkdownV2",
        )
        return True

    # Check if already used
    already_used = user_id in promo.used_by
    uses_left = (promo.max_uses - promo.uses) if promo.max_uses > 0 else "∞"

    discount_text = (
        f"`{promo.discount_value}%` off"
        if promo.discount_type == "percentage"
        else f"`${promo.discount_value:.2f}` off"
    )

    expires_text = escape_md(promo.expires_at[:10]) if promo.expires_at else "Never"
    min_text = f"`${promo.min_order_amount:.2f}`" if promo.min_order_amount else "None"

    status_icon = "⚠️ Already Used" if already_used else "✅ Valid"
    text = (
        f"🎟 *Promo Code: `{escape_md(promo.code)}`*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💸 *Discount:* {discount_text}\n"
        f"📦 *Min Order:* {min_text}\n"
        f"🔢 *Uses Left:* {uses_left}\n"
        f"📅 *Expires:* {expires_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Status:* {status_icon}"
    )

    await update.message.reply_text(text, parse_mode="MarkdownV2")
    return True
