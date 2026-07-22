# 🛍️ Jah Shop Bot

A complete, production-quality Telegram shopping bot built with Python 3.12+ and python-telegram-bot v21.

## Features

### User Features
- 🛍 **Shop** — Browse 6 product categories with inline keyboards and pagination
- 👛 **Wallet** — Balance display, top-up via USDT/Bank/Manual, transaction history
- 📦 **My Orders** — View orders filtered by status (Pending/Processing/Completed/Cancelled)
- 🎁 **Promo Codes** — Enter codes for percentage/flat discounts during checkout
- 📞 **Support** — Send messages to admins, receive replies inside Telegram
- ℹ️ **About** — Company info, contact, terms, and privacy links

### Admin Features
- 📊 **Dashboard** — Real-time stats: users, orders, revenue, wallet requests
- 🛒 **Products** — Full CRUD: add, edit, delete, enable/disable, update stock, upload images
- 📦 **Orders** — View, approve, complete, cancel, refund orders; notify customers
- 👥 **Users** — Search, ban/unban, edit wallet, view orders and transactions
- 💳 **Wallet Requests** — Approve/reject with notes, user notifications
- 📢 **Broadcast** — Send text/photo/document/video to all users with progress tracking
- 🎟 **Promo Codes** — Create, edit, disable, delete promo codes
- 📈 **Statistics** — Daily/weekly/monthly sales and best-selling products
- ⚙️ **Settings** — Bot name, currency, support, payment addresses, maintenance mode
- 📝 **Logs** — View and export log files for all categories

## Quick Start

### 1. Clone and Install

```bash
git clone <your-repo>
cd jah-shop2-bot
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
nano .env
```

Fill in:
```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
SUPPORT_USERNAME=your_username
USDT_ADDRESS=0xYourAddress
BANK_DETAILS=Bank Name | Account: 123456 | Name: Your Name
```

### 3. Run

```bash
python bot.py
```

## Project Structure

```
jah-shop2-bot/
├── bot.py                  # Entry point
├── config.py               # Configuration
├── requirements.txt
├── .env.example
├── data/                   # JSON storage
│   ├── products.json
│   ├── users.json
│   ├── wallets.json
│   ├── orders.json
│   ├── transactions.json
│   ├── promo_codes.json
│   ├── settings.json
│   ├── admins.json
│   └── support_messages.json
├── handlers/               # Telegram handlers
│   ├── start.py
│   ├── shop.py
│   ├── wallet.py
│   ├── orders.py
│   ├── promo.py
│   ├── support.py
│   ├── router.py
│   ├── admin.py
│   ├── admin_products.py
│   ├── admin_orders.py
│   ├── admin_users.py
│   ├── admin_wallet.py
│   ├── admin_broadcast.py
│   ├── admin_promos.py
│   ├── admin_settings.py
│   └── admin_logs.py
├── services/               # Business logic
│   ├── database.py
│   ├── user_service.py
│   ├── wallet_service.py
│   ├── product_service.py
│   ├── order_service.py
│   ├── promo_service.py
│   ├── support_service.py
│   └── settings_service.py
├── keyboards/              # Keyboard builders
│   ├── menus.py
│   ├── shop_kb.py
│   ├── wallet_kb.py
│   └── admin_kb.py
├── models/                 # Data models
│   └── models.py
├── middlewares/
│   └── auth.py
├── utils/
│   ├── formatting.py
│   ├── rate_limiter.py
│   ├── logger.py
│   └── validators.py
├── images/                 # Product images
├── logs/                   # Log files
└── backups/               # Auto-backups
```

## Sample Promo Codes

Two codes are pre-loaded:
- `WELCOME10` — 10% off any order
- `SAVE5` — $5 off orders over $20

## Security

- Rate limiting: 10 messages per 30 seconds per user
- Admin-only panel with ID whitelist from `.env`
- Banned user blocking
- Input validation on all user inputs
- Atomic JSON writes (temp → rename) to prevent corruption
- Automatic backups before write operations

## License

MIT
