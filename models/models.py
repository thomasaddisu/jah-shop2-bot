"""
Models — Dataclass definitions with factory methods.
All models use dict serialization for JSON compatibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "") -> str:
    uid = str(uuid.uuid4()).replace("-", "")[:12]
    return f"{prefix}{uid}" if prefix else uid


# ─── User ─────────────────────────────────────────────────────

class User:
    __slots__ = (
        "user_id", "username", "first_name", "last_name",
        "is_banned", "joined_at", "last_active", "language_code",
    )

    def __init__(
        self,
        user_id: int,
        username: str = "",
        first_name: str = "",
        last_name: str = "",
        is_banned: bool = False,
        joined_at: str = "",
        last_active: str = "",
        language_code: str = "en",
    ) -> None:
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.is_banned = is_banned
        self.joined_at = joined_at or _now()
        self.last_active = last_active or _now()
        self.language_code = language_code

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        return cls(**{k: d.get(k, v) for k, v in cls._defaults().items()})

    @classmethod
    def _defaults(cls) -> dict:
        return {
            "user_id": 0, "username": "", "first_name": "", "last_name": "",
            "is_banned": False, "joined_at": _now(), "last_active": _now(),
            "language_code": "en",
        }

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}

    @property
    def display_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.username or str(self.user_id)


# ─── Wallet ────────────────────────────────────────────────────

class Wallet:
    __slots__ = ("user_id", "balance", "total_deposited", "total_spent", "updated_at")

    def __init__(
        self,
        user_id: int,
        balance: float = 0.0,
        total_deposited: float = 0.0,
        total_spent: float = 0.0,
        updated_at: str = "",
    ) -> None:
        self.user_id = user_id
        self.balance = round(balance, 2)
        self.total_deposited = round(total_deposited, 2)
        self.total_spent = round(total_spent, 2)
        self.updated_at = updated_at or _now()

    @classmethod
    def from_dict(cls, d: dict) -> "Wallet":
        return cls(
            user_id=d.get("user_id", 0),
            balance=d.get("balance", 0.0),
            total_deposited=d.get("total_deposited", 0.0),
            total_spent=d.get("total_spent", 0.0),
            updated_at=d.get("updated_at", _now()),
        )

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


# ─── WalletRequest ─────────────────────────────────────────────

class WalletRequest:
    __slots__ = (
        "id", "user_id", "amount", "method", "status",
        "admin_note", "proof", "screenshot_file_id", "created_at", "updated_at",
    )

    def __init__(
        self,
        user_id: int,
        amount: float,
        method: str,
        status: str = "pending",
        admin_note: str = "",
        proof: str = "",
        screenshot_file_id: str = "",
        id: str = "",
        created_at: str = "",
        updated_at: str = "",
    ) -> None:
        self.id = id or _new_id("wr_")
        self.user_id = user_id
        self.amount = round(amount, 2)
        self.method = method
        self.status = status
        self.admin_note = admin_note
        self.proof = proof
        self.screenshot_file_id = screenshot_file_id
        self.created_at = created_at or _now()
        self.updated_at = updated_at or _now()

    @classmethod
    def from_dict(cls, d: dict) -> "WalletRequest":
        return cls(**{k: d.get(k, "") for k in (
            "id", "user_id", "amount", "method", "status",
            "admin_note", "proof", "screenshot_file_id", "created_at", "updated_at",
        )})

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


# ─── Order ─────────────────────────────────────────────────────

class Order:
    __slots__ = (
        "id", "user_id", "product_id", "product_name",
        "price", "currency", "status", "promo_code",
        "discount", "final_price", "delivery_data",
        "admin_note", "created_at", "updated_at",
    )

    def __init__(
        self,
        user_id: int,
        product_id: str,
        product_name: str,
        price: float,
        currency: str = "ETB",
        status: str = "pending",
        promo_code: str = "",
        discount: float = 0.0,
        final_price: float = 0.0,
        delivery_data: str = "",
        admin_note: str = "",
        id: str = "",
        created_at: str = "",
        updated_at: str = "",
    ) -> None:
        self.id = id or _new_id("ord_")
        self.user_id = user_id
        self.product_id = product_id
        self.product_name = product_name
        self.price = round(price, 2)
        self.currency = currency
        self.status = status
        self.promo_code = promo_code
        self.discount = round(discount, 2)
        self.final_price = round(final_price if final_price else price - discount, 2)
        self.delivery_data = delivery_data
        self.admin_note = admin_note
        self.created_at = created_at or _now()
        self.updated_at = updated_at or _now()

    @classmethod
    def from_dict(cls, d: dict) -> "Order":
        return cls(**{k: d.get(k, "") for k in (
            "id", "user_id", "product_id", "product_name",
            "price", "currency", "status", "promo_code",
            "discount", "final_price", "delivery_data",
            "admin_note", "created_at", "updated_at",
        )})

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


# ─── Transaction ───────────────────────────────────────────────

class Transaction:
    __slots__ = (
        "id", "user_id", "type", "amount", "description",
        "reference_id", "created_at",
    )

    def __init__(
        self,
        user_id: int,
        type: str,  # "credit" | "debit"
        amount: float,
        description: str = "",
        reference_id: str = "",
        id: str = "",
        created_at: str = "",
    ) -> None:
        self.id = id or _new_id("txn_")
        self.user_id = user_id
        self.type = type
        self.amount = round(abs(amount), 2)
        self.description = description
        self.reference_id = reference_id
        self.created_at = created_at or _now()

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(**{k: d.get(k, "") for k in (
            "id", "user_id", "type", "amount",
            "description", "reference_id", "created_at",
        )})

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


# ─── Product ────────────────────────────────────────────────────

class Product:
    __slots__ = (
        "id", "name", "category", "description", "price",
        "currency", "duration", "stock", "available", "image",
        "delivery_type", "created_at", "updated_at",
    )

    def __init__(
        self,
        name: str,
        category: str,
        description: str,
        price: float,
        currency: str = "ETB",
        duration: str = "30 days",
        stock: int = 0,
        available: bool = True,
        image: str = "",
        delivery_type: str = "manual",
        id: str = "",
        created_at: str = "",
        updated_at: str = "",
    ) -> None:
        self.id = id or _new_id("prod_")
        self.name = name
        self.category = category
        self.description = description
        self.price = round(price, 2)
        self.currency = currency
        self.duration = duration
        self.stock = max(0, int(stock))
        self.available = available
        self.image = image
        self.delivery_type = delivery_type
        self.created_at = created_at or _now()
        self.updated_at = updated_at or _now()

    @classmethod
    def from_dict(cls, d: dict) -> "Product":
        return cls(**{k: d.get(k, "") for k in (
            "id", "name", "category", "description", "price",
            "currency", "duration", "stock", "available",
            "image", "delivery_type", "created_at", "updated_at",
        )})

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


# ─── PromoCode ─────────────────────────────────────────────────

class PromoCode:
    __slots__ = (
        "id", "code", "discount_type", "discount_value",
        "min_order_amount", "max_uses", "uses", "used_by",
        "active", "expires_at", "created_at",
    )

    def __init__(
        self,
        code: str,
        discount_type: str,  # "percentage" | "flat"
        discount_value: float,
        min_order_amount: float = 0.0,
        max_uses: int = 0,
        uses: int = 0,
        used_by: list | None = None,
        active: bool = True,
        expires_at: str = "",
        id: str = "",
        created_at: str = "",
    ) -> None:
        self.id = id or _new_id("promo_")
        self.code = code.upper().strip()
        self.discount_type = discount_type
        self.discount_value = round(discount_value, 2)
        self.min_order_amount = round(min_order_amount, 2)
        self.max_uses = max_uses
        self.uses = uses
        self.used_by: list[int] = used_by or []
        self.active = active
        self.expires_at = expires_at
        self.created_at = created_at or _now()

    @classmethod
    def from_dict(cls, d: dict) -> "PromoCode":
        obj = cls(
            code=d.get("code", ""),
            discount_type=d.get("discount_type", "percentage"),
            discount_value=d.get("discount_value", 0),
            min_order_amount=d.get("min_order_amount", 0),
            max_uses=d.get("max_uses", 0),
            uses=d.get("uses", 0),
            used_by=d.get("used_by", []),
            active=d.get("active", True),
            expires_at=d.get("expires_at", ""),
            id=d.get("id", ""),
            created_at=d.get("created_at", _now()),
        )
        return obj

    def to_dict(self) -> dict:
        d = {s: getattr(self, s) for s in self.__slots__}
        return d


# ─── SupportMessage ────────────────────────────────────────────

class SupportMessage:
    __slots__ = (
        "id", "user_id", "message", "reply", "status",
        "admin_id", "created_at", "replied_at",
    )

    def __init__(
        self,
        user_id: int,
        message: str,
        reply: str = "",
        status: str = "open",
        admin_id: int = 0,
        id: str = "",
        created_at: str = "",
        replied_at: str = "",
    ) -> None:
        self.id = id or _new_id("sup_")
        self.user_id = user_id
        self.message = message
        self.reply = reply
        self.status = status
        self.admin_id = admin_id
        self.created_at = created_at or _now()
        self.replied_at = replied_at

    @classmethod
    def from_dict(cls, d: dict) -> "SupportMessage":
        return cls(
            id=d.get("id", ""),
            user_id=d.get("user_id", 0),
            message=d.get("message", ""),
            reply=d.get("reply", ""),
            status=d.get("status", "open"),
            admin_id=d.get("admin_id", 0),
            created_at=d.get("created_at", _now()),
            replied_at=d.get("replied_at", ""),
        )

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}
