# ============================================================
# main.py — точка входа приложения Guitar Store
# FastAPI + PostgreSQL + JWT-аутентификация
# ============================================================

from fastapi import FastAPI, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel as PydanticBaseModel

import models
import schemas
import crud
from database import engine, get_db, Base
from auth import (
    create_access_token,
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_manager,
    require_any,
)

# ============================================================
# ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
# ============================================================
app = FastAPI(
    title="Guitar Store API",
    version="1.0",
    description="Учебный проект: магазин гитар с аутентификацией и ролями",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Если хочешь, чтобы SQLAlchemy сама создавала таблицы — раскомментируй.
# Но у тебя таблицы уже созданы через guitar_store.sql, так что обычно не нужно.
# Base.metadata.create_all(bind=engine)


# ============================================================
# АУТЕНТИФИКАЦИЯ — API
# ============================================================

@app.post("/api/auth/register", response_model=schemas.UserOut, tags=["auth"])
def api_register(user: schemas.UserRegister, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    Публично можно создавать только client.
    Создавать manager/admin может только существующий admin.
    """
    if user.role != "client":
        admin_exists = db.query(models.User).filter(models.User.role == "admin").first()
        if admin_exists:
            raise HTTPException(
                status_code=403,
                detail="Создавать менеджеров/админов может только администратор",
            )

    created = crud.create_user(db, user.fio, user.login, user.password, user.role)
    if not created:
        raise HTTPException(status_code=400, detail="Логин уже занят")
    return created


@app.post("/api/auth/login", response_model=schemas.Token, tags=["auth"])
def api_login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Логин через OAuth2 Password Flow.
    В Swagger UI: username = логин, password = пароль.
    """
    user = crud.authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": str(user.id_user), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/api/auth/me", response_model=schemas.UserOut, tags=["auth"])
def api_me(current_user: models.User = Depends(get_current_user)):
    """Информация о текущем пользователе (по токену)."""
    return current_user


# ============================================================
# HTML-СТРАНИЦЫ АУТЕНТИФИКАЦИИ
# ============================================================

@app.get("/login", response_class=HTMLResponse, tags=["pages"])
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", tags=["pages"])
def login_submit(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = crud.authenticate_user(db, login, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=401,
        )
    token = create_access_token({"sub": str(user.id_user), "role": user.role})
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24,
        samesite="lax",
    )
    return response


@app.get("/register", response_class=HTMLResponse, tags=["pages"])
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", tags=["pages"])
def register_submit(
    request: Request,
    fio: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # 1. Создаём пользователя
    created = crud.create_user(db, fio, login, password, role="client")
    if not created:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Логин уже занят"},
            status_code=400,
        )

    # 2. Сразу авторизуем — выдаём JWT
    token = create_access_token({"sub": str(created.id_user), "role": created.role})

    # 3. Кладём токен в cookie и редиректим на главную
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24,  # 1 сутки
        samesite="lax",
    )
    return response


@app.get("/logout", tags=["pages"])
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


# ============================================================
# API — ТОВАРЫ
# ============================================================

@app.get("/api/products", response_model=List[schemas.ProductOut], tags=["products"])
def api_get_products(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any),
):
    """Список всех товаров. Доступно любому авторизованному пользователю."""
    return crud.get_products(db)


@app.get("/api/products/{product_id}", response_model=schemas.ProductOut, tags=["products"])
def api_get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any),
):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product


@app.post("/api/products", response_model=schemas.ProductOut, tags=["products"])
def api_create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_manager),
):
    """Создание товара. Только manager/admin."""
    return crud.create_product(db, product)


@app.put("/api/products/{product_id}", response_model=schemas.ProductOut, tags=["products"])
def api_update_product(
    product_id: int,
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_manager),
):
    """Обновление товара. Только manager/admin."""
    updated = crud.update_product(db, product_id, product)
    if not updated:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return updated


