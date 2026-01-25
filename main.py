"""
Запускает основную функцию бота.
Просто вызывает главную функцию из bot/main.py
Также запускает веб-приложение

"""
from flask import Flask, render_template, send_from_directory
import asyncio
import multiprocessing
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализируем веб-приложение
app = Flask(__name__, template_folder="src/templates")  

def run_bot():
    """Запускает бота в отдельном потоке"""
    import asyncio
    from bot.main import main as bot_main

    # Создаем новую event loop для процесса
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(bot_main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        loop.close()

@app.route("/")  
def web():  
    return render_template('index.html')  

@app.route('/styles/<path:filename>')
def serve_styles(filename):
    """Обслуживает стили из src/styles"""
    return send_from_directory("src/styles", filename)

def run_webapp():
    """Запускает Flask"""
    logger.info("Запуск Flask веб-сервера...")
    #app.run(host="0.0.0.0", port=80, debug=False)
    app.run(host="localhost", port=5000, debug=True, use_reloader=False)

if __name__ == "__main__":
    bot_process = multiprocessing.Process(target=run_bot, daemon=True)
    bot_process.start()
    logger.info(f"Бот запущен в процессе PID: {bot_process.pid}")
    
    run_webapp()