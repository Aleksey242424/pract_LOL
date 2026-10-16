# main.py
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from fastapi import (
    FastAPI, Request, Depends, Form, HTTPException,
)
from fastapi.responses import (
    HTMLResponse, RedirectResponse, JSONResponse,
)
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User, Product, Category, Manufacturer,
    WarehouseStock, Customer, Order, OrderItem,
)
from schemas import UserRegister
from auth import (
    get_current_user, require_admin, authenticate_user,
    hash_password, create_access_token, decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from captcha_service import generate_captcha, verify_captcha
from cart import (
    get_cart, save_cart, cart_count,
    get_product_stock, build_cart_items,
)

# -----------------------------------------------------------------
# ВАЖНО: сюда впиши значение статуса, которое РАЗРЕШЕНО в БД.
# Узнать можно так (в psql):
#     SELECT DISTINCT status FROM orders;
# Например, если в БД уже есть 'pending' — пиши "pending".
# -----------------------------------------------------------------
ORDER_STATUS_NEW = "new"

app = FastAPI(title="Guitar Store")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------
# Универсальный рендер + отладка
# ---------------------------------------------------------------
def render(template_name, request, db, status_code=200, **extra):
    token = request.cookies.get("access_token")
    print(f"\n=== RENDER {template_name} ===")
    print("cookie access_token present:", bool(token))

    current_user = None
    if token:
        payload = decode_token(token)
        print("decoded payload:", payload)
        if payload:
            sub = payload.get("sub")
            print("sub from token:", sub, type(sub).__name__)
            try:
                sub_int = int(sub)
            except (TypeError, ValueError):
                print("!!! SUB is not int-convertible")
                sub_int = None
            if sub_int is not None:
                current_user = (
                    db.query(User).filter(User.id_user == sub_int).first()
                )
            print("current_user found:", bool(current_user))
            if current_user:
                print("current_user.id_user:", current_user.id_user,
                      "login:", current_user.login,
                      "role:", current_user.role)
    print("=== END RENDER ===\n")

    context = {
        "request": request,
        "current_user": current_user,
        "cart_count": cart_count(request),
    }
    context.update(extra)
    return templates.TemplateResponse(
        template_name, context, status_code=status_code
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(x) for x in err["loc"] if x != "body")
        errors.append({"field": field, "message": err["msg"]})
    return JSONResponse(
        status_code=422,
        content={"detail": "Ошибка валидации", "errors": errors},
    )


# ---------------------------------------------------------------
# CAPTCHA
# ---------------------------------------------------------------
@app.get("/api/captcha/challenge", tags=["captcha"])
def captcha_challenge():
    return generate_captcha()


# ---------------------------------------------------------------
# ЛОГИН / РЕГИСТРАЦИЯ / ВЫХОД
# ---------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse, tags=["pages"])
def login_page(request: Request, db: Session = Depends(get_db)):
    return render("login.html", request, db)


@app.post("/login", tags=["auth"])
def login_submit(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    captcha_id: str = Form(...),
    captcha_x: int = Form(...),
    db: Session = Depends(get_db),
):
    print(f"\n=== LOGIN ATTEMPT: login={login!r} captcha_x={captcha_x} ===")

    if not verify_captcha(captcha_id, captcha_x):
        print("!!! CAPTCHA FAILED")
        return render(
            "login.html", request, db,
            status_code=400, error="CAPTCHA не пройдена",
        )
    print("CAPTCHA passed")

    try:
        user = authenticate_user(db, login, password)
    except HTTPException as e:
        print(f"!!! AUTH EXCEPTION: {e.detail}")
        return render(
            "login.html", request, db,
            status_code=e.status_code, error=e.detail,
        )

    if not user:
        print("!!! USER NOT FOUND or password wrong")
        return render(
            "login.html", request, db,
            status_code=401, error="Неверный логин или пароль",
        )

    print(f"USER OK: id_user={user.id_user} role={user.role}")

    token = create_access_token({"sub": str(user.id_user), "role": user.role})
    print(f"TOKEN CREATED: {token[:50]}...")

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "access_token", token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    print("COOKIE SET, redirecting to /")
    print("=== END LOGIN ===\n")
    return response


@app.get("/register", response_class=HTMLResponse, tags=["pages"])
def register_page(request: Request, db: Session = Depends(get_db)):
    return render("register.html", request, db)


@app.post("/register", tags=["auth"])
def register_submit(
    request: Request,
    fio: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        schema = UserRegister(fio=fio, login=login, password=password)
    except Exception as e:
        return render(
            "register.html", request, db,
            status_code=400, error=str(e),
        )

    if db.query(User).filter(User.login == schema.login).first():
        return render(
            "register.html", request, db,
            status_code=400, error="Логин уже занят",
        )

    user = User(
        fio=schema.fio,
        login=schema.login,
        password_hash=hash_password(schema.password),
        role=schema.role,
    )
    db.add(user)
    db.flush()

    db.add(Customer(fio=schema.fio, user_id=user.id_user))
    db.commit()
    return RedirectResponse("/login", status_code=303)


@app.get("/logout", tags=["auth"])
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response


# ---------------------------------------------------------------
# ГЛАВНАЯ
# ---------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, tags=["pages"])
def home(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.id_product).all()
    stocks = {p.id_product: get_product_stock(db, p.id_product) for p in products}
    return render("index.html", request, db, products=products, stocks=stocks)


# ---------------------------------------------------------------
# КОРЗИНА
# ---------------------------------------------------------------
@app.get("/cart", response_class=HTMLResponse, tags=["cart"])
def cart_page(request: Request, db: Session = Depends(get_db)):
    cart = get_cart(request)
    items, total = build_cart_items(db, cart)
    return render("cart.html", request, db, items=items, total=total)


@app.post("/cart/add/{product_id}", tags=["cart"])
def cart_add(product_id: int, request: Request, quantity: int = Form(1)):
    cart = get_cart(request)
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    response = RedirectResponse("/cart", status_code=303)
    save_cart(response, cart)
    return response


@app.post("/cart/remove/{product_id}", tags=["cart"])
def cart_remove(product_id: int, request: Request):
    cart = get_cart(request)
    cart.pop(str(product_id), None)
    response = RedirectResponse("/cart", status_code=303)
    save_cart(response, cart)
    return response


@app.post("/checkout", tags=["cart"])
def checkout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse("/login", status_code=303)

    cart = get_cart(request)
    if not cart:
        return RedirectResponse("/cart", status_code=303)

    customer = (
        db.query(Customer)
        .filter(Customer.user_id == current_user.id_user)
        .first()
    )
    if not customer:
        customer = Customer(fio=current_user.fio, user_id=current_user.id_user)
        db.add(customer)
        db.flush()

    order = Order(
        order_number=f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        customer_id=customer.id_customer,
        status=ORDER_STATUS_NEW,   # ← значение из константы вверху файла
    )
    db.add(order)
    db.flush()

    for pid, qty in cart.items():
        product = (
            db.query(Product).filter(Product.id_product == int(pid)).first()
        )
        if not product:
            continue

        rows = (
            db.query(WarehouseStock)
            .filter(WarehouseStock.product_id == product.id_product)
            .order_by(WarehouseStock.quantity.desc())
            .all()
        )
        available = sum(r.quantity for r in rows)
        if available < qty:
            raise HTTPException(400, f"Недостаточно товара: {product.name}")

        remaining = qty
        for row in rows:
            if remaining <= 0:
                break
            take = min(row.quantity, remaining)
            row.quantity -= take
            remaining -= take

        db.add(OrderItem(
            order_id=order.id_order,
            product_id=product.id_product,
            quantity=qty,
            price=product.price,
        ))

    db.commit()
    response = RedirectResponse(f"/orders/{order.id_order}", status_code=303)
    response.delete_cookie("cart")
    return response


@app.get("/orders/{order_id}", response_class=HTMLResponse, tags=["pages"])
def order_page(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id_order == order_id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    products = {p.id_product: p for p in db.query(Product).all()}
    total = sum((i.price * i.quantity for i in items), Decimal("0"))
    return render(
        "order.html", request, db,
        order=order, items=items, products=products, total=total,
    )


# ---------------------------------------------------------------
# УПРАВЛЕНИЕ ТОВАРАМИ
# ---------------------------------------------------------------
@app.get("/admin/products", response_class=HTMLResponse, tags=["admin"])
def admin_products_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    products = db.query(Product).order_by(Product.id_product).all()
    categories = db.query(Category).order_by(Category.name).all()
    manufacturers = db.query(Manufacturer).order_by(Manufacturer.name).all()
    stocks = {p.id_product: get_product_stock(db, p.id_product) for p in products}
    return render(
        "admin/products.html", request, db,
        products=products,
        categories=categories,
        manufacturers=manufacturers,
        stocks=stocks,
    )


@app.post("/admin/products", tags=["admin"])
def admin_product_create(
    article: str = Form(...),
    name: str = Form(...),
    price: Decimal = Form(...),
    manufacturer_id: int = Form(...),
    category_id: int = Form(...),
    material: str = Form(""),
    pickup_type: str = Form(""),
    strings_count: Optional[int] = Form(None),
    fret_count: Optional[int] = Form(None),
    color: str = Form(""),
    initial_stock: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    product = Product(
        article=article, name=name, price=price,
        manufacturer_id=manufacturer_id, category_id=category_id,
        material=material or None, pickup_type=pickup_type or None,
        strings_count=strings_count, fret_count=fret_count,
        color=color or None,
    )
    db.add(product)
    db.flush()

    first_warehouse = db.query(WarehouseStock).first()
    warehouse_id = first_warehouse.warehouse_id if first_warehouse else 1
    db.add(WarehouseStock(
        warehouse_id=warehouse_id,
        product_id=product.id_product,
        quantity=initial_stock,
    ))
    db.commit()
    return RedirectResponse("/admin/products", status_code=303)


@app.post("/admin/products/{product_id}/delete", tags=["admin"])
def admin_product_delete(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    db.query(WarehouseStock).filter(
        WarehouseStock.product_id == product_id
    ).delete()
    db.query(OrderItem).filter(OrderItem.product_id == product_id).delete()
    product = db.query(Product).filter(Product.id_product == product_id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse("/admin/products", status_code=303)


# ---------------------------------------------------------------
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ---------------------------------------------------------------
@app.get("/admin/users", response_class=HTMLResponse, tags=["admin"])
def admin_users_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.id_user).all()
    return render("admin/users.html", request, db, users=users)


@app.post("/admin/users/{user_id}/update", tags=["admin"])
def admin_user_update(
    user_id: int,
    fio: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id_user == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.fio = fio
    user.role = role
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/unlock", tags=["admin"])
def admin_user_unlock(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id_user == user_id).first()
    if user:
        user.locked_until = None
        user.failed_attempts = 0
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/delete", tags=["admin"])
def admin_user_delete(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id_user == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


# ---------------------------------------------------------------
# ЗАПУСК
# ---------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)