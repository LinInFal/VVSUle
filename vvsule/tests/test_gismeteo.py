"""
Тесты для модуля погоды vvsule/gismeteo.py

"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from vvsule.gismeteo import GismeteoWeather, get_weekly_weather_sync, weather_client


class TestGismeteoWeather:
    """Тесты для класса GismeteoWeather"""
    
    def test_init_without_api_token(self):
        """Тест инициализации без API токена"""
        # Arrange & Act
        with patch('vvsule.gismeteo.os.getenv', return_value=None):
            with patch('vvsule.gismeteo.aiopygismeteo.Gismeteo') as mock_gism_class:
                weather = GismeteoWeather()
            
        # Assert
        assert weather.api_token is None
        mock_gism_class.assert_not_called()

        
    @patch('vvsule.gismeteo.aiopygismeteo.Gismeteo')
    def test_init_with_api_token(self, mock_gismeteo_class):
        """Тест инициализации с API токеном"""
        # Arrange
        mock_gismeteo_instance = Mock()
        mock_gismeteo_class.return_value = mock_gismeteo_instance
        
        # Act
        with patch('vvsule.gismeteo.os.getenv', return_value="test-token-123"):
            weather = GismeteoWeather()
            
        # Assert
        assert weather.api_token == "test-token-123"
        assert weather.gism is not None
        
    @pytest.mark.asyncio
    async def test_get_city_id_success(self):
        """Тест успешного получения ID города"""
        # Arrange
        weather = GismeteoWeather()
        weather.gism = AsyncMock()
        
        mock_search_result = Mock()
        mock_search_result.id = 12345
        weather.gism.search.by_query = AsyncMock(return_value=[mock_search_result])
        
        # Act
        city_id = await weather._get_city_id()
        
        # Assert
        assert city_id == 12345
        assert weather.city_id == 12345
        weather.gism.search.by_query.assert_called_once_with("Владивосток")
        
    @pytest.mark.asyncio
    async def test_get_city_id_not_found(self):
        """Тест ситуации, когда город не найден"""
        # Arrange
        weather = GismeteoWeather()
        weather.gism = AsyncMock()
        weather.gism.search.by_query = AsyncMock(return_value=[])
        
        # Act
        city_id = await weather._get_city_id()
        
        # Assert
        assert city_id is None
        
    @pytest.mark.asyncio
    async def test_get_weekly_weather_demo_mode(self):
        """Тест получения погоды в демо-режиме (без токена)"""
        # Arrange
        weather = GismeteoWeather()
        weather.api_token = None  # Нет токена = демо-режим
        
        # Act
        result = await weather.get_weekly_weather()
        
        # Assert
        assert result['success'] is True
        assert result['city'] == "Владивосток"
        assert result['source'] == "demo"
        assert 'forecast' in result
        assert len(result['forecast']) == 7
        
        # Проверяем структуру данных
        day_forecast = result['forecast'][0]
        assert 'date' in day_forecast
        assert 'date_display' in day_forecast
        assert 'temperature' in day_forecast
        assert 'humidity' in day_forecast
        assert 'wind_speed' in day_forecast
        assert 'condition_icon' in day_forecast
        
    @pytest.mark.asyncio
    async def test_get_weekly_weather_with_api(self):
        """Тест получения погоды через API"""
        # Arrange
        weather = GismeteoWeather()
        weather.api_token = "test-token"
        weather.gism = AsyncMock()
        
        # Мокаем получение ID города
        weather._get_city_id = AsyncMock(return_value=12345)
        
        # Мокаем данные погоды
        mock_day_data = Mock()
        mock_day_data.date.local = "2024-01-01T00:00:00Z"
        mock_day_data.temperature.air.c = -5.5
        mock_day_data.humidity.percent = 75
        mock_day_data.wind.speed.m_s = 3.2
        mock_day_data.wind.direction.scale_8 = "n"
        mock_day_data.precipitation.amount = 0.5
        mock_day_data.description.full = "Ясно"
        
        weather.gism.step3.by_id = AsyncMock(return_value=[mock_day_data] * 3)
        
        # Act
        result = await weather.get_weekly_weather()
        
        # Assert
        assert result['success'] is True
        assert result['city'] == "Владивосток"
        assert result['source'] == "gismeteo"
        assert len(result['forecast']) == 3
        
    @pytest.mark.asyncio
    async def test_get_weekly_weather_api_failure(self):
        """Тест получения погоды при ошибке API"""
        # Arrange
        weather = GismeteoWeather()
        weather.api_token = "test-token"
        weather.gism = AsyncMock()
        
        # Мокаем ошибку при получении города
        weather._get_city_id = AsyncMock(return_value=None)
        
        # Act
        result = await weather.get_weekly_weather()
        
        # Assert
        assert result['success'] is True  # Демо-данные всегда успешны
        assert result['source'] == "demo"
        
    def test_get_weather_icon(self):
        """Тест получения иконки погоды по описанию"""
        # Arrange
        weather = GismeteoWeather()
        
        # Act & Assert
        assert weather._get_weather_icon("ясно") == '☀️'
        assert weather._get_weather_icon("малооблачно") == '🌤️'
        assert weather._get_weather_icon("дождь") == '🌧️'
        assert weather._get_weather_icon("неизвестное состояние") is None
        
    def test_get_wind_direction_symbol(self):
        """Тест преобразования кода направления ветра"""
        # Arrange
        weather = GismeteoWeather()
        
        # Act & Assert
        assert weather._get_wind_direction_symbol("n") == "С"
        assert weather._get_wind_direction_symbol("e") == "В"
        assert weather._get_wind_direction_symbol("s") == "Ю"
        assert weather._get_wind_direction_symbol("w") == "З"
        assert weather._get_wind_direction_symbol("unknown") == ""
        
    def test_get_russian_weekday(self):
        """Тест получения русского названия дня недели"""
        # Arrange
        weather = GismeteoWeather()
        
        # Act & Assert
        assert weather._get_russian_weekday(0) == "Понедельник"
        assert weather._get_russian_weekday(3) == "Четверг"
        assert weather._get_russian_weekday(6) == "Воскресенье"
        
    def test_get_russian_month(self):
        """Тест получения русского названия месяца"""
        # Arrange
        weather = GismeteoWeather()
        
        # Act & Assert
        assert weather._get_russian_month(1) == "января"
        assert weather._get_russian_month(5) == "мая"
        assert weather._get_russian_month(12) == "декабря"
        
    def test_get_demo_data(self):
        """Тест генерации демо-данных"""
        # Arrange
        weather = GismeteoWeather()
        
        # Act
        result = weather._get_demo_data()
        
        # Assert
        assert result['success'] is True
        assert result['city'] == "Владивосток"
        assert result['source'] == "demo"
        assert 'forecast' in result
        assert len(result['forecast']) == 7
        assert 'note' in result
        
        # Проверяем структуру демо-данных
        forecast_day = result['forecast'][0]
        expected_keys = ['date', 'date_display', 'date_obj', 'day_of_week', 
                        'day', 'month', 'temperature', 'humidity', 
                        'wind_speed', 'wind_direction', 'precipitation',
                        'condition_icon', 'condition_text', 'condition_code']
        
        for key in expected_keys:
            assert key in forecast_day
            
    def test_get_weekly_weather_sync(self):
        """Тест синхронной обертки для получения погоды"""
        # Arrange
        expected_result = {
            'success': True,
            'city': 'Владивосток',
            'source': 'demo'
        }
        
        with patch.object(weather_client, 'get_weekly_weather', 
                         AsyncMock(return_value=expected_result)):
            # Act
            result = get_weekly_weather_sync()
            
            # Assert
            assert result == expected_result
            
    def test_get_weekly_weather_sync_exception(self):
        """Тест синхронной обертки при исключении"""
        # Arrange
        with patch.object(weather_client, 'get_weekly_weather', 
                         side_effect=Exception("API error")):
            # Act
            result = get_weekly_weather_sync()
            
            # Assert
            assert result['source'] == "demo"  # Должны получить демо-данные
            assert 'note' in result
            
    def test_condition_code_mapping(self):
        """Тест кодов условий погоды"""
        # Arrange
        weather = GismeteoWeather()
        
        # Act & Assert
        assert weather._get_condition_code("ясно") == 1
        assert weather._get_condition_code("малооблачно") == 2
        assert weather._get_condition_code("переменная облачность") == 3
        assert weather._get_condition_code("облачно") == 4
        assert weather._get_condition_code("дождь") == 5
        assert weather._get_condition_code("ливень") == 6
        assert weather._get_condition_code("гроза") == 7
        assert weather._get_condition_code("снег") == 8
        assert weather._get_condition_code("туман") == 9
        assert weather._get_condition_code("неизвестно") == 1  # default