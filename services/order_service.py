"""
Order Service — Purchase flow, order management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import ORDERS_FILE, ORDER_STATUS
from models.models import Order
from services.database import get_db

logger = logging.getLogger("jah_shop.order_service")
_db = get_db(ORDERS_FILE, {"orders": []})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict]:
    return _db.read().get("orders", [])


def _save(orders: list[dict]) -> None:
    _db.write({"orders": orders}, backup=True)


# ─── Public API ──────────────────────────────────────────────

def create_order(
    user_id: int,
    product_id: str,
    product_name: str,
    price: float,
    currency: str = "USD",
    promo_code: str = "",
    discount: float = 0.0,
) -> Order:
    orders = _load()
    order = Order(
        user_id=user_id,
        product_id=product_id,
        product_name=product_name,
        price=price,
        currency=currency,
        status="pending",
        promo_code=promo_code,
        discount=discount,
        final_price=round(price - discount, 2),
    )
    orders.append(order.to_dict())
    _save(orders)
    logger.info(f"Order created: {order.id} by user {user_id} for product {product_id}")
    return order


def get_order(order_id: str) -> Order | None:
    for o in _load():
        if o.get("id") == order_id:
            return Order.from_dict(o)
    return None


def get_user_orders(user_id: int) -> list[Order]:
    orders = [Order.from_dict(o) for o in _load() if o.get("user_id") == user_id]
    return sorted(orders, key=lambda o: o.created_at, reverse=True)


def get_all_orders(status: str | None = None) -> list[Order]:
    orders = [Order.from_dict(o) for o in _load()]
    if status:
        orders = [o for o in orders if o.status == status]
    return sorted(orders, key=lambda o: o.created_at, reverse=True)


def update_order_status(order_id: str, status: str, admin_note: str = "") -> Order | None:
    orders = _load()
    for o in orders:
        if o.get("id") == order_id:
            o["status"] = status
            if admin_note:
                o["admin_note"] = admin_note
            o["updated_at"] = _now()
            _save(orders)
            logger.info(f"Order {order_id} status → {status}")
            return Order.from_dict(o)
    return None


def complete_order(order_id: str, delivery_data: str = "", admin_note: str = "") -> Order | None:
    orders = _load()
    for o in orders:
        if o.get("id") == order_id:
            o["status"] = "completed"
            o["delivery_data"] = delivery_data
            if admin_note:
                o["admin_note"] = admin_note
            o["updated_at"] = _now()
            _save(orders)
            return Order.from_dict(o)
    return None


def refund_order(order_id: str) -> Order | None:
    """Mark order as refunded (wallet refund must be handled separately)."""
    return update_order_status(order_id, "refunded", "Order refunded")


def search_orders(query: str) -> list[Order]:
    query = query.lower().strip()
    results = []
    for o in _load():
        if (
            query in o.get("id", "").lower()
            or query in str(o.get("user_id", ""))
            or query in o.get("product_name", "").lower()
            or query in o.get("status", "").lower()
        ):
            results.append(Order.from_dict(o))
    return results


def get_order_count(status: str | None = None) -> int:
    orders = _load()
    if status:
        return sum(1 for o in orders if o.get("status") == status)
    return len(orders)


def get_pending_orders() -> list[Order]:
    return get_all_orders("pending")


def get_completed_orders() -> list[Order]:
    return get_all_orders("completed")