@app.delete("/api/products/{product_id}", tags=["products"])
def api_delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Удаление товара. Только admin."""
    deleted = crud.delete_product(db, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return {"status": "ok", "deleted_id": product_id}


# ============================================================
# API — КЛИЕНТЫ
# ============================================================

@app.get("/api/customers", response_model=List[schemas.CustomerOut], tags=["customers"])
def api_get_customers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_manager),
):
    """Список клиентов. Только manager/admin."""
    return crud.get_customers(db)


@app.post("/api/customers", response_model=schemas.CustomerOut, tags=["customers"])
def api_create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_manager),
):
    return crud.create_customer(db, customer)


# ============================================================
# API — ЗАКАЗЫ
# ============================================================

@app.get("/api/orders", response_model=List[schemas.OrderOut], tags=["orders"])
def api_get_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_manager),
):
    """Все заказы. Только manager/admin."""
    return crud.get_orders(db)


@app.post("/api/orders", response_model=schemas.OrderOut, tags=["orders"])
def api_create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_manager),
):
    return crud.create_order(db, order)


# ============================================================
# API — АНАЛИТИКА
# ============================================================

@app.get("/api/analytics/sales", tags=["analytics"])
def api_sales(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_manager),
):
    """Сумма продаж по товарам. Только manager/admin."""
    return crud.get_sales_summary(db)


# ============================================================
# API — ПОЛЬЗОВАТЕЛИ (только admin)
# ============================================================

@app.get("/api/users", response_model=List[schemas.UserOut], tags=["admin"])
def api_get_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Список всех пользователей. Только admin."""
    return db.query(models.User).all()


# ============================================================
# HTML-СТРАНИЦЫ ПРИЛОЖЕНИЯ
# ============================================================

@app.get("/", response_class=HTMLResponse, tags=["pages"])
def index(
    request: Request,
    welcome: int = 0,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    products = crud.get_products(db)
    if current_user.role in ("manager", "admin"):
        orders = crud.get_orders(db)
    else:
        orders = crud.get_orders_for_user(db, current_user)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products,
        "orders": orders,
        "user": current_user,
        "can_manage": current_user.role in ("manager", "admin"),
        "is_admin": current_user.role == "admin",
        "welcome": bool(welcome),
    })


@app.get("/form", response_class=HTMLResponse, tags=["pages"])
def form_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
):
    """Форма редактирования товаров. Только manager/admin."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Доступ только для менеджеров и админов")

    manufacturers = db.query(models.Manufacturer).all()
    categories = db.query(models.Category).all()
    return templates.TemplateResponse("form.html", {
        "request": request,
        "manufacturers": manufacturers,
        "categories": categories,
        "user": current_user,
    })


@app.get("/admin", response_class=HTMLResponse, tags=["pages"])
def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
):
    """Админ-панель со списком пользователей. Только admin."""
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только для администратора")

    users = db.query(models.User).all()
    products = crud.get_products(db)
    orders = crud.get_orders(db)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products,
        "orders": orders,
        "user": current_user,
        "users": users,
    })


class CartItem(PydanticBaseModel):
    product_id: int
    quantity: int


class CartCheckout(PydanticBaseModel):
    items: list[CartItem]


@app.post("/api/shop/checkout", tags=["shop"])
def api_checkout(
    payload: CartCheckout,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any),
):
    """
    Оформить заказ. Доступно любому авторизованному пользователю.
    Получает список товаров и количество, создаёт заказ и возвращает его.
    """
    if not payload.items:
        raise HTTPException(status_code=400, detail="Корзина пуста")
    items = [{"product_id": i.product_id, "quantity": i.quantity} for i in payload.items]
    order, total = crud.create_order_for_user(db, current_user, items)
    return {
        "order_id": order.id_order,
        "order_number": order.order_number,
        "total": total,
        "status": order.status,
    }


@app.get("/api/shop/my-orders", tags=["shop"])
def api_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any),
):
    """Мои заказы."""
    orders = crud.get_orders_for_user(db, current_user)
    return [
        {
            "id_order": o.id_order,
            "order_number": o.order_number,
            "order_date": o.order_date,
            "status": o.status,
        }
        for o in orders
    ]