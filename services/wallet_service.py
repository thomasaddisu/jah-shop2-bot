"""
Wallet Service — Balance management, top-up requests, transactions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import WALLETS_FILE, TRANSACTIONS_FILE
from models.models import Wallet, WalletRequest, Transaction
from services.database import get_db

logger = logging.getLogger("jah_shop.wallet_service")
_wallet_db = get_db(WALLETS_FILE, {"wallets": []})
_txn_db = get_db(TRANSACTIONS_FILE, {"transactions": []})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Wallet ──────────────────────────────────────────────────

def get_wallet(user_id: int) -> Wallet:
    """Get or create a wallet for the user."""
    wallets = _wallet_db.read().get("wallets", [])
    for w in wallets:
        if w.get("user_id") == user_id:
            return Wallet.from_dict(w)
    # Create new wallet
    wallet = Wallet(user_id=user_id)
    wallets.append(wallet.to_dict())
    _wallet_db.write({"wallets": wallets})
    return wallet


def get_balance(user_id: int) -> float:
    return get_wallet(user_id).balance


def credit_wallet(user_id: int, amount: float, description: str = "", ref_id: str = "") -> Wallet:
    """Add funds to wallet."""
    data = _wallet_db.read()
    wallets = data.get("wallets", [])
    found = False
    for w in wallets:
        if w.get("user_id") == user_id:
            w["balance"] = round(w.get("balance", 0) + amount, 2)
            w["total_deposited"] = round(w.get("total_deposited", 0) + amount, 2)
            w["updated_at"] = _now()
            found = True
            wallet = Wallet.from_dict(w)
            break
    if not found:
        wallet = Wallet(user_id=user_id, balance=amount, total_deposited=amount)
        wallets.append(wallet.to_dict())
    _wallet_db.write({"wallets": wallets})

    # Log transaction
    _add_transaction(user_id, "credit", amount, description, ref_id)
    logger.info(f"Wallet credited: user={user_id}, amount={amount}")
    return wallet


def debit_wallet(user_id: int, amount: float, description: str = "", ref_id: str = "") -> bool:
    """Deduct funds from wallet. Returns False if insufficient balance."""
    data = _wallet_db.read()
    wallets = data.get("wallets", [])
    for w in wallets:
        if w.get("user_id") == user_id:
            if w.get("balance", 0) < amount:
                return False
            w["balance"] = round(w["balance"] - amount, 2)
            w["total_spent"] = round(w.get("total_spent", 0) + amount, 2)
            w["updated_at"] = _now()
            _wallet_db.write({"wallets": wallets})
            _add_transaction(user_id, "debit", amount, description, ref_id)
            logger.info(f"Wallet debited: user={user_id}, amount={amount}")
            return True
    return False


def admin_set_balance(user_id: int, new_balance: float) -> Wallet:
    """Admin: directly set a user's wallet balance."""
    data = _wallet_db.read()
    wallets = data.get("wallets", [])
    for w in wallets:
        if w.get("user_id") == user_id:
            old = w.get("balance", 0)
            diff = new_balance - old
            w["balance"] = round(new_balance, 2)
            w["updated_at"] = _now()
            if diff > 0:
                w["total_deposited"] = round(w.get("total_deposited", 0) + diff, 2)
            _wallet_db.write({"wallets": wallets})
            _add_transaction(user_id, "credit" if diff >= 0 else "debit", abs(diff), "Admin adjustment")
            return Wallet.from_dict(w)
    wallet = Wallet(user_id=user_id, balance=new_balance, total_deposited=new_balance)
    wallets.append(wallet.to_dict())
    _wallet_db.write({"wallets": wallets})
    return wallet


# ─── Wallet Requests ─────────────────────────────────────────

_REQUESTS_KEY = "wallet_requests"
_req_db = get_db(WALLETS_FILE, {"wallets": [], "wallet_requests": []})


def create_wallet_request(user_id: int, amount: float, method: str) -> WalletRequest:
    data = _req_db.read()
    requests = data.get(_REQUESTS_KEY, [])
    req = WalletRequest(user_id=user_id, amount=amount, method=method)
    requests.append(req.to_dict())
    data[_REQUESTS_KEY] = requests
    _req_db.write(data)
    return req


def get_wallet_request(req_id: str) -> WalletRequest | None:
    data = _req_db.read()
    for r in data.get(_REQUESTS_KEY, []):
        if r.get("id") == req_id:
            return WalletRequest.from_dict(r)
    return None


def get_pending_wallet_requests() -> list[WalletRequest]:
    data = _req_db.read()
    return [WalletRequest.from_dict(r) for r in data.get(_REQUESTS_KEY, [])
            if r.get("status") == "pending"]


def get_all_wallet_requests() -> list[WalletRequest]:
    data = _req_db.read()
    return [WalletRequest.from_dict(r) for r in data.get(_REQUESTS_KEY, [])]


def get_user_wallet_requests(user_id: int) -> list[WalletRequest]:
    data = _req_db.read()
    return [WalletRequest.from_dict(r) for r in data.get(_REQUESTS_KEY, [])
            if r.get("user_id") == user_id]


def approve_wallet_request(req_id: str, admin_note: str = "") -> WalletRequest | None:
    data = _req_db.read()
    requests = data.get(_REQUESTS_KEY, [])
    for r in requests:
        if r.get("id") == req_id:
            if r.get("status") != "pending":
                return None
            r["status"] = "approved"
            r["admin_note"] = admin_note
            r["updated_at"] = _now()
            data[_REQUESTS_KEY] = requests
            _req_db.write(data)
            req = WalletRequest.from_dict(r)
            credit_wallet(req.user_id, req.amount, f"Top-up approved ({req.method})", req_id)
            return req
    return None


def reject_wallet_request(req_id: str, admin_note: str = "") -> WalletRequest | None:
    data = _req_db.read()
    requests = data.get(_REQUESTS_KEY, [])
    for r in requests:
        if r.get("id") == req_id:
            r["status"] = "rejected"
            r["admin_note"] = admin_note
            r["updated_at"] = _now()
            data[_REQUESTS_KEY] = requests
            _req_db.write(data)
            return WalletRequest.from_dict(r)
    return None


def has_pending_request(user_id: int) -> bool:
    return any(r for r in get_pending_wallet_requests() if r.user_id == user_id)


# ─── Transactions ────────────────────────────────────────────

def _add_transaction(user_id: int, type: str, amount: float,
                     description: str = "", reference_id: str = "") -> Transaction:
    data = _txn_db.read()
    txns = data.get("transactions", [])
    txn = Transaction(user_id=user_id, type=type, amount=amount,
                      description=description, reference_id=reference_id)
    txns.append(txn.to_dict())
    _txn_db.write({"transactions": txns})
    return txn


def get_user_transactions(user_id: int, limit: int = 20) -> list[Transaction]:
    data = _txn_db.read()
    txns = [Transaction.from_dict(t) for t in data.get("transactions", [])
            if t.get("user_id") == user_id]
    return sorted(txns, key=lambda t: t.created_at, reverse=True)[:limit]


def get_total_revenue() -> float:
    data = _txn_db.read()
    return round(sum(
        t.get("amount", 0) for t in data.get("transactions", [])
        if t.get("type") == "debit"
    ), 2)


def get_total_topups() -> float:
    data = _txn_db.read()
    return round(sum(
        t.get("amount", 0) for t in data.get("transactions", [])
        if t.get("type") == "credit"
    ), 2)
