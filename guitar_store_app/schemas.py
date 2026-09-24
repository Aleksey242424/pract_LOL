from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from decimal import Decimal


class ProductBase(BaseModel):
    article: str
    name: str
    price: Decimal = Field(ge=0)
    manufacturer_id: int
    category_id: int
    material: Optional[str] = None
    pickup_type: Optional[str] = None
    strings_count: Optional[int] = None
    fret_count: Optional[int] = None
    color: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id_product: int
    class Config:
        from_attributes = True


class CustomerBase(BaseModel):
    fio: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerOut(CustomerBase):
    id_customer: int
    class Config:
        from_attributes = True


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    price: Decimal = Field(ge=0)


class OrderCreate(BaseModel):
    order_number: str
    customer_id: int
    order_date: date
    status: str
    items: List[OrderItemCreate] = []


class OrderOut(BaseModel):
    id_order: int
    order_number: str
    customer_id: int
    order_date: date
    status: str
    class Config:
        from_attributes = True


class UserRegister(BaseModel):
    fio: str = Field(min_length=2, max_length=100)
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4, max_length=100)
    role: str = "client"  # по умолчанию клиент


class UserLogin(BaseModel):
    login: str
    password: str


class UserOut(BaseModel):
    id_user: int
    fio: str
    login: str
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut