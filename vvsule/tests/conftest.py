"""
Конфигурация pytest для тестов VVSUle

"""

"""
Запуск всех тестов
pytest vvsule/tests/ -v

Запуск с покрытием кода
pytest vvsule/tests/ --cov=vvsule --cov-report=html

Запуск конкретного тестового файла
pytest vvsule/tests/test_parser.py -v

Запуск тестов с выводом подробной информации
pytest vvsule/tests/ -v --tb=short
"""
import pytest
import asyncio
import sys
import os

# Добавляем путь к родительскому каталогу для импорта модулей
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для асинхронных тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_schedule_data():
    """Фикстура с примерными данными расписания"""
    return {
        'success': True,
        'group_name': 'БПИ-25-1',
        'weeks': [
            [  # Неделя 1
                {
                    'Дата': 'Понедельник 01.01.2024',
                    'Время': '09:00 - 10:30',
                    'Дисциплина': 'Математика',
                    'Аудитория': '101',
                    'Преподаватель': 'Иванов И.И.',
                    'Тип занятия': 'Лекция'
                }
            ],
            [  # Неделя 2
                {
                    'Дата': 'Понедельник 08.01.2024',
                    'Время': '11:00 - 12:30',
                    'Дисциплина': 'Программирование',
                    'Аудитория': '201',
                    'Преподаватель': 'Петров П.П.',
                    'Тип занятия': 'Практика'
                }
            ]
        ],
        'total_weeks': 2
    }


@pytest.fixture
def sample_weather_data():
    """Фикстура с примерными данными погоды"""
    return {
        'success': True,
        'city': 'Владивосток',
        'forecast': [
            {
                'date_display': 'Понедельник, 1 января',
                'temperature': -5,
                'condition_icon': '☀️',
                'wind_speed': 3,
                'humidity': 75
            }
        ]
    }


@pytest.fixture
def mock_driver():
    """Фикстура для мока драйвера Selenium"""
    from unittest.mock import Mock
    driver = Mock()
    
    # Настраиваем основные методы драйвера
    driver.find_element.return_value = Mock()
    driver.find_elements.return_value = []
    driver.execute_script = Mock()
    driver.quit = Mock()
    
    return driver