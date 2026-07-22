"""
Admin Settings Handler
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_settings_keyboard
from services.settings_service import get_all, set as set_setting, get as get_setting
from utils.formatting import escape_md
from utils.logger import log_admin_action
from config import ADMIN_IDS

logger = logging.getLogger("jah_shop.handlers.admin_settings")
_state: dict[int, dict] = {}

_SETTING_LABELS = {
    "bot_name": "Bot Name",
    "currency": "Currency",
    "support_username": "Support Username",
    "usdt_address": "USDT Address",
    "bank_details": "Bank Details",
    "maintenance_mode": "Maintenance Mode",
    "order_notifications": "Order Notifications",
    "admin_notifications": "Admin Notifications",
}


async def admin_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    data = query.data

    if data == "admin:settings":
        await _show_settings(query)
        return

    if not data.startswith("admin_set:"):
        return

    key = data.split(":", 1)[1]

    # Toggle boolean settings immediately
    if key in ("maintenance_mode", "order_notifications", "admin_notifications"):
        current = get_setting(key, False)
        set_setting(key, not current)
        log_admin_action(admin_id, f"toggle_{key}", str(not current))
        await _show_settings(query)
        return

    # Text settings — prompt for input
    _state[admin_id] = {"key": key}
    context.user_data["admin_set_state"] = True
    label = _SETTING_LABELS.get(key, key)
    current = get_setting(key, "")
    await query.edit_message_text(
        f"⚙️ *Edit Setting: {escape_md(label)}*\n\n"
        f"Current value: `{escape_md(str(current))}`\n\n"
        f"Enter new value:",
        parse_mode="MarkdownV2",
    )


async def _show_settings(query) -> None:
    s = get_all()
    maintenance = "🔴 ON" if s.get("maintenance_mode") else "🟢 OFF"
    order_notif = "🔔 ON" if s.get("order_notifications", True) else "🔕 OFF"
    admin_notif = "🔔 ON" if s.get("admin_notifications", True) else "🔕 OFF"
    text = (
        f"⚙️ *Bot Settings*\n\n"
        f"🤖 Name: `{escape_md(s.get('bot_name', 'Jah Shop'))}`\n"
        f"💱 Currency: `{escape_md(s.get('currency', 'USD'))}`\n"
        f"👤 Support: @{escape_md(s.get('support_username', ''))}\n"
        f"🔧 Maintenance: {maintenance}\n"
        f"🔔 Order Notif: {order_notif}\n"
        f"📢 Admin Notif: {admin_notif}"
    )
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=admin_settings_keyboard())


async def handle_admin_settings_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return False
    if not context.user_data.get("admin_set_state"):
        return False
    state = _state.get(admin_id)
    if not state:
        context.user_data.pop("admin_set_state", None)
        return False

    key = state.get("key")
    value = update.message.text.strip()
    _state.pop(admin_id, None)
    context.user_data.pop("admin_set_state", None)

    set_setting(key, value)
    log_admin_action(admin_id, f"update_setting_{key}", value[:100])
    label = _SETTING_LABELS.get(key, key)
    await update.message.reply_text(
        f"✅ *{escape_md(label)}* updated\\.",
        parse_mode="MarkdownV2",
    )
    return True
