"""
Запускает основную функцию бота.
Просто вызывает главную функцию из bot/main.py

"""
from bot.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())