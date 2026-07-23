"""
Jah Shop Bot — Configuration Module
Loads all environment variables and provides centralized config.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# ─── Bot Credentials ────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

# Admin IDs — comma-separated in .env
_raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [
    int(i.strip()) for i in _raw_admin_ids.split(",") if i.strip().isdigit()
]
if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS is not set or invalid in .env file")

# ─── Bot Metadata ────────────────────────────────────────────
BOT_NAME: str = os.getenv("BOT_NAME", "Jah Shop")
CURRENCY: str = os.getenv("CURRENCY", "USD")
SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "Frank_wedaj")
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
VERSION: str = "1.0.0"

# ─── Payment Details ─────────────────────────────────────────
USDT_ADDRESS: str = os.getenv("USDT_ADDRESS", "")
BANK_DETAILS: str = os.getenv("BANK_DETAILS", "")

# ─── Paths ───────────────────────────────────────────────────
DATA_DIR: Path = BASE_DIR / "data"
LOGS_DIR: Path = BASE_DIR / "logs"
BACKUPS_DIR: Path = BASE_DIR / "backups"
IMAGES_DIR: Path = BASE_DIR / "images"

for _dir in [DATA_DIR, LOGS_DIR, BACKUPS_DIR, IMAGES_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ─── Data Files ──────────────────────────────────────────────
USERS_FILE: Path = DATA_DIR / "users.json"
PRODUCTS_FILE: Path = DATA_DIR / "products.json"
WALLETS_FILE: Path = DATA_DIR / "wallets.json"
ORDERS_FILE: Path = DATA_DIR / "orders.json"
TRANSACTIONS_FILE: Path = DATA_DIR / "transactions.json"
PROMO_CODES_FILE: Path = DATA_DIR / "promo_codes.json"
SETTINGS_FILE: Path = DATA_DIR / "settings.json"
ADMINS_FILE: Path = DATA_DIR / "admins.json"
SUPPORT_MESSAGES_FILE: Path = DATA_DIR / "support_messages.json"

# ─── Pagination ───────────────────────────────────────────────
PAGE_SIZE: int = 5

# ─── Rate Limiting ────────────────────────────────────────────
RATE_LIMIT_MESSAGES: int = 10   # max messages per window
RATE_LIMIT_WINDOW: int = 30     # seconds

# ─── Logging ─────────────────────────────────────────────────
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=LOG_LEVEL,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("jah_shop")

# ─── Product Categories ──────────────────────────────────────
CATEGORIES: dict[str, str] = {
    "ai_tools": "🤖 AI Tools",
    "streaming": "🎬 Streaming",
    "productivity": "💼 Productivity",
    "gaming": "🎮 Gaming",
    "vpn": "🔒 VPN",
    "other": "📦 Other",
}

# ─── Payment Methods ─────────────────────────────────────────
PAYMENT_METHODS: dict[str, str] = {
    # "usdt_bep20": "₮ USDT BEP20",
    "bank_transfer": "🏦 Bank Transfer",
    # "manual": "💵 Manual Payment",
}

# ─── Order Statuses ──────────────────────────────────────────
ORDER_STATUS = {
    "pending": "⏳ Pending",
    "processing": "🔄 Processing",
    "completed": "✅ Completed",
    "cancelled": "❌ Cancelled",
    "refunded": "↩️ Refunded",
}

# ─── Wallet Request Statuses ─────────────────────────────────
WALLET_REQUEST_STATUS = {
    "pending": "⏳ Pending",
    "approved": "✅ Approved",
    "rejected": "❌ Rejected",
}

# ─── About Info ──────────────────────────────────────────────
ABOUT_INFO = {
    "company": "Jah Shop",
    "tagline": "Your premium digital goods marketplace",
    "contact_email": "@frank_wedaj",
    "working_hours": "For now 1-4 at night local time 🌙",
    "terms_url": "https://jahshop.com/terms",
    "privacy_url": "https://jahshop.com/privacy",
    "version": VERSION,
}
