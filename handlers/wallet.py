"""
Wallet Handler — Balance display, top-up, transactions.

Top-up flow:
  1. User taps "Top Up" → enters amount
  2. User selects payment method → sees payment instructions
  3. User uploads screenshot/photo of payment receipt
  4. WalletRequest is created; admins are notified with the screenshot
  5. Admin approves or rejects → user is notified
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from keyboards.menus import main_menu_keyboard
from keyboards.wallet_kb import wallet_keyboard, payment_method_keyboard, transactions_keyboard
from middlewares.auth import check_banned, register_user, rate_limit
from services.wallet_service import (
    get_wallet, get_user_transactions, create_wallet_request, has_pending_request,
)
from services.settings_service import get as get_setting, get_usdt_address, get_bank_details
from utils.formatting import escape_md, fmt_date, fmt_price, paginate
from utils.logger import log_user_action, log_wallet
from utils.validators import validate_amount
from config import PAGE_SIZE, ADMIN_IDS, PAYMENT_METHODS

logger = logging.getLogger("jah_shop.handlers.wallet")

# In-memory state per user.
# Stages: "awaiting_method" → "awaiting_screenshot"
_topup_state: dict[int, dict] = {}


# ─── Entry Points ─────────────────────────────────────────────

@register_user
@check_banned
@rate_limit
async def wallet_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    log_user_action(user.id, "wallet_menu")
    await _show_wallet(update.message, user.id)


async def _show_wallet(message, user_id: int) -> None:
    wallet = get_wallet(user_id)
    text = (
        f"👛 *Your Wallet*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Balance:* `${wallet.balance:.2f}`\n"
        f"📥 *Total Deposited:* `${wallet.total_deposited:.2f}`\n"
        f"📤 *Total Spent:* `${wallet.total_spent:.2f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Choose an option below:"
    )
    await message.reply_text(text, parse_mode="MarkdownV2", reply_markup=wallet_keyboard())


# ─── Callback Router ──────────────────────────────────────────

async def wallet_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data == "wallet:menu":
        wallet = get_wallet(user.id)
        text = (
            f"👛 *Your Wallet*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Balance:* `${wallet.balance:.2f}`\n"
            f"📥 *Total Deposited:* `${wallet.total_deposited:.2f}`\n"
            f"📤 *Total Spent:* `${wallet.total_spent:.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=wallet_keyboard())

    elif data == "wallet:topup":
        await _start_topup(query, context, user.id)

    elif data.startswith("topup_method:"):
        method = data.split(":", 1)[1]
        await _handle_payment_method(query, context, user.id, method)

    elif data == "wallet:transactions":
        await _show_transactions(query, user.id, page=0)

    elif data.startswith("txn_page:"):
        page = int(data.split(":")[1])
        await _show_transactions(query, user.id, page=page)


# ─── Top-up Flow ──────────────────────────────────────────────

async def _start_topup(query, context, user_id: int) -> None:
    """Step 1 — Check for pending request, then ask for amount."""
    if has_pending_request(user_id):
        await query.edit_message_text(
            "⚠️ *You already have a pending top\\-up request\\.*\n\n"
            "Please wait for admin approval before submitting another\\.",
            parse_mode="MarkdownV2",
            reply_markup=wallet_keyboard(),
        )
        return

    # Clear any stale state
    _topup_state.pop(user_id, None)
    context.user_data["awaiting_topup_amount"] = True
    context.user_data.pop("awaiting_topup_screenshot", None)

    await query.edit_message_text(
        "➕ *Top Up Wallet*\n\n"
        "Please enter the amount you want to deposit:\n"
        "_\\(minimum: \\$1\\.00, maximum: \\$10\\,000\\.00\\)_\n\n"
        "Example: `50` or `100.50`",
        parse_mode="MarkdownV2",
    )


async def _handle_payment_method(query, context, user_id: int, method: str) -> None:
    """Step 2 — Show payment details and prompt for screenshot."""
    state = _topup_state.get(user_id, {})
    amount = state.get("amount", 0.0)
    if not amount:
        await query.edit_message_text("❌ Session expired\\. Please restart top\\-up\\.", parse_mode="MarkdownV2")
        return

    method_name = PAYMENT_METHODS.get(method, method)

    if method == "usdt_bep20":
        address = get_usdt_address()
        instructions = (
            f"₮ *USDT BEP20 Payment*\n\n"
            f"💰 *Amount:* `${amount:.2f}`\n\n"
            f"📋 *Send exactly to this address:*\n"
            f"`{escape_md(address)}`\n\n"
            f"⚠️ *Important:*\n"
            f"• Use BEP20 \\(Binance Smart Chain\\) network only\n"
            f"• Send the exact amount\n\n"
        )
    elif method == "bank_transfer":
        details = get_bank_details()
        instructions = (
            f"🏦 *Bank Transfer Payment*\n\n"
            f"💰 *Amount:* `${amount:.2f}`\n\n"
            f"📋 *Bank Details:*\n"
            f"`{escape_md(details)}`\n\n"
            f"⚠️ *Include your Telegram ID in the reference:* `{user_id}`\n\n"
        )
    else:
        instructions = (
            f"💵 *Manual Payment*\n\n"
            f"💰 *Amount:* `${amount:.2f}`\n\n"
            f"Please contact support with your payment proof\\.\n\n"
        )

    # Advance state to "awaiting_screenshot"
    _topup_state[user_id] = {
        "amount": amount,
        "method": method,
        "method_name": method_name,
        "stage": "awaiting_screenshot",
    }
    context.user_data.pop("awaiting_topup_amount", None)
    context.user_data.pop("awaiting_topup_method", None)
    context.user_data["awaiting_topup_screenshot"] = True

    await query.edit_message_text(
        instructions
        + "📸 *Upload Your Payment Screenshot*\n\n"
          "After completing the payment, send a *photo* of your transaction "
          "receipt here\\. The admin will review and approve your top\\-up\\.",
        parse_mode="MarkdownV2",
    )


# ─── Transaction History ──────────────────────────────────────

async def _show_transactions(query, user_id: int, page: int = 0) -> None:
    txns = get_user_transactions(user_id, limit=100)

    if not txns:
        from keyboards.menus import back_button
        await query.edit_message_text(
            "📜 *Transaction History*\n\n_No transactions yet\\._",
            parse_mode="MarkdownV2",
            reply_markup=back_button("wallet:menu"),
        )
        return

    page_items, total_pages, current_page = paginate(txns, page, PAGE_SIZE)

    lines = [f"📜 *Transaction History* \\({len(txns)} total\\)\n"]
    for txn in page_items:
        icon = "📥" if txn.type == "credit" else "📤"
        sign = "+" if txn.type == "credit" else "-"
        lines.append(
            f"{icon} `{sign}${txn.amount:.2f}` — {escape_md(txn.description or txn.type)}\n"
            f"   📅 {escape_md(fmt_date(txn.created_at))}"
        )

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="MarkdownV2",
        reply_markup=transactions_keyboard(current_page, total_pages),
    )


# ─── Stateful Input Handlers ──────────────────────────────────

async def handle_topup_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Step 1b — Process the amount the user typed. Returns True if consumed."""
    if not context.user_data.get("awaiting_topup_amount"):
        return False

    user_id = update.effective_user.id
    text = update.message.text.strip()

    min_amount = float(get_setting("min_topup_amount", 1.0))
    max_amount = float(get_setting("max_topup_amount", 10000.0))

    valid, amount, err = validate_amount(text, min_val=min_amount, max_val=max_amount)
    if not valid:
        await update.message.reply_text(err)
        return True

    _topup_state[user_id] = {"amount": amount, "stage": "awaiting_method"}
    context.user_data.pop("awaiting_topup_amount", None)
    context.user_data["awaiting_topup_method"] = True

    await update.message.reply_text(
        f"💰 *Amount:* `${amount:.2f}`\n\n"
        f"Now select your preferred payment method:",
        parse_mode="MarkdownV2",
        reply_markup=payment_method_keyboard(),
    )
    return True


