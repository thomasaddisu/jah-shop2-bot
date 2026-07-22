"""
Admin Keyboards — Admin panel inline keyboards.
"""

from __future__ import annotations

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="admin:dashboard"),
            InlineKeyboardButton("🛒 Products", callback_data="admin:products"),
        ],
        [
            InlineKeyboardButton("📦 Orders", callback_data="admin:orders"),
            InlineKeyboardButton("👥 Users", callback_data="admin:users"),
        ],
        [
            InlineKeyboardButton("💳 Wallet Requests", callback_data="admin:wallet_requests"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast"),
        ],
        [
            InlineKeyboardButton("🎟 Promo Codes", callback_data="admin:promos"),
            InlineKeyboardButton("📈 Statistics", callback_data="admin:stats"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="admin:settings"),
            InlineKeyboardButton("📝 Logs", callback_data="admin:logs"),
        ],
    ])


def admin_products_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Product", callback_data="admin_prod:add")],
        [InlineKeyboardButton("🔍 Search Product", callback_data="admin_prod:search")],
        [InlineKeyboardButton("📋 List All", callback_data="admin_prod:list:0")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:menu")],
    ])


def admin_product_actions_keyboard(product_id: str, is_available: bool) -> InlineKeyboardMarkup:
    toggle_label = "🔴 Disable" if is_available else "🟢 Enable"
    toggle_data = f"admin_prod:disable:{product_id}" if is_available else f"admin_prod:enable:{product_id}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"admin_prod:edit:{product_id}"),
            InlineKeyboardButton(toggle_label, callback_data=toggle_data),
        ],
        [
            InlineKeyboardButton("📦 Update Stock", callback_data=f"admin_prod:stock:{product_id}"),
            InlineKeyboardButton("🖼 Upload Image", callback_data=f"admin_prod:image:{product_id}"),
        ],
        [
            InlineKeyboardButton("🗑 Delete", callback_data=f"admin_prod:delete_confirm:{product_id}"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_prod:list:0")],
    ])


def admin_product_edit_keyboard(product_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Name", callback_data=f"admin_prod:edit_name:{product_id}")],
        [InlineKeyboardButton("📋 Description", callback_data=f"admin_prod:edit_desc:{product_id}")],
        [InlineKeyboardButton("💰 Price", callback_data=f"admin_prod:edit_price:{product_id}")],
        [InlineKeyboardButton("⏱ Duration", callback_data=f"admin_prod:edit_duration:{product_id}")],
        [InlineKeyboardButton("🏷 Category", callback_data=f"admin_prod:edit_category:{product_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"admin_prod:view:{product_id}")],
    ])


def admin_orders_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ Pending", callback_data=f"admin_ord:list:pending:0")],
        [InlineKeyboardButton("🔄 Processing", callback_data=f"admin_ord:list:processing:0")],
        [InlineKeyboardButton("✅ Completed", callback_data=f"admin_ord:list:completed:0")],
        [InlineKeyboardButton("❌ Cancelled", callback_data=f"admin_ord:list:cancelled:0")],
        [InlineKeyboardButton("🔍 Search", callback_data="admin_ord:search")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:menu")],
    ])


def admin_order_actions_keyboard(order_id: str, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == "pending":
        buttons.append([
            InlineKeyboardButton("✅ Complete", callback_data=f"admin_ord:complete:{order_id}"),
            InlineKeyboardButton("🔄 Processing", callback_data=f"admin_ord:processing:{order_id}"),
        ])
        buttons.append([
            InlineKeyboardButton("❌ Cancel", callback_data=f"admin_ord:cancel:{order_id}"),
        ])
    elif status == "processing":
        buttons.append([
            InlineKeyboardButton("✅ Complete", callback_data=f"admin_ord:complete:{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"admin_ord:cancel:{order_id}"),
        ])
    elif status == "completed":
        buttons.append([
            InlineKeyboardButton("↩️ Refund", callback_data=f"admin_ord:refund:{order_id}"),
        ])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_ord:list:all:0")])
    return InlineKeyboardMarkup(buttons)


def admin_users_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search User", callback_data="admin_usr:search")],
        [InlineKeyboardButton("📋 List All", callback_data="admin_usr:list:0")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:menu")],
    ])


def admin_user_actions_keyboard(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_label = "✅ Unban" if is_banned else "🚫 Ban"
    ban_data = f"admin_usr:unban:{user_id}" if is_banned else f"admin_usr:ban:{user_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ban_label, callback_data=ban_data)],
        [InlineKeyboardButton("💰 Edit Wallet", callback_data=f"admin_usr:edit_wallet:{user_id}")],
        [InlineKeyboardButton("📦 View Orders", callback_data=f"admin_usr:orders:{user_id}")],
        [InlineKeyboardButton("📜 Transactions", callback_data=f"admin_usr:txns:{user_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:users")],
    ])


