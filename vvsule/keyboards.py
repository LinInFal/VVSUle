"""
Inline-keyboards для бота.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ввода группы"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Ввести группу", callback_data="input_group")
    builder.button(
        text="🌐 Веб-приложение", 
        web_app=WebAppInfo(url="https://vvsule-makxfed.amvera.io/")
    )

    builder.adjust(1, 1)
    return builder.as_markup()


def get_main_menu_keyboard(group_name: str = None) -> InlineKeyboardMarkup:
    """Основное меню с выбором недели"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Текущая неделя", callback_data="current_week")
    builder.button(text="Назад", callback_data="input_group")
    
    builder.adjust(1, 1)
    return builder.as_markup()


def get_schedule_keyboard(group_name: str, week_type: str = "current") -> InlineKeyboardMarkup:
    """Клавиатура при просмотре расписания"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации по неделям
    builder.button(text="⏪", callback_data=f"schedule_prev_{group_name}")
    builder.button(text="Текущая", callback_data=f"schedule_current_{group_name}")
    builder.button(text="⏩", callback_data=f"schedule_next_{group_name}")
    builder.button(text="Назад", callback_data=f"main_menu_{group_name}")
    
    builder.adjust(3, 1)
    return builder.as_markup()