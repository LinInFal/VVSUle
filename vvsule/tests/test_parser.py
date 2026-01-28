"""
Тесты для модуля парсинга расписания vvsule/parser.py

"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from vvsule.parser import (
    parse_vvsu_timetable,
    parse_current_week,
    go_to_next_week,
    parse_schedule_table,
    setup_driver
)
import logging


class TestParser:
    """Тесты для функций парсинга расписания"""
    
    @patch('vvsule.parser.webdriver.Firefox')
    @patch('vvsule.parser.FirefoxService')
    def test_setup_driver_success(self, mock_service, mock_driver):
        """Тест успешной настройки драйвера Firefox"""
        # Arrange
        mock_driver_instance = Mock()
        mock_driver.return_value = mock_driver_instance
        
        # Act
        driver = setup_driver()
        
        # Assert
        assert driver is not None
        mock_driver.assert_called_once()
        assert mock_driver_instance.set_page_load_timeout.called
        assert mock_driver_instance.implicitly_wait.called
        
    @patch('vvsule.parser.webdriver.Firefox', side_effect=Exception("Driver error"))
    def test_setup_driver_failure(self, mock_driver):
        """Тест неудачной настройки драйвера"""
        # Act
        driver = setup_driver()
        
        # Assert
        assert driver is None
        
    @patch('vvsule.parser.setup_driver')
    def test_parse_vvsu_timetable_success(self, mock_setup_driver):
        """Тест успешного парсинга расписания (положительный случай)"""
        # Arrange
        mock_driver = Mock()
        mock_setup_driver.return_value = mock_driver
        
        # Мокаем элементы страницы
        mock_group_input = Mock()
        mock_group_button = Mock()
        mock_group_button.text = "БПИ-25-1" 
        
        mock_driver.find_elements.side_effect = [
            [mock_group_button],  # Для поиска кнопки
            []  # Для других поисков
        ]
    
        mock_driver.find_element.return_value = mock_group_input
        
        # Эмулируем парсинг недели
        with patch('vvsule.parser.parse_current_week') as mock_parse_week:
            mock_parse_week.return_value = [
                {
                    'Дата': 'Понедельник 01.01.2024',
                    'Время': '09:00 - 10:30',
                    'Дисциплина': 'Математика',
                    'Аудитория': '101',
                    'Преподаватель': 'Иванов И.И.',
                    'Тип занятия': 'Лекция'
                }
            ]
            
            with patch('vvsule.parser.go_to_next_week') as mock_next_week:
                mock_next_week.return_value = False
                
                # Act
                result = parse_vvsu_timetable("БПИ-25-1")
                
                # Assert
                assert result['success'] is True
                assert 'group_name' in result
                assert result['group_name'] == "БПИ-25-1"
                assert 'weeks' in result
                assert len(result['weeks']) > 0
                assert result['total_weeks'] == 1
                assert 'parsed_at' in result
                
    @patch('vvsule.parser.setup_driver')
    def test_parse_vvsu_timetable_group_not_found(self, mock_setup_driver):
        """Тест парсинга с несуществующей группой (негативный случай)"""
        # Arrange
        mock_driver = Mock()
        mock_setup_driver.return_value = mock_driver
        
        # Мокаем поиск группы - группа не найдена
        mock_group_input = Mock()
        mock_driver.find_element.return_value = mock_group_input
        mock_driver.find_elements.return_value = []  # Группа не найдена
        
        # Act
        result = parse_vvsu_timetable("НЕСУЩЕСТВУЮЩАЯ-ГРУППА")
        
        # Assert
        assert result['success'] is False
        assert 'error' in result
        assert "не найдена" in result['error'] or result['error']
        assert result['weeks'] == []
        
    def test_parse_schedule_table_empty(self):
        """Тест парсинга пустой таблицы расписания"""
        # Arrange
        mock_table = Mock()
        mock_row = Mock()
        
        # Эмулируем строку без времени
        mock_time_cell = Mock()
        mock_time_cell.text.strip.return_value = ""  # Пустое время
        
        mock_row.find_element.return_value = mock_time_cell
        
        mock_table.find_elements.return_value = [mock_row]
        
        # Act
        result = parse_schedule_table(mock_table)
        
        # Assert
        assert result == []  # Пустой список, т.к. строка без времени пропускается
        
    def test_parse_schedule_table_valid_data(self):
        """Тест парсинга таблицы с валидными данными"""
        # Arrange
        mock_table = Mock()
        
        # Создаем mock строки с данными
        mock_row = Mock()
        
        # Мокаем ячейки с данными
        mock_date_cell = Mock()
        mock_date_cell.text.strip.return_value = "Понедельник 01.01.2024"
        mock_date_cell.get_attribute.return_value = "2"  # rowspan
        
        mock_time_cell = Mock()
        mock_time_cell.text.strip.return_value = "09:00 - 10:30"
        
        mock_discipline_cell = Mock()
        mock_discipline_cell.text.strip.return_value = "Математика\nЛекция"
        
        mock_classroom_cell = Mock()
        mock_classroom_cell.text.strip.return_value = "Аудитория 101"
        
        mock_teacher_cell = Mock()
        mock_teacher_cell.text.strip.return_value = "Иванов И.И."
        
        mock_type_cell = Mock()
        mock_type_cell.text.strip.return_value = "Лекция"
        
        # Настраиваем вызовы find_element для разных селекторов
        def find_element_side_effect(by, value):
            selectors = {
                ("css selector", "td[data-th='Дата']"): mock_date_cell,
                ("css selector", "td[data-th='Время']"): mock_time_cell,
                ("css selector", "td[data-th='Дисциплина']"): mock_discipline_cell,
                ("css selector", "td[data-th='Аудитория']"): mock_classroom_cell,
                ("css selector", "td[data-th='Преподаватель']"): mock_teacher_cell,
                ("css selector", "td[data-th='Занятие']"): mock_type_cell,
            }
            return selectors.get((by, value))
        
        mock_row.find_element.side_effect = find_element_side_effect
        mock_table.find_elements.return_value = [mock_row]
        
        # Act
        result = parse_schedule_table(mock_table)
        
        # Assert
        assert len(result) == 1
        lesson = result[0]
        assert lesson['Дата'] == "Понедельник 01.01.2024"
        assert lesson['Время'] == "09:00 - 10:30"
        assert lesson['Дисциплина'] == "Математика"
        assert lesson['Аудитория'] == "Аудитория 101"
        assert lesson['Преподаватель'] == "Иванов И.И."
        assert lesson['Тип занятия'] == "Лекция"
        
    @patch('vvsule.parser.logging')
    def test_parse_vvsu_timetable_exception_handling(self, mock_logging):
        """Тест обработки исключений при парсинге"""
        # Arrange
        with patch('vvsule.parser.setup_driver', side_effect=Exception("Critical error")):
            # Act
            result = parse_vvsu_timetable("БПИ-25-1")
            
            # Assert
            assert result['success'] is False
            assert 'error' in result
            assert "Critical error" in result['error']
            assert result['weeks'] == []
            mock_logging.error.assert_called()