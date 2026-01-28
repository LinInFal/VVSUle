"""
Настраивает подключение к PostgreSQL через SQLAlchemy.
Создает движок и сессии для работы с базой.

"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from config import config
from .models import Base
import logging


class Database:
    def __init__(self):
        # Для PostgreSQL используем asyncpg
        self.engine = create_async_engine(
            config.db.url,
            echo=config.debug,
            future=True,
            pool_size=20,
            max_overflow=40
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    

    async def create_tables(self):
        """Создание таблиц в БД"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logging.info("✅ Таблицы созданы успешно")
        except Exception as e:
            logging.error(f"❌ Ошибка при создании таблиц: {e}")
            raise
    

    async def get_session(self) -> AsyncSession:
        """Получение сессии"""
        async with self.async_session() as session:
            try:
                yield session
            finally:
                await session.close()


# Создаем глобальный объект БД
database = Database()