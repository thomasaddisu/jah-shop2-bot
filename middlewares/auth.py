"""
Auth Middleware — Admin authorization and ban checking.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from services.user_service import is_banned, upsert_user
from utils.rate_limiter import is_rate_limited

logger = logging.getLogger("jah_shop.auth")


def require_admin(func: Callable) -> Callable:
    """Decorator: only allow admin users."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user or user.id not in ADMIN_IDS:
            if update.message:
                await update.message.reply_text("⛔ Access denied. Admins only.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Access denied.", show_alert=True)
            logger.warning(f"Unauthorized access attempt by user {user.id if user else 'unknown'}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def check_banned(func: Callable) -> Callable:
    """Decorator: block banned users."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user and is_banned(user.id):
            if update.message:
                await update.message.reply_text(
                    "🚫 Your account has been suspended. Contact support for assistance."
                )
            elif update.callback_query:
                await update.callback_query.answer("🚫 Account suspended.", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def rate_limit(func: Callable) -> Callable:
    """Decorator: rate limit users."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user and user.id not in ADMIN_IDS and is_rate_limited(user.id):
            if update.message:
                await update.message.reply_text(
                    "⚠️ You're sending messages too quickly. Please slow down."
                )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def register_user(func: Callable) -> Callable:
    """Decorator: register/update user on every interaction."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        tg_user = update.effective_user
        if tg_user:
            try:
                upsert_user(tg_user)
            except Exception as e:
                logger.error(f"Failed to register user {tg_user.id}: {e}")
        return await func(update, context, *args, **kwargs)
    return wrapper
