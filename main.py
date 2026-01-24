"""
Запускает основную функцию бота.
Просто вызывает главную функцию из bot/main.py

"""
from bot.main import main
import asyncio

# import os
# import sys
  
# Выводим информацию о системе для отладки
# print("=" * 50)
# print("Системная информация:")
# print(f"Python: {sys.version}")
# print(f"Рабочая директория: {os.getcwd()}")
# print(f"PATH: {os.environ.get('PATH', '')}")
# print(f"Содержимое /usr/local/bin/:")
# try:
#     print(os.listdir('/usr/local/bin/'))
# except:
#     print("Не удалось прочитать директорию")
# print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())