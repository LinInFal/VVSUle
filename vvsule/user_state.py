"""Хранение состояния пользователей"""

user_positions = {}  # {user_id: {group_name: current_week_index}}


def get_user_week_position(user_id: int, group_name: str) -> int:
    """Получить текущую позицию недели для пользователя"""
    user_key = f"{user_id}_{group_name}"
    return user_positions.get(user_key, 0)


def set_user_week_position(user_id: int, group_name: str, week_index: int):
    """Установить позицию недели для пользователя"""
    user_key = f"{user_id}_{group_name}"
    user_positions[user_key] = week_index


def update_user_week_position(user_id: int, group_name: str, offset: int, total_weeks: int) -> int:
    """Обновить позицию недели с учетом смещения"""
    user_key = f"{user_id}_{group_name}"
    current = user_positions.get(user_key, 0)
    new_position = current + offset
    
    # Проверяем границы
    if new_position < 0:
        new_position = 0
    elif new_position >= total_weeks:
        new_position = total_weeks - 1
    
    user_positions[user_key] = new_position
    return new_position