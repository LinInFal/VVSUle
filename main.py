"""
Запускает основную функцию бота.
Просто вызывает главную функцию из vvsule/main.py
Также запускает веб-приложение

"""
from flask import Flask, render_template, send_from_directory, jsonify, request
import asyncio
import threading
import logging
import sys
import os
import json
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from vvsule.database.models import ScheduleCache
from vvsule.parser import parse_vvsu_timetable
from vvsule.gismeteo import get_weekly_weather_sync
from config import config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)

# Инициализируем веб-приложение
app = Flask(__name__, template_folder="vvsule/src/templates")  

# Используем ту же конфигурацию БД
db_url = config.db.url.replace('+asyncpg', '+psycopg2')

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

DB_AVAILABLE = True
PARSER_AVAILABLE = True

# Импортируем парсер
try:
    from vvsule.parser import parse_vvsu_timetable
    PARSER_AVAILABLE = True
except ImportError as e:
    logging.error(f"Не удалось импортировать парсер: {e}")
    PARSER_AVAILABLE = False


def get_cached_schedule(group_name: str):
    """Получение кэшированного расписания из БД"""
    if not DB_AVAILABLE:
        return None
    
    session = SessionLocal()
    normalized_group = group_name.upper()
    try:
        # Ищем кэш в БД
        cache = session.query(ScheduleCache).filter(
            ScheduleCache.group_name == normalized_group,
            ScheduleCache.week_type == "all_weeks"
        ).first()
        
        if cache:
            # Проверяем, не устарели ли данные
            time_diff = datetime.utcnow() - cache.last_updated
            if time_diff.total_seconds() < 21600:  # 6 часов
                try:
                    data = json.loads(cache.schedule_data)
                    logging.info(f"Загружен кэш для {normalized_group}: {len(data.get('weeks', []))} недель")
                    return data
                except Exception as e:
                    logging.error(f"Ошибка при загрузке кэша: {e}")
        
        logging.info(f"Кэш для {normalized_group} не найден или устарел")
        return None
        
    except Exception as e:
        logging.error(f"Ошибка при получении кэша: {e}")
        return None
    finally:
        session.close()


def save_schedule_cache(group_name: str, schedule_data: dict):
    """Сохранение расписания в кэш (синхронная версия)"""
    if not DB_AVAILABLE:
        return
    
    session = SessionLocal()
    normalized_group = group_name.upper()
    try:
        # Ищем существующий кэш
        cache = session.query(ScheduleCache).filter(
            ScheduleCache.group_name == normalized_group,
            ScheduleCache.week_type == "all_weeks"
        ).first()
        
        if cache:
            cache.schedule_data = json.dumps(schedule_data, ensure_ascii=False)
            cache.last_updated = datetime.utcnow()
            logging.info(f"Обновлен кэш для {normalized_group}")
        else:
            cache = ScheduleCache(
                group_name=normalized_group,
                week_type="all_weeks",
                schedule_data=json.dumps(schedule_data, ensure_ascii=False)
            )
            session.add(cache)
            logging.info(f"Создан новый кэш для {normalized_group}")
        
        session.commit()
        logging.info(f"Кэш сохранен для {normalized_group}")
        
    except Exception as e:
        logging.error(f"Ошибка при сохранении кэша: {e}")
        session.rollback()
    finally:
        session.close()


def run_bot():
    """Запускает бота в отдельном потоке"""
    import asyncio
    from vvsule.main import main as bot_main

    # Создаем новую event loop для процесса
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(bot_main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
    finally:
        loop.close()


def run_webapp():
    """Запускает Flask"""
    # app.run(host="0.0.0.0", port=80, debug=False)
    app.run(host="localhost", port=5000, debug=True, use_reloader=False)


@app.route("/")  
def web():  
    return render_template('index.html')  


@app.route('/styles/<path:filename>')
def serve_styles(filename):
    """Обслуживает стили из vvsule/src/styles"""
    return send_from_directory("vvsule/src/styles", filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    """Обслуживает JavaScript файлы из vvsule/src/js"""
    return send_from_directory("vvsule/src/js", filename)


@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    """API endpoint для получения расписания"""
    group_name = request.args.get('group', '').strip()
    normalized_group = group_name.upper()
    
    if not normalized_group:
        return jsonify({
            'success': False,
            'message': 'Не указана группа'
        })

    # Проверяем кэш
    cached_data = get_cached_schedule(normalized_group)
    
    if cached_data:
        return jsonify({
            'success': True,
            'schedule': cached_data,
            'group': normalized_group,
            'weeks_count': len(cached_data.get('weeks', [])),
            'source': 'cache'
        })

    if not PARSER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Парсер недоступен',
            'source': 'error'
        })
    
    try:
        # Используем существующую функцию парсинга
        schedule_data = parse_vvsu_timetable(normalized_group)
        
        if schedule_data and schedule_data.get('success'):
            # Сохраняем в кэш
            save_schedule_cache(normalized_group, schedule_data)

            weeks = schedule_data.get('weeks', [])

            return jsonify({
                'success': True,
                'schedule': schedule_data,
                'group': normalized_group,
                'weeks_count': len(weeks),
                'source': 'parser'
            })
        else:
            error_msg = schedule_data.get('error', 'Неизвестная ошибка') if schedule_data else 'Ошибка парсинга'
            logging.error(f"Ошибка парсинга: {error_msg}")

            return jsonify({
                'success': False,
                'message': f'Ошибка при загрузке расписания: {error_msg}',
                'source': 'error'
            })
            
            
    except Exception as e:
        logging.error(f"Ошибка парсинга в веб-приложении: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Ошибка при загрузке расписания: {str(e)}'
        })


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Статистика кэша"""
    if not DB_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'База данных недоступна'
        })
    
    session = SessionLocal()
    normalized_group = group_name.upper()
    try:
        total_cache = session.query(ScheduleCache).count()
        
        # Группы в кэше
        groups = session.query(ScheduleCache.normalized_group).distinct().all()
        groups_list = [g[0] for g in groups]
        
        return jsonify({
            'success': True,
            'total_cached_groups': total_cache,
            'cached_groups': groups_list,
            'db_available': DB_AVAILABLE
        })
    except Exception as e:
        logging.error(f"Ошибка при получении статистики кэша: {e}")
        return jsonify({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        })
    finally:
        session.close()


@app.route('/api/weather', methods=['GET'])
def get_weather():
    """API endpoint для получения погоды во Владивостоке"""
    try:
        weather_data = get_weekly_weather_sync()
        return jsonify(weather_data)
    except Exception as e:
        logging.error(f"Ошибка при получении погоды: {e}")
        return jsonify({
            'success': False,
            'message': f'Ошибка при загрузке погоды: {str(e)}'
        })


if __name__ == "__main__":
    web_thread = threading.Thread(target=run_webapp, daemon=True)
    web_thread.start()
    
    run_bot()