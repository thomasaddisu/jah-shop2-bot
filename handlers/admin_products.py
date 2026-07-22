"""
Admin Products Handler
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.admin_kb import (
    admin_products_keyboard, admin_product_actions_keyboard,
    admin_product_edit_keyboard, admin_categories_keyboard,
)
from services.product_service import (
    get_all_products, get_product, create_product, update_product,
    delete_product, set_product_available, update_stock, search_products,
    update_product_image,
)
from utils.formatting import escape_md, fmt_date, paginate
from utils.validators import validate_product_price, validate_stock, validate_text_length
from utils.logger import log_admin_action
from config import ADMIN_IDS, PAGE_SIZE, CATEGORIES

logger = logging.getLogger("jah_shop.handlers.admin_products")

# State per admin
_state: dict[int, dict] = {}


async def admin_products_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    data = query.data

    if data == "admin:products":
        await query.edit_message_text(
            "🛒 *Product Management*", parse_mode="MarkdownV2",
            reply_markup=admin_products_keyboard()
        )

    elif data == "admin_prod:add":
        _state[admin_id] = {"action": "add", "step": "name"}
        context.user_data["admin_prod_state"] = True
        await query.edit_message_text(
            "➕ *Add New Product*\n\nStep 1/7 — Enter product *name*:",
            parse_mode="MarkdownV2",
        )

    elif data == "admin_prod:search":
        _state[admin_id] = {"action": "search"}
        context.user_data["admin_prod_state"] = True
        await query.edit_message_text("🔍 Enter product name or keyword to search:")

    elif data.startswith("admin_prod:list:"):
        page = int(data.split(":")[2])
        await _list_products(query, page)

    elif data.startswith("admin_prod:view:"):
        pid = data.split(":")[2]
        await _view_product(query, pid)

    elif data.startswith("admin_prod:delete_confirm:"):
        pid = data.split(":")[2]
        from keyboards.menus import confirm_cancel_keyboard
        await query.edit_message_text(
            f"🗑 Delete this product? This cannot be undone\\.",
            parse_mode="MarkdownV2",
            reply_markup=confirm_cancel_keyboard(
                f"admin_prod:delete:{pid}", f"admin_prod:view:{pid}"
            )
        )

    elif data.startswith("admin_prod:delete:"):
        pid = data.split(":")[2]
        ok = delete_product(pid)
        log_admin_action(admin_id, "delete_product", pid)
        msg = "✅ Product deleted\\." if ok else "❌ Product not found\\."
        await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=admin_products_keyboard())

    elif data.startswith("admin_prod:enable:"):
        pid = data.split(":")[2]
        set_product_available(pid, True)
        log_admin_action(admin_id, "enable_product", pid)
        await _view_product(query, pid)

    elif data.startswith("admin_prod:disable:"):
        pid = data.split(":")[2]
        set_product_available(pid, False)
        log_admin_action(admin_id, "disable_product", pid)
        await _view_product(query, pid)

    elif data.startswith("admin_prod:edit:"):
        pid = data.split(":")[2]
        await query.edit_message_text(
            "✏️ *Edit Product* — What to edit?",
            parse_mode="MarkdownV2",
            reply_markup=admin_product_edit_keyboard(pid),
        )

    elif data.startswith("admin_prod:edit_name:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "edit", "field": "name", "product_id": pid}
        context.user_data["admin_prod_state"] = True
        await query.edit_message_text("✏️ Enter new *name*:", parse_mode="MarkdownV2")

    elif data.startswith("admin_prod:edit_desc:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "edit", "field": "description", "product_id": pid}
        context.user_data["admin_prod_state"] = True
        await query.edit_message_text("✏️ Enter new *description*:", parse_mode="MarkdownV2")

    elif data.startswith("admin_prod:edit_price:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "edit", "field": "price", "product_id": pid}
        context.user_data["admin_prod_state"] = True
        await query.edit_message_text("✏️ Enter new *price* \\(e\\.g\\. `9\\.99`\\):", parse_mode="MarkdownV2")

    elif data.startswith("admin_prod:edit_duration:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "edit", "field": "duration", "product_id": pid}
        context.user_data["admin_prod_state"] = True
        await query.edit_message_text("✏️ Enter new *duration* \\(e\\.g\\. `30 days`\\):", parse_mode="MarkdownV2")

    elif data.startswith("admin_prod:edit_category:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "edit", "field": "category", "product_id": pid}
        context.user_data["admin_prod_state"] = True
        await query.edit_message_text("✏️ Select new *category*:", parse_mode="MarkdownV2", reply_markup=admin_categories_keyboard())

    elif data.startswith("admin_prod:set_cat:"):
        cat = data.split(":")[2]
        state = _state.get(admin_id, {})
        if state.get("action") == "edit" and state.get("field") == "category":
            pid = state.get("product_id")
            update_product(pid, {"category": cat})
            _state.pop(admin_id, None)
            context.user_data.pop("admin_prod_state", None)
            log_admin_action(admin_id, "edit_product_category", f"{pid} → {cat}")
            await _view_product(query, pid)
        elif state.get("action") == "add":
            state["category"] = cat
            state["step"] = "description"
            await query.edit_message_text("Step 3/7 — Enter product *description*:", parse_mode="MarkdownV2")

    elif data.startswith("admin_prod:stock:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "set_stock", "product_id": pid}
        context.user_data["admin_prod_state"] = True
        p = get_product(pid)
        await query.edit_message_text(
            f"📦 Current stock: `{p.stock if p else 0}`\n\nEnter new stock amount:",
            parse_mode="MarkdownV2",
        )

    elif data.startswith("admin_prod:image:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "set_image", "product_id": pid}
        context.user_data["admin_prod_state"] = True
        await query.edit_message_text("🖼 Send the product image (photo):")

    elif data.startswith("admin_prod:set_delivery:"):
        dtype = data.split(":")[2]
        state = _state.get(admin_id, {})
        if state.get("action") == "add":
            state["delivery_type"] = dtype
            state["step"] = "done"
            # Trigger product creation by calling the step handler with a dummy message
            product = create_product(state)
            _state.pop(admin_id, None)
            context.user_data.pop("admin_prod_state", None)
            log_admin_action(admin_id, "create_product", product.id)
            await query.edit_message_text(
                f"✅ *Product Created\\!*\n🆔 `{escape_md(product.id)}`",
                parse_mode="MarkdownV2",
                reply_markup=admin_products_keyboard(),
            )


async def _list_products(query, page: int) -> None:
    products = get_all_products(include_unavailable=True)
    page_items, total_pages, current_page = paginate(products, page, PAGE_SIZE)

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    if not products:
        await query.edit_message_text("📋 No products found.", reply_markup=admin_products_keyboard())
        return

    buttons = []
    for p in page_items:
        status = "🟢" if p.available and p.stock > 0 else "🔴"
        buttons.append([InlineKeyboardButton(
            f"{status} {p.name} — ${p.price:.2f} [{p.stock}]",
            callback_data=f"admin_prod:view:{p.id}"
        )])

    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin_prod:list:{current_page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin_prod:list:{current_page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:products")])

    await query.edit_message_text(
        f"🛒 *All Products* \\({len(products)} total\\)",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _view_product(query, pid: str) -> None:
    p = get_product(pid)
    if not p:
        await query.edit_message_text("❌ Product not found.", reply_markup=admin_products_keyboard())
        return
    cat_name = CATEGORIES.get(p.category, p.category)
    status = "🟢 Available" if p.available else "🔴 Disabled"
    text = (
        f"🛒 *{escape_md(p.name)}*\n\n"
        f"🏷 Category: {escape_md(cat_name)}\n"
        f"💰 Price: `${p.price:.2f}`\n"
        f"⏱ Duration: {escape_md(p.duration)}\n"
        f"📦 Stock: `{p.stock}`\n"
        f"📋 {escape_md(p.description[:200])}\n"
        f"Status: {status}\n"
        f"🆔 `{escape_md(p.id)}`"
    )
    await query.edit_message_text(
        text, parse_mode="MarkdownV2",
        reply_markup=admin_product_actions_keyboard(pid, p.available),
    )


async def handle_admin_product_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle text/photo input for product management. Returns True if handled."""
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return False
    if not context.user_data.get("admin_prod_state"):
        return False

    state = _state.get(admin_id)
    if not state:
        context.user_data.pop("admin_prod_state", None)
        return False

    action = state.get("action")

    # Handle photo upload
    if update.message.photo and action == "set_image":
        pid = state.get("product_id")
        import os
        from config import IMAGES_DIR
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_path = str(IMAGES_DIR / f"{pid}.jpg")
        await file.download_to_drive(img_path)
        update_product_image(pid, img_path)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_prod_state", None)
        log_admin_action(admin_id, "upload_product_image", pid)
        await update.message.reply_text("✅ Product image updated!")
        return True

    text = update.message.text.strip() if update.message.text else ""
    if not text:
        return False

    if action == "search":
        results = search_products(text, include_unavailable=True)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_prod_state", None)
        if not results:
            await update.message.reply_text("🔍 No products found.", reply_markup=admin_products_keyboard())
            return True
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = [[InlineKeyboardButton(
            f"{p.name} — ${p.price:.2f}", callback_data=f"admin_prod:view:{p.id}"
        )] for p in results[:10]]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:products")])
        await update.message.reply_text(
            f"🔍 Found {len(results)} result(s):",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return True

    if action == "set_stock":
        valid, stock, err = validate_stock(text)
        if not valid:
            await update.message.reply_text(err)
            return True
        pid = state.get("product_id")
        update_stock(pid, stock)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_prod_state", None)
        log_admin_action(admin_id, "update_stock", f"{pid}={stock}")
        await update.message.reply_text(f"✅ Stock updated to {stock}\\.", parse_mode="MarkdownV2")
        return True

    if action == "edit":
        field = state.get("field")
        pid = state.get("product_id")
        if field == "price":
            valid, price, err = validate_product_price(text)
            if not valid:
                await update.message.reply_text(err)
                return True
            update_product(pid, {"price": price})
        elif field == "name":
            ok, err = validate_text_length(text, 2, 100)
            if not ok:
                await update.message.reply_text(err)
                return True
            update_product(pid, {"name": text})
        elif field == "description":
            ok, err = validate_text_length(text, 5, 1000)
            if not ok:
                await update.message.reply_text(err)
                return True
            update_product(pid, {"description": text})
        elif field == "duration":
            update_product(pid, {"duration": text})
        _state.pop(admin_id, None)
        context.user_data.pop("admin_prod_state", None)
        log_admin_action(admin_id, f"edit_product_{field}", f"{pid}={text[:50]}")
        await update.message.reply_text(f"✅ Product {field} updated\\.", parse_mode="MarkdownV2")
        return True

    if action == "add":
        return await _handle_add_product_step(update, context, admin_id, state, text)

    return False


async def _handle_add_product_step(update, context, admin_id: int, state: dict, text: str) -> bool:
    step = state.get("step")

    if step == "name":
        ok, err = validate_text_length(text, 2, 100)
        if not ok:
            await update.message.reply_text(err)
            return True
        state["name"] = text
        state["step"] = "category"
        await update.message.reply_text(
            "Step 2/7 — Select *category*:", parse_mode="MarkdownV2",
            reply_markup=admin_categories_keyboard()
        )

    elif step == "description":
        ok, err = validate_text_length(text, 5, 1000)
        if not ok:
            await update.message.reply_text(err)
            return True
        state["description"] = text
        state["step"] = "price"
        await update.message.reply_text("Step 4/7 — Enter *price* \\(e\\.g\\. `9\\.99`\\):", parse_mode="MarkdownV2")

    elif step == "price":
        valid, price, err = validate_product_price(text)
        if not valid:
            await update.message.reply_text(err)
            return True
        state["price"] = price
        state["step"] = "duration"
        await update.message.reply_text("Step 5/7 — Enter *duration* \\(e\\.g\\. `30 days`\\):", parse_mode="MarkdownV2")

    elif step == "duration":
        state["duration"] = text
        state["step"] = "stock"
        await update.message.reply_text("Step 6/7 — Enter *stock* amount:", parse_mode="MarkdownV2")

    elif step == "stock":
        valid, stock, err = validate_stock(text)
        if not valid:
            await update.message.reply_text(err)
            return True
        state["stock"] = stock
        state["step"] = "delivery_type"
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        await update.message.reply_text(
            "Step 7/7 — Select *delivery type*:", parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Auto", callback_data="admin_prod:set_delivery:auto")],
                [InlineKeyboardButton("👤 Manual", callback_data="admin_prod:set_delivery:manual")],
            ])
        )

    elif step == "done":
        product = create_product(state)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_prod_state", None)
        log_admin_action(admin_id, "create_product", product.id)
        await update.message.reply_text(
            f"✅ *Product Created\\!*\n🆔 `{escape_md(product.id)}`",
            parse_mode="MarkdownV2",
            reply_markup=admin_products_keyboard(),
        )
    return True
