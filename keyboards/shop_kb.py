"""
Shop Keyboards — Category, product, and buy-flow inline keyboards.
"""

from __future__ import annotations

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from config import CATEGORIES, PAGE_SIZE
from utils.formatting import paginate


def categories_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    cat_list = list(CATEGORIES.items())
    for i in range(0, len(cat_list), 2):
        row = []
        for cat_key, cat_name in cat_list[i:i+2]:
            row.append(InlineKeyboardButton(cat_name, callback_data=f"cat:{cat_key}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="shop:back")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products: list, page: int = 0) -> InlineKeyboardMarkup:
    page_items, total_pages, current_page = paginate(products, page, PAGE_SIZE)
    buttons = []
    for p in page_items:
        stock_label = f" [{p.stock}]" if p.stock <= 5 else ""
        buttons.append([
            InlineKeyboardButton(
                f"{p.name}{stock_label} — ${p.price:.2f}",
                callback_data=f"product:{p.id}"
            )
        ])

    # Pagination
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"products_page:{current_page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"products_page:{current_page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop:categories")])
    return InlineKeyboardMarkup(buttons)


def product_detail_keyboard(product_id: str, category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy:{product_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"cat:{category}")],
    ])


def buy_confirm_keyboard(product_id: str, promo_applied: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"buy_confirm:{product_id}")],
    ]
    if not promo_applied:
        buttons.append([InlineKeyboardButton("🎟 Apply Promo Code", callback_data=f"buy_promo:{product_id}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"product:{product_id}")])
    return InlineKeyboardMarkup(buttons)


def insufficient_balance_keyboard(product_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Top Up Wallet", callback_data="wallet:topup")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"product:{product_id}")],
    ])
