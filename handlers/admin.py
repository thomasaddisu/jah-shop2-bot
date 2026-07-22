"""
Admin Handler — Dashboard and routing.
"""

from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_main_keyboard
from middlewares.auth import require_admin, register_user
from utils.formatting import escape_md
from utils.logger import log_admin_action
from config import ADMIN_IDS

logger = logging.getLogger("jah_shop.handlers.admin")


@register_user
async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Access denied.")
        return
    log_admin_action(user.id, "admin_panel")
    await update.message.reply_text(
        f"⚙️ *Admin Panel*\n\n"
        f"Welcome, {escape_md(user.first_name or 'Admin')}\\!\n"
        f"Select an option:",
        parse_mode="MarkdownV2",
        reply_markup=admin_main_keyboard(),
    )


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await query.answer("⛔ Access denied.", show_alert=True)
        return

    data = query.data

    if data == "admin:menu":
        await query.edit_message_text(
            "⚙️ *Admin Panel*\n\nSelect an option:",
            parse_mode="MarkdownV2",
            reply_markup=admin_main_keyboard(),
        )

    elif data == "admin:dashboard":
        await _show_dashboard(query, user.id)

    elif data == "admin:products" or data.startswith("admin_prod:"):
        from handlers.admin_products import admin_products_callback
        await admin_products_callback(update, context)

    elif data == "admin:orders" or data.startswith("admin_ord:"):
        from handlers.admin_orders import admin_orders_callback
        await admin_orders_callback(update, context)

    elif data == "admin:users" or data.startswith("admin_usr:"):
        from handlers.admin_users import admin_users_callback
        await admin_users_callback(update, context)

    elif data == "admin:wallet_requests" or data.startswith("admin_wr:"):
        from handlers.admin_wallet import admin_wallet_callback
        await admin_wallet_callback(update, context)

    elif data == "admin:broadcast" or data.startswith("admin_bc:"):
        from handlers.admin_broadcast import admin_broadcast_callback
        await admin_broadcast_callback(update, context)

    elif data == "admin:promos" or data.startswith("admin_promo:"):
        from handlers.admin_promos import admin_promos_callback
        await admin_promos_callback(update, context)

    elif data == "admin:stats":
        await _show_stats(query, user.id)

    elif data == "admin:settings" or data.startswith("admin_set:"):
        from handlers.admin_settings import admin_settings_callback
        await admin_settings_callback(update, context)

    elif data == "admin:logs" or data.startswith("admin_log:"):
        from handlers.admin_logs import admin_logs_callback
        await admin_logs_callback(update, context)


async def _show_dashboard(query, admin_id: int) -> None:
    from services.user_service import get_user_count
    from services.product_service import get_product_count, get_available_product_count
    from services.order_service import get_order_count
    from services.wallet_service import get_pending_wallet_requests, get_total_revenue

    total_users = get_user_count()
    total_orders = get_order_count()
    completed = get_order_count("completed")
    pending = get_order_count("pending")
    processing = get_order_count("processing")
    wr_pending = len(get_pending_wallet_requests())
    revenue = get_total_revenue()
    products = get_product_count()
    avail = get_available_product_count()

    log_admin_action(admin_id, "dashboard")
    text = (
        f"📊 *Admin Dashboard*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Total Users:* `{total_users}`\n"
        f"🛒 *Total Orders:* `{total_orders}`\n"
        f"  ✅ Completed: `{completed}`\n"
        f"  ⏳ Pending: `{pending}`\n"
        f"  🔄 Processing: `{processing}`\n"
        f"💳 *Wallet Requests:* `{wr_pending}` pending\n"
        f"💰 *Revenue:* `${revenue:.2f}`\n"
        f"📦 *Products:* `{avail}`/`{products}` available\n"
        f"🤖 *Bot Status:* 🟢 Online\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    from keyboards.admin_kb import admin_main_keyboard
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=admin_main_keyboard())


async def _show_stats(query, admin_id: int) -> None:
    from services.order_service import get_all_orders
    from services.wallet_service import get_total_revenue, get_total_topups
    from services.product_service import get_best_selling_products
    from services.user_service import get_all_users
    from datetime import datetime, timezone, timedelta

    log_admin_action(admin_id, "statistics")
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    all_orders = get_all_orders()

    def sales_in(since: datetime) -> tuple[int, float]:
        count, total = 0, 0.0
        for o in all_orders:
            if o.status == "completed":
                try:
                    dt = datetime.fromisoformat(o.created_at.replace("Z", "+00:00"))
                    if dt >= since:
                        count += 1
                        total += o.final_price
                except Exception:
                    pass
        return count, total

    d_count, d_rev = sales_in(day_ago)
    w_count, w_rev = sales_in(week_ago)
    m_count, m_rev = sales_in(month_ago)

    best = get_best_selling_products(3)
    best_lines = ""
    for i, item in enumerate(best, 1):
        p = item["product"]
        best_lines += f"  {i}\\. {escape_md(p.name)} \\(`{item['sales']}` sales\\)\n"

    text = (
        f"📈 *Statistics*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Daily Sales:* `{d_count}` orders \\(`${d_rev:.2f}`\\)\n"
        f"📅 *Weekly Sales:* `{w_count}` orders \\(`${w_rev:.2f}`\\)\n"
        f"📅 *Monthly Sales:* `{m_count}` orders \\(`${m_rev:.2f}`\\)\n"
        f"💰 *Total Revenue:* `${get_total_revenue():.2f}`\n"
        f"💳 *Total Topups:* `${get_total_topups():.2f}`\n\n"
        f"🏆 *Best Selling Products:*\n{best_lines if best_lines else '  _No data yet_'}"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    from keyboards.admin_kb import admin_main_keyboard
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=admin_main_keyboard())
