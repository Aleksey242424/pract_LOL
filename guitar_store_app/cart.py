# cart.py
from decimal import Decimal
from fastapi import Request
from itsdangerous import URLSafeSerializer
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Product, WarehouseStock

SECRET_KEY = "change-me-in-production"
cart_serializer = URLSafeSerializer(SECRET_KEY, salt="cart")


def get_cart(request: Request) -> dict:
    raw = request.cookies.get("cart")
    if not raw:
        return {}
    try:
        return cart_serializer.loads(raw)
    except Exception:
        return {}


def save_cart(response, cart: dict):
    response.set_cookie(
        "cart",
        cart_serializer.dumps(cart),
        httponly=True,
        max_age=7 * 24 * 3600,
    )


def cart_count(request: Request) -> int:
    cart = get_cart(request)
    try:
        return sum(int(v) for v in cart.values())
    except Exception:
        return 0


def get_product_stock(db: Session, product_id: int) -> int:
    result = (
        db.query(func.coalesce(func.sum(WarehouseStock.quantity), 0))
        .filter(WarehouseStock.product_id == product_id)
        .scalar()
    )
    return int(result or 0)


def build_cart_items(db: Session, cart: dict):
    items = []
    total = Decimal("0")
    for pid, qty in cart.items():
        product = (
            db.query(Product).filter(Product.id_product == int(pid)).first()
        )
        if product:
            line_total = product.price * qty
            total += line_total
            items.append({
                "product": product,
                "quantity": qty,
                "line_total": line_total,
            })
    return items, total