async def handle_topup_screenshot_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Step 3 — User uploads a screenshot/photo as payment proof. Returns True if consumed."""
    if not context.user_data.get("awaiting_topup_screenshot"):
        return False

    user_id = update.effective_user.id
    state = _topup_state.get(user_id, {})
    if state.get("stage") != "awaiting_screenshot":
        return False

    # Accept photo or image document
    photo = None
    if update.message.photo:
        photo = update.message.photo[-1]          # pick highest resolution
    elif (
        update.message.document
        and update.message.document.mime_type
        and update.message.document.mime_type.startswith("image/")
    ):
        photo = update.message.document
    else:
        await update.message.reply_text(
            "📸 Please send your payment screenshot as a *photo* "
            "\\(not as a file/document\\)\\.",
            parse_mode="MarkdownV2",
        )
        return True   # still consumed — we stay in the awaiting_screenshot state

    screenshot_file_id = photo.file_id
    amount: float = state["amount"]
    method: str = state["method"]
    method_name: str = state["method_name"]

    # Create wallet request (screenshot stored for admin view)
    req = create_wallet_request(user_id, amount, method, screenshot_file_id=screenshot_file_id)

    # Clear state
    _topup_state.pop(user_id, None)
    context.user_data.pop("awaiting_topup_screenshot", None)

    log_user_action(user_id, "topup_request", f"amount={amount}, method={method}, req={req.id}")

    from keyboards.menus import back_button
    await update.message.reply_text(
        f"✅ *Top\\-Up Request Submitted\\!*\n\n"
        f"💰 *Amount:* `${amount:.2f}`\n"
        f"💳 *Method:* {escape_md(method_name)}\n"
        f"🆔 *Request ID:* `{escape_md(req.id)}`\n\n"
        f"⏳ Your request is under review\\. You will be notified once the "
        f"admin approves or rejects it\\.",
        parse_mode="MarkdownV2",
        reply_markup=back_button("wallet:menu"),
    )

    # Notify admins with the screenshot photo
    from keyboards.admin_kb import admin_wallet_request_actions_keyboard
    from services.user_service import get_user
    user_obj = get_user(user_id)
    user_display = escape_md(user_obj.display_name if user_obj else str(user_id))

    caption = (
        f"📸 *New Top\\-Up Request \\— Screenshot Attached*\n\n"
        f"👤 *User:* {user_display} \\(`{user_id}`\\)\n"
        f"💰 *Amount:* `${amount:.2f}`\n"
        f"💳 *Method:* {escape_md(method_name)}\n"
        f"🆔 *Request ID:* `{escape_md(req.id)}`\n\n"
        f"Review the screenshot above and approve or reject below\\."
    )

    for admin_id in ADMIN_IDS:
        try:
            await update.message.get_bot().send_photo(
                chat_id=admin_id,
                photo=screenshot_file_id,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=admin_wallet_request_actions_keyboard(req.id),
            )
        except Exception as exc:
            logger.warning(f"Could not notify admin {admin_id}: {exc}")

    return True
