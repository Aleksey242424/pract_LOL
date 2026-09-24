"""
Скрипт для создания первого администратора.
Запуск: python init_admin.py
"""
from database import SessionLocal
import crud

db = SessionLocal()

print("Создание первого администратора...")
user = crud.create_user(
    db,
    fio="Главный Администратор",
    login="admin",
    password="admin123",   # ← смени после первого входа!
    role="admin",
)
if user:
    print(f"✅ Админ создан: login=admin, password=admin123")
else:
    print("⚠️ Пользователь с логином 'admin' уже существует")
db.close()