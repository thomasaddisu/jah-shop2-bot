"""
Admin Promo Codes Handler
"""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_promos_keyboard, admin_promo_actions_keyboard
from services.promo_service import (
    get_all_promo_codes, get_promo_by_id, create_promo_code,
    update_promo_code, delete_promo_code, disable_promo_code,
)
from utils.formatting import escape_md, fmt_date, paginate
from utils.validators import validate_promo_code, validate_discount, validate_date
from utils.logger import log_admin_action
from config import ADMIN_IDS, PAGE_SIZE

logger = logging.getLogger("jah_shop.handlers.admin_promos")
_state: dict[int, dict] = {}


async def admin_promos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    data = query.data

    if data == "admin:promos":
        await query.edit_message_text(
            "🎟 *Promo Code Management*", parse_mode="MarkdownV2",
            reply_markup=admin_promos_keyboard()
        )

    elif data == "admin_promo:create":
        _state[admin_id] = {"action": "create", "step": "code"}
        context.user_data["admin_promo_state"] = True
        await query.edit_message_text("➕ *Create Promo Code*\n\nStep 1/5 — Enter promo *code*:", parse_mode="MarkdownV2")

    elif data.startswith("admin_promo:list:"):
        page = int(data.split(":")[2])
        await _list_promos(query, page)

    elif data.startswith("admin_promo:view:"):
        pid = data.split(":")[2]
        await _view_promo(query, pid)

    elif data.startswith("admin_promo:enable:"):
        pid = data.split(":")[2]
        update_promo_code(pid, {"active": True})
        log_admin_action(admin_id, "enable_promo", pid)
        await _view_promo(query, pid)

    elif data.startswith("admin_promo:disable:"):
        pid = data.split(":")[2]
        disable_promo_code(pid)
        log_admin_action(admin_id, "disable_promo", pid)
        await _view_promo(query, pid)

    elif data.startswith("admin_promo:delete:"):
        pid = data.split(":")[2]
        delete_promo_code(pid)
        log_admin_action(admin_id, "delete_promo", pid)
        await query.edit_message_text("✅ Promo code deleted\\.", parse_mode="MarkdownV2", reply_markup=admin_promos_keyboard())

    elif data.startswith("admin_promo:edit:"):
        pid = data.split(":")[2]
        p = get_promo_by_id(pid)
        if not p:
            return
        _state[admin_id] = {"action": "edit", "promo_id": pid, "step": "field"}
        context.user_data["admin_promo_state"] = True
        await query.edit_message_text(
            "✏️ What to edit?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Discount Value", callback_data=f"admin_promo:edit_val:{pid}")],
                [InlineKeyboardButton("📅 Expiry Date", callback_data=f"admin_promo:edit_exp:{pid}")],
                [InlineKeyboardButton("🔢 Max Uses", callback_data=f"admin_promo:edit_uses:{pid}")],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"admin_promo:view:{pid}")],
            ])
        )

    elif data.startswith("admin_promo:edit_val:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "edit_val", "promo_id": pid}
        context.user_data["admin_promo_state"] = True
        await query.edit_message_text("Enter new discount value:")

    elif data.startswith("admin_promo:edit_exp:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "edit_exp", "promo_id": pid}
        context.user_data["admin_promo_state"] = True
        await query.edit_message_text("Enter new expiry date \\(YYYY\\-MM\\-DD\\):", parse_mode="MarkdownV2")

    elif data.startswith("admin_promo:edit_uses:"):
        pid = data.split(":")[2]
        _state[admin_id] = {"action": "edit_uses", "promo_id": pid}
        context.user_data["admin_promo_state"] = True
        await query.edit_message_text("Enter new max uses \\(0 = unlimited\\):", parse_mode="MarkdownV2")

    # Discount type selection during create
    elif data.startswith("admin_promo:type:"):
        dtype = data.split(":")[2]
        state = _state.get(admin_id, {})
        if state.get("action") == "create":
            state["discount_type"] = dtype
            state["step"] = "discount_value"
            await query.edit_message_text(
                f"Step 3/5 — Enter *discount value*\n"
                f"{'\\(percentage\\, e\\.g\\. `10` = 10%\\)' if dtype == 'percentage' else '\\(flat amount\\, e\\.g\\. `5`\\)'}",
                parse_mode="MarkdownV2",
            )


async def _list_promos(query, page: int) -> None:
    promos = get_all_promo_codes()
    page_items, total_pages, current_page = paginate(promos, page, PAGE_SIZE)

    if not promos:
        await query.edit_message_text("🎟 No promo codes found.", reply_markup=admin_promos_keyboard())
        return

    buttons = []
    for p in page_items:
        icon = "🟢" if p.active else "🔴"
        discount = f"{p.discount_value}%" if p.discount_type == "percentage" else f"${p.discount_value:.2f}"
        buttons.append([InlineKeyboardButton(
            f"{icon} {p.code} — {discount} ({p.uses}/{p.max_uses if p.max_uses else '∞'})",
            callback_data=f"admin_promo:view:{p.id}"
        )])

    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin_promo:list:{current_page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin_promo:list:{current_page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:promos")])

    await query.edit_message_text(
        f"🎟 *Promo Codes* \\({len(promos)} total\\)",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _view_promo(query, pid: str) -> None:
    p = get_promo_by_id(pid)
    if not p:
        await query.edit_message_text("❌ Not found.", reply_markup=admin_promos_keyboard())
        return
    discount = f"{p.discount_value}%" if p.discount_type == "percentage" else f"${p.discount_value:.2f}"
    status = "🟢 Active" if p.active else "🔴 Inactive"
    expires = escape_md(p.expires_at[:10]) if p.expires_at else "Never"
    text = (
        f"🎟 *Promo Code: `{escape_md(p.code)}`*\n\n"
        f"💸 Discount: `{escape_md(discount)}`\n"
        f"📦 Min Order: `${p.min_order_amount:.2f}`\n"
        f"🔢 Uses: `{p.uses}`/`{p.max_uses if p.max_uses else '∞'}`\n"
        f"📅 Expires: {expires}\n"
        f"Status: {status}\n"
        f"🆔 `{escape_md(p.id)}`"
    )
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=admin_promo_actions_keyboard(pid, p.active))


async def handle_admin_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return False
    if not context.user_data.get("admin_promo_state"):
        return False
    state = _state.get(admin_id)
    if not state:
        context.user_data.pop("admin_promo_state", None)
        return False

    text = update.message.text.strip()
    action = state.get("action")

    if action in ("edit_val", "edit_exp", "edit_uses"):
        pid = state.get("promo_id")
        p = get_promo_by_id(pid)
        if action == "edit_val" and p:
            valid, val, err = validate_discount(text, p.discount_type)
            if not valid:
                await update.message.reply_text(err)
                return True
            update_promo_code(pid, {"discount_value": val})
        elif action == "edit_exp":
            valid, date_str, err = validate_date(text)
            if not valid:
                await update.message.reply_text(err)
                return True
            update_promo_code(pid, {"expires_at": date_str})
        elif action == "edit_uses":
            try:
                uses = int(text)
                update_promo_code(pid, {"max_uses": max(0, uses)})
            except ValueError:
                await update.message.reply_text("❌ Enter a whole number.")
                return True
        _state.pop(admin_id, None)
        context.user_data.pop("admin_promo_state", None)
        log_admin_action(admin_id, f"edit_promo_{action}", pid)
        await update.message.reply_text("✅ Promo code updated\\.", parse_mode="MarkdownV2")
        return True

    # Multi-step create flow
    if action == "create":
        return await _handle_create_step(update, context, admin_id, state, text)

    return False


async def _handle_create_step(update, context, admin_id, state, text):
    step = state.get("step")

    if step == "code":
        valid, code, err = validate_promo_code(text)
        if not valid:
            await update.message.reply_text(err)
            return True
        state["code"] = code
        state["step"] = "discount_type"
        await update.message.reply_text(
            "Step 2/5 — Select *discount type*:", parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Percentage", callback_data="admin_promo:type:percentage")],
                [InlineKeyboardButton("💵 Flat Amount", callback_data="admin_promo:type:flat")],
            ])
        )

    elif step == "discount_value":
        dtype = state.get("discount_type", "percentage")
        valid, val, err = validate_discount(text, dtype)
        if not valid:
            await update.message.reply_text(err)
            return True
        state["discount_value"] = val
        state["step"] = "max_uses"
        await update.message.reply_text("Step 4/5 — Enter *max uses* \\(0 = unlimited\\):", parse_mode="MarkdownV2")

    elif step == "max_uses":
        try:
            uses = int(text)
            state["max_uses"] = max(0, uses)
        except ValueError:
            await update.message.reply_text("❌ Enter a whole number.")
            return True
        state["step"] = "expires_at"
        await update.message.reply_text("Step 5/5 — Enter *expiry date* \\(YYYY\\-MM\\-DD\\) or `none`:", parse_mode="MarkdownV2")

    elif step == "expires_at":
        if text.lower() == "none":
            state["expires_at"] = ""
        else:
            valid, date_str, err = validate_date(text)
            if not valid:
                await update.message.reply_text(err)
                return True
            state["expires_at"] = date_str
        promo = create_promo_code(state)
        _state.pop(admin_id, None)
        context.user_data.pop("admin_promo_state", None)
        log_admin_action(admin_id, "create_promo", promo.id)
        await update.message.reply_text(
            f"✅ *Promo Code Created\\!*\n🎟 `{escape_md(promo.code)}`",
            parse_mode="MarkdownV2",
            reply_markup=admin_promos_keyboard(),
        )
    return True
