"""
Jah Shop Bot — Main Entry Point
"""

from __future__ import annotations

import logging
import sys

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)

import config  # loads .env and sets up logging

logger = logging.getLogger("jah_shop.bot")


def build_application() -> Application:
    app = Application.builder().token(config.BOT_TOKEN).build()

    # ── Command Handlers ──────────────────────────────────────
    from handlers.start import start_handler
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("menu", start_handler))
    app.add_handler(CommandHandler("admin", _admin_cmd))

    # ── Callback Query Router ─────────────────────────────────
    app.add_handler(CallbackQueryHandler(_callback_router))

    # ── Message Router (text + media) ─────────────────────────
    from handlers.router import message_router
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND | filters.PHOTO | filters.Document.ALL | filters.VIDEO,
        message_router,
    ))

    # ── Error Handler ─────────────────────────────────────────
    app.add_error_handler(_error_handler)

    return app


async def _admin_cmd(update: Update, context) -> None:
    from handlers.admin import admin_panel_handler
    await admin_panel_handler(update, context)


async def _callback_router(update: Update, context) -> None:
    """Route all callback queries to appropriate handlers."""
    query = update.callback_query
    if not query:
        return
    data = query.data or ""

    try:
        if data.startswith("cat:") or data.startswith("product:") or data.startswith("buy") \
                or data.startswith("products_page:") or data.startswith("shop:") or data == "home" or data == "noop":
            from handlers.shop import shop_callback_handler
            await shop_callback_handler(update, context)

        elif data.startswith("wallet:") or data.startswith("topup_method:") or data.startswith("txn_page:"):
            from handlers.wallet import wallet_callback_handler
            await wallet_callback_handler(update, context)

        elif data.startswith("orders:"):
            from handlers.orders import orders_callback_handler
            await orders_callback_handler(update, context)

        elif data.startswith("support:"):
            from handlers.support import support_callback_handler
            await support_callback_handler(update, context)

        elif data.startswith("admin_sup:"):
            from handlers.support import admin_support_callback
            await admin_support_callback(update, context)

        elif data.startswith("admin_prod:set_delivery:"):
            from handlers.admin_products import admin_products_callback
            await admin_products_callback(update, context)

        elif data.startswith("admin_promo:type:"):
            from handlers.admin_promos import admin_promos_callback
            await admin_promos_callback(update, context)

        elif data.startswith("admin"):
            from handlers.admin import admin_callback_handler
            await admin_callback_handler(update, context)

        elif data.startswith("admin_log_export:"):
            from handlers.admin_logs import admin_log_export_callback
            await admin_log_export_callback(update, context)

        elif data == "back":
            from handlers.start import start_handler
            await query.answer()
            if query.message:
                await query.message.delete()
        else:
            await query.answer()

    except Exception as e:
        logger.error(f"Callback error for data={data!r}: {e}", exc_info=True)
        from utils.logger import log_error
        log_error(f"callback:{data}", str(e))
        try:
            await query.answer("⚠️ An error occurred. Please try again.", show_alert=True)
        except Exception:
            pass


async def _error_handler(update: object, context) -> None:
    from utils.logger import log_error
    error_msg = str(context.error)
    logger.error(f"Unhandled exception: {error_msg}", exc_info=context.error)
    log_error("unhandled_exception", error_msg)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An unexpected error occurred. Our team has been notified."
            )
        except Exception:
            pass


def main() -> None:
    logger.info("=" * 50)
    logger.info("  Jah Shop Bot Starting Up")
    logger.info(f"  Version: {config.VERSION}")
    logger.info(f"  Admins: {config.ADMIN_IDS}")
    logger.info("=" * 50)

    app = build_application()

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
