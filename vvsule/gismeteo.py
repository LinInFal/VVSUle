"""
(Не рабочий)
Получает погоду во Владивостоке с помощью Gismeteo API

"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import aiopygismeteo

class GismeteoWeather:
    """Класс для работы с погодой через aiopygismeteo"""
    
    def __init__(self):
        self.api_token = None
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
        pass
    

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
        pass
    

    def _get_weather_icon(self, description: str) -> str:
        """Получает emoji иконку погоды по описанию"""
        pass

    
    def _get_condition_code(self, description: str) -> int:
        """Получает код состояния погоды для демо-данных"""
        pass
    

    def _get_wind_direction_symbol(self, direction_code: str) -> str:
        """Конвертирует код направления ветра в символ"""
        pass
    

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