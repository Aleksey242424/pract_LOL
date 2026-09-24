from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Строка подключения под твою БД
# Формат: postgresql://ПОЛЬЗОВАТЕЛЬ:ПАРОЛЬ@ХОСТ:ПОРТ/БАЗА
DATABASE_URL = "postgresql://postgres:123@localhost:5432/guitar_store"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Зависимость FastAPI: выдаёт сессию и закрывает её после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()