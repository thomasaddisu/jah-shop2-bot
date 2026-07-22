"""
Promo Code Service — Validate and manage promotional codes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import PROMO_CODES_FILE
from models.models import PromoCode
from services.database import get_db

logger = logging.getLogger("jah_shop.promo_service")
_db = get_db(PROMO_CODES_FILE, {"promo_codes": []})


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


def _load() -> list[dict]:
    return _db.read().get("promo_codes", [])


def _save(codes: list[dict]) -> None:
    _db.write({"promo_codes": codes})


# ─── Public API ──────────────────────────────────────────────

def get_all_promo_codes() -> list[PromoCode]:
    return [PromoCode.from_dict(p) for p in _load()]


def get_promo_code(code_str: str) -> PromoCode | None:
    code_str = code_str.upper().strip()
    for p in _load():
        if p.get("code", "").upper() == code_str:
            return PromoCode.from_dict(p)
    return None


def get_promo_by_id(promo_id: str) -> PromoCode | None:
    for p in _load():
        if p.get("id") == promo_id:
            return PromoCode.from_dict(p)
    return None


def validate_promo_code(code_str: str, user_id: int, order_amount: float) -> tuple[bool, str, PromoCode | None]:
    """
    Validate a promo code.
    Returns (valid: bool, reason: str, promo: PromoCode | None)
    """
    promo = get_promo_code(code_str)
    if not promo:
        return False, "❌ Promo code not found.", None

    if not promo.active:
        return False, "❌ This promo code is no longer active.", None

    # Check expiry
    if promo.expires_at:
        try:
            exp = datetime.fromisoformat(promo.expires_at.replace("Z", "+00:00"))
            if _now_dt() > exp:
                return False, "❌ This promo code has expired.", None
        except ValueError:
            pass

    # Check max uses
    if promo.max_uses > 0 and promo.uses >= promo.max_uses:
        return False, "❌ This promo code has reached its maximum uses.", None

    # Check per-user use
    if user_id in promo.used_by:
        return False, "❌ You have already used this promo code.", None

    # Check minimum order amount
    if order_amount < promo.min_order_amount:
        return False, f"❌ Minimum order amount for this code is ${promo.min_order_amount:.2f}.", None

    return True, "✅ Promo code applied!", promo


def apply_promo_code(promo_id: str, user_id: int) -> bool:
    """Mark a promo code as used by a user."""
    codes = _load()
    for p in codes:
        if p.get("id") == promo_id:
            used_by = p.get("used_by", [])
            if user_id not in used_by:
                used_by.append(user_id)
                p["used_by"] = used_by
                p["uses"] = p.get("uses", 0) + 1
                _save(codes)
                return True
    return False


def calculate_discount(promo: PromoCode, price: float) -> float:
    if promo.discount_type == "percentage":
        return round(price * promo.discount_value / 100, 2)
    elif promo.discount_type == "flat":
        return min(round(promo.discount_value, 2), price)
    return 0.0


def create_promo_code(data: dict) -> PromoCode:
    codes = _load()
    promo = PromoCode(
        code=data["code"],
        discount_type=data["discount_type"],
        discount_value=float(data["discount_value"]),
        min_order_amount=float(data.get("min_order_amount", 0)),
        max_uses=int(data.get("max_uses", 0)),
        active=bool(data.get("active", True)),
        expires_at=data.get("expires_at", ""),
    )
    codes.append(promo.to_dict())
    _save(codes)
    logger.info(f"Promo code created: {promo.code}")
    return promo


def update_promo_code(promo_id: str, updates: dict) -> PromoCode | None:
    codes = _load()
    for p in codes:
        if p.get("id") == promo_id:
            for k, v in updates.items():
                if k not in ("id", "uses", "used_by", "created_at"):
                    p[k] = v
            _save(codes)
            return PromoCode.from_dict(p)
    return None


def delete_promo_code(promo_id: str) -> bool:
    codes = _load()
    new_codes = [p for p in codes if p.get("id") != promo_id]
    if len(new_codes) == len(codes):
        return False
    _save(new_codes)
    return True


def disable_promo_code(promo_id: str) -> bool:
    result = update_promo_code(promo_id, {"active": False})
    return result is not None
