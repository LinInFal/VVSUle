"""
Инициализирует бота, диспетчер, подключает роутеры.
Запускает polling для получения сообщений от Telegram.

"""
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import asyncio
import logging
from config import config
from vvsule.database.database import database

# Импортируем роутеры
from vvsule.handlers.start import router as start_router
from vvsule.handlers.schedule import router as schedule_router


logging.basicConfig(
    level=config.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    """Основная функция запуска бота"""

    # Создаем таблицы в БД
    await database.create_tables()
    logging.info("База данных инициализирована")

    # Инициализируем бота и диспетчер
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем роутеры
    dp.include_router(start_router)
    dp.include_router(schedule_router)

    # Запускаем бота
    logging.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())