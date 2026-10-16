# schemas.py
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserRegister(BaseModel):
    fio: str = Field(min_length=2, max_length=100)
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4, max_length=100)
    role: str = "client"

    @field_validator("login")
    @classmethod
    def login_no_spaces(cls, v):
        if " " in v:
            raise ValueError("Логин не должен содержать пробелов")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if v.isdigit():
            raise ValueError("Пароль не может состоять только из цифр")
        return v


class ProductCreate(BaseModel):
    article: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    price: Decimal = Field(gt=0)
    manufacturer_id: int
    category_id: int
    material: Optional[str] = None
    pickup_type: Optional[str] = None
    strings_count: Optional[int] = None
    fret_count: Optional[int] = None
    color: Optional[str] = None
    initial_stock: int = 0