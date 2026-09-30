from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Product, Customer, Order, OrderItem,User
import schemas
from auth import hash_password, verify_password
from datetime import date
from models import Warehouse, WarehouseStock, Product


# ---------- PRODUCTS ----------
def get_products(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Product).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int):
    return db.query(Product).filter(Product.id_product == product_id).first()


def create_product(db: Session, product: schemas.ProductCreate):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, data: schemas.ProductCreate):
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    for key, value in data.model_dump().items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    db.delete(db_product)
    db.commit()
    return db_product


# ---------- CUSTOMERS ----------
def get_customers(db: Session):
    return db.query(Customer).all()


def create_customer(db: Session, customer: schemas.CustomerCreate):
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


# ---------- ORDERS ----------
def get_orders(db: Session):
    return db.query(Order).all()


def create_order(db: Session, order: schemas.OrderCreate):
    db_order = Order(
        order_number=order.order_number,
        customer_id=order.customer_id,
        order_date=order.order_date,
        status=order.status,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    for item in order.items:
        db_item = OrderItem(
            order_id=db_order.id_order,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
        )
        db.add(db_item)
    db.commit()
    db.refresh(db_order)
    return db_order


# ---------- АНАЛИТИКА (приятный бонус) ----------
def get_sales_summary(db: Session):
    """Сумма продаж по товарам."""
    result = (
        db.query(
            Product.name,
            func.sum(OrderItem.quantity * OrderItem.price).label("total_sales")
        )
        .join(OrderItem, OrderItem.product_id == Product.id_product)
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.quantity * OrderItem.price).desc())
        .all()
    )
    return [{"product": r[0], "total_sales": float(r[1])} for r in result]



def get_user_by_login(db: Session, login: str):
    return db.query(User).filter(User.login == login).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id_user == user_id).first()


def create_user(db: Session, fio: str, login: str, password: str, role: str = "client"):
    if get_user_by_login(db, login):
        return None
    user = User(
        fio=fio,
        login=login,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, login: str, password: str):
    user = get_user_by_login(db, login)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def get_customer_by_user(db: Session, user_id: int):
    """Найти запись клиента, привязанную к пользователю."""
    return db.query(Customer).filter(Customer.user_id == user_id).first()


def get_or_create_customer_for_user(db: Session, user: User):
    """Вернуть customers-запись для пользователя. Создать, если нет."""
    customer = get_customer_by_user(db, user.id_user)
    if customer:
        return customer
    customer = Customer(
        fio=user.fio,
        user_id=user.id_user,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_order_for_user(db: Session, user: User, items: list):
    """
    Создаёт заказ для текущего пользователя.
    items: [{"product_id": int, "quantity": int}, ...]
    """
    customer = get_or_create_customer_for_user(db, user)

    # Генерируем номер заказа
    last = db.query(Order).order_by(Order.id_order.desc()).first()
    next_num = (last.id_order + 1) if last else 1
    order_number = f"ORD-{1000 + next_num}"

    order = Order(
        order_number=order_number,
        customer_id=customer.id_customer,
        order_date=date.today(),
        status="В обработке",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    total = 0
    for item in items:
        product = get_product(db, item["product_id"])
        if not product:
            continue
        qty = item["quantity"]
        db_item = OrderItem(
            order_id=order.id_order,
            product_id=product.id_product,
            quantity=qty,
            price=product.price,
        )
        db.add(db_item)
        total += float(product.price) * qty
    db.commit()
    db.refresh(order)
    return order, total


def get_orders_for_user(db: Session, user: User):
    """Вернуть заказы текущего пользователя."""
    customer = get_customer_by_user(db, user.id_user)
    if not customer:
        return []
    return (
        db.query(Order)
        .filter(Order.customer_id == customer.id_customer)
        .order_by(Order.order_date.desc())
        .all()
    )

def get_orders_with_totals(db: Session):
    """
    Возвращает список заказов с ФИО клиента и итоговой суммой.
    Используется на странице /orders и в отчёте.
    """
    rows = (
        db.query(
            Order.id_order,
            Order.order_number,
            Customer.fio.label("customer_name"),
            Order.order_date,
            Order.status,
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0).label("total"),
        )
        .join(Customer, Customer.id_customer == Order.customer_id)
        .outerjoin(OrderItem, OrderItem.order_id == Order.id_order)
        .group_by(Order.id_order, Customer.fio)
        .order_by(Order.order_date.desc(), Order.id_order.desc())
        .all()
    )
    return [
        {
            "id_order": r.id_order,
            "order_number": r.order_number,
            "customer_name": r.customer_name,
            "order_date": r.order_date,
            "status": r.status,
            "total": float(r.total),
        }
        for r in rows
    ]

def get_warehouse_stock(db: Session):
    """
    Возвращает список остатков: склад, товар, артикул, количество.
    Используется на странице /warehouses.
    """
    rows = (
        db.query(
            Warehouse.id_warehouse,
            Warehouse.name.label("warehouse_name"),
            Warehouse.address.label("warehouse_address"),
            Product.id_product,
            Product.article,
            Product.name.label("product_name"),
            Product.price,
            WarehouseStock.quantity,
        )
        .join(WarehouseStock, WarehouseStock.warehouse_id == Warehouse.id_warehouse)
        .join(Product, Product.id_product == WarehouseStock.product_id)
        .order_by(Warehouse.name, Product.name)
        .all()
    )
    return [
        {
            "id_warehouse": r.id_warehouse,
            "warehouse_name": r.warehouse_name,
            "warehouse_address": r.warehouse_address,
            "id_product": r.id_product,
            "article": r.article,
            "product_name": r.product_name,
            "price": float(r.price),
            "quantity": r.quantity,
            "stock_value": float(r.price) * r.quantity,
        }
        for r in rows
    ]


def get_warehouses_summary(db: Session):
    """
    Сводка по складам: сколько позиций, сколько всего единиц, общая стоимость.
    """
    rows = (
        db.query(
            Warehouse.id_warehouse,
            Warehouse.name,
            Warehouse.address,
            func.count(WarehouseStock.product_id).label("positions"),
            func.coalesce(func.sum(WarehouseStock.quantity), 0).label("total_units"),
            func.coalesce(func.sum(WarehouseStock.quantity * Product.price), 0).label("total_value"),
        )
        .outerjoin(WarehouseStock, WarehouseStock.warehouse_id == Warehouse.id_warehouse)
        .outerjoin(Product, Product.id_product == WarehouseStock.product_id)
        .group_by(Warehouse.id_warehouse)
        .order_by(Warehouse.name)
        .all()
    )
    return [
        {
            "id_warehouse": r.id_warehouse,
            "name": r.name,
            "address": r.address,
            "positions": r.positions,
            "total_units": int(r.total_units),
            "total_value": float(r.total_value),
        }
        for r in rows
    ]