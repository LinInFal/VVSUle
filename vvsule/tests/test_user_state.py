"""
Тесты для модуля хранения состояния пользователей vvsule/user_state.py

"""

import pytest
from vvsule.user_state import (
    get_user_week_position,
    set_user_week_position,
    update_user_week_position
)


class TestUserState:
    """Тесты для функций хранения состояния пользователей"""
    
    def setup_method(self):
        """Очистка состояния перед каждым тестом"""
        from vvsule.user_state import user_positions
        user_positions.clear()
        
    def test_get_user_week_position_default(self):
        """Тест получения позиции по умолчанию (еще не установлена)"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        
        # Act
        position = get_user_week_position(user_id, group_name)
        
        # Assert
        assert position == 0  # Значение по умолчанию
        
    def test_set_and_get_user_week_position(self):
        """Тест установки и получения позиции недели"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        
        # Act
        set_user_week_position(user_id, group_name, 2)
        position = get_user_week_position(user_id, group_name)
        
        # Assert
        assert position == 2
        
    def test_set_user_week_position_multiple_users(self):
        """Тест хранения позиций для нескольких пользователей"""
        # Arrange
        user1_id = 12345
        user2_id = 67890
        group1 = "БПИ-25-1"
        group2 = "БПИ-25-2"
        
        # Act
        set_user_week_position(user1_id, group1, 0)
        set_user_week_position(user1_id, group2, 1)
        set_user_week_position(user2_id, group1, 2)
        set_user_week_position(user2_id, group2, 3)
        
        # Assert
        assert get_user_week_position(user1_id, group1) == 0
        assert get_user_week_position(user1_id, group2) == 1
        assert get_user_week_position(user2_id, group1) == 2
        assert get_user_week_position(user2_id, group2) == 3
        
    def test_update_user_week_position_forward(self):
        """Тест обновления позиции с переходом вперед"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        set_user_week_position(user_id, group_name, 1)
        total_weeks = 5
        
        # Act
        new_position = update_user_week_position(user_id, group_name, 1, total_weeks)
        
        # Assert
        assert new_position == 2
        assert get_user_week_position(user_id, group_name) == 2
        
    def test_update_user_week_position_backward(self):
        """Тест обновления позиции с переходом назад"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        set_user_week_position(user_id, group_name, 3)
        total_weeks = 5
        
        # Act
        new_position = update_user_week_position(user_id, group_name, -1, total_weeks)
        
        # Assert
        assert new_position == 2
        assert get_user_week_position(user_id, group_name) == 2
        
    def test_update_user_week_position_lower_bound(self):
        """Тест обновления позиции с выходом за нижнюю границу"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        set_user_week_position(user_id, group_name, 0)
        total_weeks = 5
        
        # Act
        new_position = update_user_week_position(user_id, group_name, -1, total_weeks)
        
        # Assert
        assert new_position == 0  # Не может быть меньше 0
        assert get_user_week_position(user_id, group_name) == 0
        
    def test_update_user_week_position_upper_bound(self):
        """Тест обновления позиции с выходом за верхнюю границу"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        set_user_week_position(user_id, group_name, 4)
        total_weeks = 5
        
        # Act
        new_position = update_user_week_position(user_id, group_name, 1, total_weeks)
        
        # Assert
        assert new_position == 4  # Не может быть больше total_weeks - 1
        assert get_user_week_position(user_id, group_name) == 4
        
    def test_update_user_week_position_no_change(self):
        """Тест обновления позиции с нулевым смещением"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        set_user_week_position(user_id, group_name, 2)
        total_weeks = 5
        
        # Act
        new_position = update_user_week_position(user_id, group_name, 0, total_weeks)
        
        # Assert
        assert new_position == 2
        assert get_user_week_position(user_id, group_name) == 2
        
    def test_update_user_week_position_multiple_steps(self):
        """Тест обновления позиции с несколькими шагами"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        set_user_week_position(user_id, group_name, 0)
        total_weeks = 10
        
        # Act
        # Переходим на 3 недели вперед
        pos1 = update_user_week_position(user_id, group_name, 3, total_weeks)
        # Еще на 2 вперед
        pos2 = update_user_week_position(user_id, group_name, 2, total_weeks)
        # На 4 назад
        pos3 = update_user_week_position(user_id, group_name, -4, total_weeks)
        
        # Assert
        assert pos1 == 3
        assert pos2 == 5
        assert pos3 == 1
        assert get_user_week_position(user_id, group_name) == 1
        
    def test_update_user_week_position_single_week(self):
        """Тест обновления позиции при наличии только одной недели"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        set_user_week_position(user_id, group_name, 0)
        total_weeks = 1  # Только одна неделя
        
        # Act
        new_position = update_user_week_position(user_id, group_name, 1, total_weeks)
        
        # Assert
        assert new_position == 0  # Всегда 0 при одной неделе
        assert get_user_week_position(user_id, group_name) == 0
        
    def test_user_key_generation(self):
        """Тест проверки формата ключа пользователя"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        
        # Act
        set_user_week_position(user_id, group_name, 2)
        
        # Assert - проверяем, что ключ сгенерирован правильно
        from vvsule.user_state import user_positions
        expected_key = f"{user_id}_{group_name}"
        assert expected_key in user_positions
        assert user_positions[expected_key] == 2
        
    def test_concurrent_updates_simulation(self):
        """Тест симуляции конкурентных обновлений (негативный случай)"""
        # Arrange
        user_id = 12345
        group_name = "БПИ-25-1"
        total_weeks = 10
        
        # Симулируем несколько "параллельных" обновлений
        positions = []
        for i in range(5):
            # Каждое обновление начинается с позиции 0
            set_user_week_position(user_id, group_name, 0)
            pos = update_user_week_position(user_id, group_name, i + 1, total_weeks)
            positions.append(pos)
            
        # Assert - проверяем, что последнее обновление сохранилось
        final_position = get_user_week_position(user_id, group_name)
        assert final_position == positions[-1]  # Последнее вычисленное значение
        
    def test_reset_position_for_new_group(self):
        """Тест сброса позиции при работе с новой группой"""
        # Arrange
        user_id = 12345
        group1 = "БПИ-25-1"
        group2 = "БПИ-25-2"
        
        # Устанавливаем позицию для первой группы
        set_user_week_position(user_id, group1, 3)
        
        # Act - получаем позицию для второй группы (еще не установлена)
        position = get_user_week_position(user_id, group2)
        
        # Assert
        assert position == 0  # Значение по умолчанию для новой группы
        # При этом позиция для первой группы не изменилась
        assert get_user_week_position(user_id, group1) == 3