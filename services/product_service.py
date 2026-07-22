"""
Product Service — CRUD operations for products.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import PRODUCTS_FILE, CATEGORIES
from models.models import Product
from services.database import get_db

logger = logging.getLogger("jah_shop.product_service")
_db = get_db(PRODUCTS_FILE, {"products": []})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict]:
    return _db.read().get("products", [])


def _save(products: list[dict]) -> None:
    _db.write({"products": products}, backup=True)


# ─── Public API ──────────────────────────────────────────────

def get_all_products(include_unavailable: bool = False) -> list[Product]:
    products = [Product.from_dict(p) for p in _load()]
    if not include_unavailable:
        products = [p for p in products if p.available and p.stock > 0]
    return products


def get_product(product_id: str) -> Product | None:
    for p in _load():
        if p.get("id") == product_id:
            return Product.from_dict(p)
    return None


def get_products_by_category(category: str, include_unavailable: bool = False) -> list[Product]:
    products = [Product.from_dict(p) for p in _load() if p.get("category") == category]
    if not include_unavailable:
        products = [p for p in products if p.available and p.stock > 0]
    return products


def create_product(data: dict) -> Product:
    products = _load()
    product = Product(
        name=data["name"],
        category=data["category"],
        description=data["description"],
        price=float(data["price"]),
        currency=data.get("currency", "USD"),
        duration=data.get("duration", "30 days"),
        stock=int(data.get("stock", 0)),
        available=bool(data.get("available", True)),
        image=data.get("image", ""),
        delivery_type=data.get("delivery_type", "manual"),
    )
    products.append(product.to_dict())
    _save(products)
    logger.info(f"Product created: {product.id} — {product.name}")
    return product


def update_product(product_id: str, updates: dict) -> Product | None:
    products = _load()
    for p in products:
        if p.get("id") == product_id:
            for key, value in updates.items():
                if key in ("price", "stock"):
                    p[key] = float(value) if key == "price" else int(value)
                elif key != "id":
                    p[key] = value
            p["updated_at"] = _now()
            _save(products)
            return Product.from_dict(p)
    return None


def delete_product(product_id: str) -> bool:
    products = _load()
    new_products = [p for p in products if p.get("id") != product_id]
    if len(new_products) == len(products):
        return False
    _save(new_products)
    logger.info(f"Product deleted: {product_id}")
    return True


def set_product_available(product_id: str, available: bool) -> bool:
    result = update_product(product_id, {"available": available})
    return result is not None


def decrement_stock(product_id: str, qty: int = 1) -> bool:
    products = _load()
    for p in products:
        if p.get("id") == product_id:
            if p.get("stock", 0) < qty:
                return False
            p["stock"] = p["stock"] - qty
            p["updated_at"] = _now()
            _save(products)
            return True
    return False


def update_stock(product_id: str, new_stock: int) -> bool:
    result = update_product(product_id, {"stock": max(0, new_stock)})
    return result is not None


def update_product_image(product_id: str, image_path: str) -> bool:
    result = update_product(product_id, {"image": image_path})
    return result is not None


def search_products(query: str, include_unavailable: bool = True) -> list[Product]:
    query = query.lower().strip()
    results = []
    for p in _load():
        if (
            query in p.get("name", "").lower()
            or query in p.get("description", "").lower()
            or query in p.get("category", "").lower()
        ):
            product = Product.from_dict(p)
            if not include_unavailable and (not product.available or product.stock == 0):
                continue
            results.append(product)
    return results


def get_product_count() -> int:
    return len(_load())


def get_available_product_count() -> int:
    return len([p for p in _load() if p.get("available") and p.get("stock", 0) > 0])


def get_category_labels() -> dict[str, str]:
    return CATEGORIES


def get_best_selling_products(limit: int = 5) -> list[dict]:
    from config import ORDERS_FILE
    from services.database import get_db as _get_db
    order_db = _get_db(ORDERS_FILE, {"orders": []})
    orders = order_db.read().get("orders", [])

    sales: dict[str, int] = {}
    for o in orders:
        if o.get("status") == "completed":
            pid = o.get("product_id", "")
            sales[pid] = sales.get(pid, 0) + 1

    ranked = sorted(sales.items(), key=lambda x: x[1], reverse=True)[:limit]
    results = []
    for pid, count in ranked:
        p = get_product(pid)
        if p:
            results.append({"product": p, "sales": count})
    return results
