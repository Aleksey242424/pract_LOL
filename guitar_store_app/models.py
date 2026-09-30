from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from database import Base



class Manufacturer(Base):
    __tablename__ = "manufacturers"
    id_manufacturer = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    products = relationship("Product", back_populates="manufacturer")


class Category(Base):
    __tablename__ = "categories"
    id_category = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id_product = Column(Integer, primary_key=True, index=True)
    article = Column(String(30), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id_manufacturer"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id_category"), nullable=False)
    material = Column(String(100))
    pickup_type = Column(String(100))
    strings_count = Column(Integer)
    fret_count = Column(Integer)
    color = Column(String(50))

    manufacturer = relationship("Manufacturer", back_populates="products")
    category = relationship("Category", back_populates="products")


class Customer(Base):
    __tablename__ = "customers"
    id_customer = Column(Integer, primary_key=True, index=True)
    fio = Column(String(100), nullable=False)
    phone = Column(String(30))
    email = Column(String(100))
    address = Column(String(200))
    user_id = Column(Integer, ForeignKey("users.id_user", ondelete="SET NULL"), unique=True)

    orders = relationship("Order", back_populates="customer")
    user = relationship("User")


class Order(Base):
    __tablename__ = "orders"
    id_order = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id_customer"), nullable=False)
    order_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id_order_item = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id_order", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id_product"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class User(Base):
    __tablename__ = "users"
    id_user = Column(Integer, primary_key=True, index=True)
    fio = Column(String(100), nullable=False)
    login = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # client | manager | admin

class Warehouse(Base):
    __tablename__ = "warehouses"
    id_warehouse = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200), nullable=False)

    stock = relationship("WarehouseStock", back_populates="warehouse", cascade="all, delete-orphan")


class WarehouseStock(Base):
    __tablename__ = "warehouse_stock"
    warehouse_id = Column(Integer, ForeignKey("warehouses.id_warehouse", ondelete="CASCADE"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id_product", ondelete="CASCADE"), primary_key=True)
    quantity = Column(Integer, nullable=False)

    warehouse = relationship("Warehouse", back_populates="stock")
    product = relationship("Product")