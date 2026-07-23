"""
Message Router — Routes all incoming text messages to the correct handler.
This is the single MessageHandler that handles all user text input.
"""

from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes
from middlewares.auth import check_banned, register_user, rate_limit
from services.settings_service import is_maintenance
from config import ADMIN_IDS

logger = logging.getLogger("jah_shop.handlers.router")

# Menu button texts → handler mapping
MENU_BUTTONS = {
    "🛍 Shop": "shop",
    "👛 Wallet": "wallet",
    "📦 My Orders": "orders",
    "🎁 Promo Codes": "promo",
    "📞 Support": "support",
    "ℹ️ About": "about",
    "🏠 Home": "home",
    "⚙️ Admin Panel": "admin",
}


@register_user
@check_banned
@rate_limit
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all text messages to the appropriate handler."""
    if not update.message or not update.message.text:
        # Handle photo/document/video messages (could be broadcast input or product image)
        await _handle_media_message(update, context)
        return

    user = update.effective_user
    text = update.message.text.strip()

    # Maintenance check
    if is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text("🔧 Bot is under maintenance. Please try again later.")
        return

    # Check main menu buttons first
    destination = MENU_BUTTONS.get(text)
    if destination:
        await _dispatch_menu(update, context, destination)
        return

    # Check contextual input states — order matters
    # 1. Admin input states (check first so they override user states)
    if user.id in ADMIN_IDS:
        if await _handle_admin_input(update, context):
            return

    # 2. User flow states
    if await _handle_user_input(update, context):
        return

    # Default: unknown input
    from keyboards.menus import main_menu_keyboard
    await update.message.reply_text(
        "❓ I didn't understand that. Please use the menu buttons.",
        reply_markup=main_menu_keyboard(user.id),
    )


async def _dispatch_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, destination: str) -> None:
    if destination == "shop":
        from handlers.shop import shop_menu_handler
        await shop_menu_handler(update, context)
    elif destination == "wallet":
        from handlers.wallet import wallet_menu_handler
        await wallet_menu_handler(update, context)
    elif destination == "orders":
        from handlers.orders import orders_menu_handler
        await orders_menu_handler(update, context)
    elif destination == "promo":
        from handlers.promo import promo_menu_handler
        await promo_menu_handler(update, context)
    elif destination == "support":
        from handlers.support import support_menu_handler
        await support_menu_handler(update, context)
    elif destination == "about":
        from handlers.start import about_handler
        await about_handler(update, context)
    elif destination == "home":
        from handlers.start import home_handler
        await home_handler(update, context)
    elif destination == "admin":
        from handlers.admin import admin_panel_handler
        await admin_panel_handler(update, context)


async def _handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle stateful user input. Returns True if consumed."""
    # Support message
    from handlers.support import handle_support_message_input, handle_admin_support_reply_input
    if await handle_support_message_input(update, context):
        return True
    if await handle_admin_support_reply_input(update, context):
        return True

    # Wallet top-up amount
    from handlers.wallet import handle_topup_amount_input
    if await handle_topup_amount_input(update, context):
        return True

    # Promo code check (standalone)
    from handlers.promo import handle_promo_check_input
    if await handle_promo_check_input(update, context):
        return True

    # Promo code during buy flow
    from handlers.shop import handle_promo_input
    if await handle_promo_input(update, context):
        return True

    return False


async def _handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle admin-specific stateful input. Returns True if consumed."""
    from handlers.admin_products import handle_admin_product_input
    if await handle_admin_product_input(update, context):
        return True

    from handlers.admin_orders import handle_admin_order_input
    if await handle_admin_order_input(update, context):
        return True

    from handlers.admin_users import handle_admin_user_input
    if await handle_admin_user_input(update, context):
        return True

    from handlers.admin_wallet import handle_admin_wallet_input
    if await handle_admin_wallet_input(update, context):
        return True

    from handlers.admin_broadcast import handle_admin_broadcast_input
    if await handle_admin_broadcast_input(update, context):
        return True

    from handlers.admin_promos import handle_admin_promo_input
    if await handle_admin_promo_input(update, context):
        return True

    from handlers.admin_settings import handle_admin_settings_input
    if await handle_admin_settings_input(update, context):
        return True

    return False


async def _handle_media_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo/document/video from any user (screenshot proof or admin broadcast/image)."""
    if not update.message:
        return
    user = update.effective_user
    if not user:
        return

    if user.id in ADMIN_IDS:
        # Try admin product image
        from handlers.admin_products import handle_admin_product_input
        if await handle_admin_product_input(update, context):
            return
        # Try admin broadcast
        from handlers.admin_broadcast import handle_admin_broadcast_input
        if await handle_admin_broadcast_input(update, context):
            return

    # Allow regular users to send their payment screenshot
    from handlers.wallet import handle_topup_screenshot_input
    if await handle_topup_screenshot_input(update, context):
        return