def admin_wallet_requests_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ Pending", callback_data="admin_wr:list:pending:0")],
        [InlineKeyboardButton("📜 All History", callback_data="admin_wr:list:all:0")],
        [InlineKeyboardButton("🔍 Search", callback_data="admin_wr:search")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:menu")],
    ])


def admin_wallet_request_actions_keyboard(req_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_wr:approve:{req_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_wr:reject:{req_id}"),
        ],
        [InlineKeyboardButton("📝 Add Note", callback_data=f"admin_wr:note:{req_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_wr:list:pending:0")],
    ])


def admin_promos_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Code", callback_data="admin_promo:create")],
        [InlineKeyboardButton("📋 List All", callback_data="admin_promo:list:0")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:menu")],
    ])


def admin_promo_actions_keyboard(promo_id: str, active: bool) -> InlineKeyboardMarkup:
    toggle_label = "🔴 Disable" if active else "🟢 Enable"
    toggle_data = f"admin_promo:disable:{promo_id}" if active else f"admin_promo:enable:{promo_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit", callback_data=f"admin_promo:edit:{promo_id}")],
        [InlineKeyboardButton(toggle_label, callback_data=toggle_data)],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"admin_promo:delete:{promo_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_promo:list:0")],
    ])


def admin_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Bot Name", callback_data="admin_set:bot_name")],
        [InlineKeyboardButton("💱 Currency", callback_data="admin_set:currency")],
        [InlineKeyboardButton("👤 Support Username", callback_data="admin_set:support_username")],
        [InlineKeyboardButton("₮ USDT Address", callback_data="admin_set:usdt_address")],
        [InlineKeyboardButton("🏦 Bank Details", callback_data="admin_set:bank_details")],
        [InlineKeyboardButton("🔧 Maintenance Mode", callback_data="admin_set:maintenance_mode")],
        [InlineKeyboardButton("🔔 Order Notifications", callback_data="admin_set:order_notifications")],
        [InlineKeyboardButton("📢 Admin Notifications", callback_data="admin_set:admin_notifications")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:menu")],
    ])


def admin_logs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 User Activity", callback_data="admin_log:user_activity")],
        [InlineKeyboardButton("🛡 Admin Activity", callback_data="admin_log:admin_activity")],
        [InlineKeyboardButton("📦 Orders", callback_data="admin_log:orders")],
        [InlineKeyboardButton("💳 Wallet", callback_data="admin_log:wallet")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_log:broadcast")],
        [InlineKeyboardButton("💬 Support", callback_data="admin_log:support")],
        [InlineKeyboardButton("❌ Errors", callback_data="admin_log:errors")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:menu")],
    ])


def admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Text Message", callback_data="admin_bc:text")],
        [InlineKeyboardButton("🖼 Image", callback_data="admin_bc:photo")],
        [InlineKeyboardButton("📄 Document", callback_data="admin_bc:document")],
        [InlineKeyboardButton("🎥 Video", callback_data="admin_bc:video")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:menu")],
    ])


def admin_categories_keyboard() -> InlineKeyboardMarkup:
    from config import CATEGORIES
    buttons = []
    for cat_key, cat_name in CATEGORIES.items():
        buttons.append([InlineKeyboardButton(cat_name, callback_data=f"admin_prod:set_cat:{cat_key}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="admin_prod:list:0")])
    return InlineKeyboardMarkup(buttons)
