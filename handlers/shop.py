"""
Shop Handler — Browse categories and products.
"""

from __future__ import annotations

import logging
import os

from telegram import Update, InputFile
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from keyboards.menus import main_menu_keyboard
from keyboards.shop_kb import (
    categories_keyboard, products_keyboard,
    product_detail_keyboard, buy_confirm_keyboard, insufficient_balance_keyboard,
)
from middlewares.auth import check_banned, register_user, rate_limit
from services.product_service import (
    get_products_by_category, get_product, decrement_stock,
)
from services.wallet_service import get_balance, debit_wallet
from services.order_service import create_order
from services.promo_service import validate_promo_code, apply_promo_code, calculate_discount
from services.settings_service import is_maintenance, get_currency
from utils.formatting import escape_md, fmt_price, fmt_date, paginate
from utils.logger import log_user_action, log_order
from config import ADMIN_IDS, CATEGORIES, PAGE_SIZE

logger = logging.getLogger("jah_shop.handlers.shop")

# In-memory pending buy state (user_id → {product_id, promo_code, discount})
_buy_state: dict[int, dict] = {}


@register_user
@check_banned
@rate_limit
async def shop_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text("🔧 Shop is currently under maintenance.")
        return

    log_user_action(user.id, "shop_menu")
    await update.message.reply_chat_action(ChatAction.TYPING)
    await update.message.reply_text(
        "🛍 *Jah Shop — Categories*\n\n Prices are in ETB NOT $ \n\nChoose a category to browse products:",
        parse_mode="MarkdownV2",
        reply_markup=categories_keyboard(),
    )


async def shop_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data == "shop:categories" or data == "shop:back":
        await query.edit_message_text(
            "🛍 *Jah Shop — Categories*\n\nChoose a category to browse products:",
            parse_mode="MarkdownV2",
            reply_markup=categories_keyboard(),
        )

    elif data.startswith("cat:"):
        cat_key = data.split(":", 1)[1]
        await _show_category(query, user.id, cat_key, page=0)

    elif data.startswith("products_page:"):
        page = int(data.split(":")[1])
        # Pull category from context user_data
        cat_key = context.user_data.get("current_category", "other")
        await _show_category(query, user.id, cat_key, page=page)

    elif data.startswith("product:"):
        product_id = data.split(":", 1)[1]
        await _show_product(query, product_id)

    elif data.startswith("buy:"):
        product_id = data.split(":", 1)[1]
        await _initiate_buy(query, context, user.id, product_id)

    elif data.startswith("buy_promo:"):
        product_id = data.split(":", 1)[1]
        context.user_data["awaiting_promo_for"] = product_id
        await query.edit_message_text(
            "🎟 *Apply Promo Code*\n\nEnter your promo code:",
            parse_mode="MarkdownV2",
        )

    elif data.startswith("buy_confirm:"):
        product_id = data.split(":", 1)[1]
        await _execute_purchase(query, context, user.id, product_id)

    elif data == "home":
        await query.message.reply_text(
            "🏠 Home",
            reply_markup=main_menu_keyboard(user.id),
        )

    elif data == "noop":
        pass


async def _show_category(query, user_id: int, cat_key: str, page: int = 0) -> None:
    from telegram.ext import ContextTypes
    cat_name = CATEGORIES.get(cat_key, "Products")
    products = get_products_by_category(cat_key)

    if not products:
        await query.edit_message_text(
            f"😔 No products available in *{escape_md(cat_name)}* right now\\.",
            parse_mode="MarkdownV2",
            reply_markup=categories_keyboard(),
        )
        return

    # Store current category for pagination
    # We'll pass it via context if possible, but for inline we embed it in callback
    text = f"🛍 *{escape_md(cat_name)}*\n\n_{len(products)} product\\(s\\) available_\n\nSelect a product:"
    await query.edit_message_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=products_keyboard(products, page),
    )


async def _show_product(query, product_id: str) -> None:
    product = get_product(product_id)
    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    stock_text = f"🔴 Out of Stock" if product.stock == 0 else (
        f"🟡 Only {product.stock} left\\!" if product.stock <= 5 else f"🟢 In Stock \\({product.stock}\\)"
    )

    text = (
        f"🛒 *{escape_md(product.name)}*\n\n"
        f"📋 *Description:*\n_{escape_md(product.description)}_\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Price:* `${product.price:.2f} {escape_md(product.currency)}`\n"
        f"⏱ *Duration:* {escape_md(product.duration)}\n"
        f"📦 *Stock:* {stock_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    kb = product_detail_keyboard(product_id, product.category)

    if product.image and os.path.exists(product.image):
        try:
            with open(product.image, "rb") as img:
                await query.message.reply_photo(
                    photo=img,
                    caption=text,
                    parse_mode="MarkdownV2",
                    reply_markup=kb,
                )
            await query.message.delete()
            return
        except Exception:
            pass

    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)


