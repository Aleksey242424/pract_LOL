# models.py
from datetime import date
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Numeric, ForeignKey,
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    fio = Column(String(100), nullable=False)
    login = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="client", nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)


class Category(Base):
    __tablename__ = "categories"
    id_category = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)


class Manufacturer(Base):
    __tablename__ = "manufacturers"
    id_manufacturer = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)


class Product(Base):
    __tablename__ = "products"

    id_product = Column(Integer, primary_key=True, index=True)
    article = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    manufacturer_id = Column(
        Integer, ForeignKey("manufacturers.id_manufacturer"), nullable=False
    )
    category_id = Column(
        Integer, ForeignKey("categories.id_category"), nullable=False
    )
    material = Column(String(100), nullable=True)
    pickup_type = Column(String(50), nullable=True)
    strings_count = Column(Integer, nullable=True)
    fret_count = Column(Integer, nullable=True)
    color = Column(String(50), nullable=True)

    manufacturer = relationship(
        "Manufacturer",
        foreign_keys=[manufacturer_id],
        primaryjoin="Product.manufacturer_id == Manufacturer.id_manufacturer",
        lazy="joined",
    )
    category = relationship(
        "Category",
        foreign_keys=[category_id],
        primaryjoin="Product.category_id == Category.id_category",
        lazy="joined",
    )


class WarehouseStock(Base):
    __tablename__ = "warehouse_stock"
    warehouse_id = Column(Integer, primary_key=True)
    product_id = Column(Integer, primary_key=True)
    quantity = Column(Integer, nullable=False, default=0)


class Customer(Base):
    __tablename__ = "customers"

    id_customer = Column(Integer, primary_key=True)
    fio = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    user_id = Column(Integer, nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id_order = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), nullable=False)
    customer_id = Column(Integer, nullable=False)
    order_date = Column(Date, default=lambda: date.today())
    status = Column(String(30), nullable=False, default="new")


class OrderItem(Base):
    __tablename__ = "order_items"

    id_order_item = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)