"""
Получает погоду во Владивостоке с помощью Gismeteo API

"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import aiopygismeteo
import os
from dotenv import load_dotenv


# Загружаем переменные окружения
load_dotenv()


class GismeteoWeather:
    """Класс для работы с погодой через aiopygismeteo"""
    
    def __init__(self):
        self.api_token = os.getenv("GISMETEO_API_TOKEN")
        
        if not self.api_token:
            logging.warning("GISMETEO_API_TOKEN не найден в .env файле")
            logging.warning("Будет использоваться демо-режим")
            self.api_token = None
        else:
            self.gism = aiopygismeteo.Gismeteo(token=self.api_token)

        self.city_name = "Владивосток"
        self.city_id = None  # Будет определен при первом запросе
        self.weather_smiles = {
            'ясно': '☀️',
            'малооблачно': '🌤️', 
            'облачно': '☁️',
            'пасмурно': '☁️',
            'переменная облачность': '⛅',
            'дождь': '🌧️',
            'снег': '❄️',
            'ливень': '🌦️',
            'гроза': '⛈️',
            'туман': '🌫️',
            'дымка': '🌫️',
            'метель': '🌨️',
            'шторм': '🌪️',
        }
    

    async def _get_city_id(self) -> int:
        """Получает ID города Владивосток"""
        if self.city_id:
            return self.city_id

        if not self.gism:
            return None
        
        try:
            search_results = await self.gism.search.by_query(self.city_name)
            if search_results:
                self.city_id = search_results[0].id
                logging.info(f"Найден ID города {self.city_name}: {self.city_id}")
                return self.city_id
            else:
                logging.error(f"Город {self.city_name} не найден")
                return None
        except Exception as e:
            logging.error(f"Ошибка поиска города: {e}")
            return None
    

    async def get_weekly_weather(self) -> Dict:
        """
        Получает погоду на неделю для Владивостока
        
        Returns:
            Dict: Словарь с данными о погоде или тестовыми данными
        """
        # Если нет токена, используем демо-данные
        if not self.api_token or not self.gism:
            logging.info("Используются демо-данные")
            return self._get_demo_data()

        try:
            # Получаем ID города
            city_id = await self._get_city_id()
            if not city_id:
                return self._get_demo_data()
            
            # Получаем прогноз на 7 дней
            days = 7
            data = await self.gism.step3.by_id(city_id, days=days)
            
            if not data:
                return self._get_demo_data()
            
            return await self._parse_weather_data(data)
                
        except Exception as e:
            logging.error(f"Ошибка получения погоды: {e}")
            return self._get_demo_data()
    

    async def _parse_weather_data(self, data: List) -> Dict:
        """Парсит данные от API в удобный формат"""
        try:
            weekly_forecast = []
            
            for i, day_data in enumerate(data):
                if i >= 7:  # Ограничиваем 7 днями
                    break
                
                # Дата
                date_str = day_data.date.local
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                
                # Температура
                temperature = day_data.temperature.air.c
                
                # Влажность
                humidity = day_data.humidity.percent
                
                # Ветер
                wind_speed = day_data.wind.speed.m_s
                wind_direction_code = day_data.wind.direction.scale_8
                wind_direction = self._get_wind_direction_symbol(wind_direction_code)
                
                # Осадки
                precipitation = day_data.precipitation.amount
                
                # Погодные условия
                description = day_data.description.full.lower()
                condition_icon = self._get_weather_icon(description)
                condition_text = day_data.description.full
                
                # День недели на русском
                weekday_ru = self._get_russian_weekday(date_obj.weekday())
                # Дата в формате "22 января"
                day_month = f"{date_obj.day} {self._get_russian_month(date_obj.month)}"
                
                weekly_forecast.append({
                    "date": date_str,
                    "date_display": f"{weekday_ru}, {day_month}",
                    "date_obj": date_obj.isoformat(),
                    "day_of_week": weekday_ru,
                    "day": date_obj.day,
                    "month": self._get_russian_month(date_obj.month),
                    "temperature": round(temperature),
                    "humidity": humidity,
                    "wind_speed": round(wind_speed),
                    "wind_direction": wind_direction,
                    "precipitation": precipitation,
                    "condition_icon": condition_icon,
                    "condition_text": condition_text,
                    "condition_code": self._get_condition_code(description)
                })
            
            return {
                "success": True,
                "city": "Владивосток",
                "updated_at": datetime.now().isoformat(),
                "forecast": weekly_forecast,
                "source": "gismeteo"
            }
            
        except Exception as e:
            logging.error(f"Ошибка парсинга данных погоды: {e}")
            return self._get_demo_data()
    

    def _get_weather_icon(self, description: str) -> str:
        """Получает emoji иконку погоды по описанию"""
        description_lower = description.lower()
        
        for key, icon in self.weather_smiles.items():
            if key in description_lower:
                return icon

    
    def _get_condition_code(self, description: str) -> int:
        """Получает код состояния погоды для демо-данных"""
        description_lower = description.lower()
        
        if 'ясн' in description_lower:
            return 1
        elif 'малооблач' in description_lower:
            return 2
        elif 'переменная' in description_lower:
            return 3
        elif 'обл' in description_lower or 'пас' in description_lower:
            return 4
        elif 'дож' in description_lower:
            return 5
        elif 'лив' in description_lower:
            return 6
        elif 'гроз' in description_lower:
            return 7
        elif 'сне' in description_lower:
            return 8
        elif 'тум' in description_lower or 'дым' in description_lower:
            return 9
        else:
            return 1
    

    def _get_wind_direction_symbol(self, direction_code: str) -> str:
        """Конвертирует код направления ветра в символ"""
        directions = {
            "n": "С",      # Север
            "nne": "ССВ",  # Северо-северо-восток
            "ne": "СВ",    # Северо-восток
            "ene": "ВСВ",  # Восток-северо-восток
            "e": "В",      # Восток
            "ese": "ВЮВ",  # Восток-юго-восток
            "se": "ЮВ",    # Юго-восток
            "sse": "ЮЮВ",  # Юго-юго-восток
            "s": "Ю",      # Юг
            "ssw": "ЮЮЗ",  # Юго-юго-запад
            "sw": "ЮЗ",    # Юго-запад
            "wsw": "ЗЮЗ",  # Запад-юго-запад
            "w": "З",      # Запад
            "wnw": "ЗСЗ",  # Запад-северо-запад
            "nw": "СЗ",    # Северо-запад
            "nnw": "ССЗ",  # Северо-северо-запад
        }
        return directions.get(direction_code.lower(), "")
    

    def _get_russian_weekday(self, weekday: int) -> str:
        """Возвращает русское название дня недели"""
        weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        return weekdays[weekday]
    

    def _get_russian_month(self, month: int) -> str:
        """Возвращает русское название месяца"""
        months = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        return months[month - 1]
    
    
    def _get_demo_data(self) -> Dict:
        """Возвращает демо-данные для тестирования"""
        today = datetime.now()
        weekly_forecast = []
        
        for i in range(7):
            date = today + timedelta(days=i)
            weekday_ru = self._get_russian_weekday(date.weekday())
            day_month = f"{date.day} {self._get_russian_month(date.month)}"
            
            # Генерация случайных, но реалистичных данных
            import random
            temp = random.randint(-15, -5)
            humidity = random.randint(40, 80)
            wind_speed = random.randint(2, 10)
            wind_dirs = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
            wind_dir = random.choice(wind_dirs)
            precipitation = random.randint(0, 5)
            
            # Выбираем случайное состояние погоды
            conditions = list(self.weather_smiles.keys())
            condition = random.choice(conditions)
            condition_icon = self.weather_smiles[condition]
            
            weekly_forecast.append({
                "date": date.isoformat(),
                "date_display": f"{weekday_ru}, {day_month}",
                "date_obj": date.isoformat(),
                "day_of_week": weekday_ru,
                "day": date.day,
                "month": self._get_russian_month(date.month),
                "temperature": temp,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "wind_direction": wind_dir,
                "precipitation": precipitation,
                "condition_icon": condition_icon,
                "condition_text": condition.capitalize(),
                "condition_code": self._get_condition_code(condition)
            })
        
        return {
            "success": True,
            "city": "Владивосток",
            "updated_at": datetime.now().isoformat(),
            "forecast": weekly_forecast,
            "source": "demo",
            "note": "Демо-данные. Для реальных данных убедитесь, что aiopygismeteo работает корректно."
        }


# Создаем глобальный экземпляр
weather_client = GismeteoWeather()

# Синхронная обертка для использования в Flask
def get_weekly_weather_sync() -> Dict:
    """Синхронная обертка для получения погоды"""
    try:
        # Создаем новую event loop для синхронного вызова
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(weather_client.get_weekly_weather())
        loop.close()
        return result
    except Exception as e:
        logging.error(f"Ошибка в синхронной обертке: {e}")
        return weather_client._get_demo_data()