async def _initiate_buy(query, context, user_id: int, product_id: str) -> None:
    product = get_product(product_id)
    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    if not product.available or product.stock == 0:
        await query.edit_message_text(
            "❌ *Sorry, this product is currently unavailable\\.*",
            parse_mode="MarkdownV2",
            reply_markup=product_detail_keyboard(product_id, product.category),
        )
        return

    balance = get_balance(user_id)
    pending = _buy_state.get(user_id, {})
    promo_code = pending.get("promo_code", "")
    discount = pending.get("discount", 0.0)
    final_price = max(0.0, round(product.price - discount, 2))

    promo_line = ""
    if promo_code and discount > 0:
        promo_line = (
            f"\n🎟 *Promo:* `{escape_md(promo_code)}`\n"
            f"🏷 *Discount:* \\-`${discount:.2f}`"
        )

    insufficient = balance < final_price

    text = (
        f"🛒 *Order Confirmation*\n\n"
        f"📦 *Product:* {escape_md(product.name)}\n"
        f"💰 *Price:* `${product.price:.2f}`"
        f"{promo_line}\n"
        f"✅ *Total:* `${final_price:.2f}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👛 *Your Balance:* `${balance:.2f}`\n"
    )

    if insufficient:
        needed = final_price - balance
        text += f"⚠️ *Insufficient balance \\(need `${needed:.2f}` more\\)*"
        await query.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            reply_markup=insufficient_balance_keyboard(product_id),
        )
    else:
        text += f"After purchase: `${balance - final_price:.2f}`"
        promo_applied = bool(promo_code and discount > 0)
        await query.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            reply_markup=buy_confirm_keyboard(product_id, promo_applied=promo_applied),
        )

    # Store buy state
    _buy_state[user_id] = {
        "product_id": product_id,
        "promo_code": promo_code,
        "discount": discount,
    }


async def _execute_purchase(query, context, user_id: int, product_id: str) -> None:
    product = get_product(product_id)
    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    # Re-check stock
    if not product.available or product.stock == 0:
        await query.edit_message_text("❌ Product is now out of stock. Please choose another.")
        _buy_state.pop(user_id, None)
        return

    state = _buy_state.get(user_id, {})
    promo_code = state.get("promo_code", "")
    discount = state.get("discount", 0.0)
    final_price = max(0.0, round(product.price - discount, 2))

    balance = get_balance(user_id)
    if balance < final_price:
        await query.edit_message_text(
            "❌ Insufficient balance\\. Please top up your wallet first\\.",
            parse_mode="MarkdownV2",
            reply_markup=insufficient_balance_keyboard(product_id),
        )
        return

    # Deduct wallet
    ok = debit_wallet(
        user_id,
        final_price,
        description=f"Purchase: {product.name}",
    )
    if not ok:
        await query.edit_message_text("❌ Payment failed. Please try again.")
        return

    # Decrement stock
    decrement_stock(product_id)

    # Apply promo
    if promo_code:
        from services.promo_service import get_promo_code
        promo = get_promo_code(promo_code)
        if promo:
            apply_promo_code(promo.id, user_id)

    # Create order
    order = create_order(
        user_id=user_id,
        product_id=product_id,
        product_name=product.name,
        price=product.price,
        currency=product.currency,
        promo_code=promo_code,
        discount=discount,
    )

    # Clear buy state
    _buy_state.pop(user_id, None)
    context.user_data.pop("awaiting_promo_for", None)

    # Log
    log_user_action(user_id, "purchase", f"product={product.name}, order={order.id}")
    log_order(order.id, user_id, product.name, final_price, "pending")

    # Notify admins
    from services.settings_service import get as get_setting
    if get_setting("order_notifications", True):
        await _notify_admins_new_order(context, order, product, user_id)

    # Success message
    await query.edit_message_text(
        f"🎉 *Purchase Successful\\!*\n\n"
        f"📦 *Product:* {escape_md(product.name)}\n"
        f"💰 *Amount Paid:* `${final_price:.2f}`\n"
        f"🆔 *Order ID:* `{escape_md(order.id)}`\n\n"
        f"⏳ Your order is now being processed\\. You'll be notified once it's ready\\.\n\n"
        f"Use *My Orders* to track your purchase\\.",
        parse_mode="MarkdownV2",
    )


async def _notify_admins_new_order(context, order, product, user_id: int) -> None:
    from config import ADMIN_IDS
    from services.user_service import get_user
    from keyboards.admin_kb import admin_order_actions_keyboard

    user_obj = get_user(user_id)
    user_display = escape_md(user_obj.display_name if user_obj else str(user_id))

    msg = (
        f"🛒 *New Order Received\\!*\n\n"
        f"👤 *Customer:* {user_display} \\(`{user_id}`\\)\n"
        f"📦 *Product:* {escape_md(product.name)}\n"
        f"💰 *Amount:* `${order.final_price:.2f}`\n"
        f"🆔 *Order ID:* `{escape_md(order.id)}`\n"
        f"📅 *Date:* {escape_md(fmt_date(order.created_at))}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=msg,
                parse_mode="MarkdownV2",
                reply_markup=admin_order_actions_keyboard(order.id, order.status),
            )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")


async def handle_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Process promo code input during buy flow. Returns True if handled."""
    product_id = context.user_data.get("awaiting_promo_for")
    if not product_id:
        return False

    user_id = update.effective_user.id
    code = update.message.text.strip()

    product = get_product(product_id)
    if not product:
        context.user_data.pop("awaiting_promo_for", None)
        return False

    valid, reason, promo = validate_promo_code(code, user_id, product.price)
    if not valid:
        await update.message.reply_text(reason)
        return True

    discount = calculate_discount(promo, product.price)
    _buy_state[user_id] = {
        "product_id": product_id,
        "promo_code": promo.code,
        "discount": discount,
    }
    context.user_data.pop("awaiting_promo_for", None)

    await update.message.reply_text(
        f"✅ *Promo code applied\\!*\n"
        f"💸 Discount: `${discount:.2f}`\n\n"
        f"Now tap *Buy Now* on the product to confirm\\.",
        parse_mode="MarkdownV2",
    )
    return True
