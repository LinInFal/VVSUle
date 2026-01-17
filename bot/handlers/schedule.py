"""
Обрабатывает команды /s, /s_next, /s_prev.
Парсит расписание ВВГУ, кэширует в БД, форматирует ответ.

"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import asyncio
from parser.parser import (
    parse_vvsu_timetable, 
    get_current_week_schedule,
    go_to_next_week, 
    go_to_previous_week
)
from database.crud import crud
from database.database import database
from keyboards.main_menu import (
    get_main_menu_keyboard,
    get_schedule_keyboard
)
import logging

router = Router()
logger = logging.getLogger(__name__)


def format_schedule_for_telegram(schedule: list) -> str:
    """Форматирование расписания для Telegram"""
    if not schedule:
        return "❌ Расписание не найдено или произошла ошибка при загрузке."
    
    current_date = None
    result_lines = []
    
    for lesson in schedule:
        lesson_date = lesson.get('Дата', '').replace('\n', ' ') if lesson.get('Дата') else None
        
        if lesson_date != current_date:
            current_date = lesson_date
            if current_date:
                result_lines.append(f"◻ <b>{current_date}</b>")
                result_lines.append("─" * 29)
        
        if lesson.get('Время'):
            result_lines.append(f"<b>{lesson.get('Время', '')}</b>")
            result_lines.append(f"<b>{lesson.get('Дисциплина', 'Не указано')}</b>")
            
            webinar_link = lesson.get('Ссылка на вебинар')
            if webinar_link:
                result_lines.append(f"Вебинар: {webinar_link}")
                result_lines.append(f"{lesson.get('Аудитория', 'Не указана')}")
            else:
                result_lines.append(f"{lesson.get('Аудитория', 'Не указана')}")
            
            teacher = lesson.get('Преподаватель')
            if teacher:
                result_lines.append(f"{teacher}")
            
            lesson_type = lesson.get('Тип занятия')
            if lesson_type:
                result_lines.append(f"{lesson_type}")
            
            result_lines.append("─" * 29)
    
    return "\n".join(result_lines)

# Обработчики инлайн-кнопок
@router.callback_query(F.data.startswith("main_menu_"))
async def process_main_menu(callback: types.CallbackQuery):
    """Обработчик возврата в главное меню"""
    group_name = callback.data.replace("main_menu_", "")
    
    await callback.message.edit_text(
        f"✅ Группа: <b>{group_name}</b>\n\n"
        "Выберите неделю для просмотра расписания:",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(group_name)
    )
    await callback.answer()

@router.callback_query(F.data == "current_week")
async def process_current_week(callback: types.CallbackQuery):
    """Обработчик кнопки 'Текущая неделя'"""
    # Получаем группу пользователя из БД
    async for session in database.get_session():
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        
        if user and user.group_name:
            await show_schedule_callback(callback, user.group_name, "current")
        else:
            await callback.message.edit_text(
                "❌ У вас не сохранена группа.\n"
                "Введите название группы:",
                reply_markup=get_back_to_group_keyboard()
            )
            await callback.answer()

@router.callback_query(F.data == "next_week")
async def process_next_week(callback: types.CallbackQuery):
    """Обработчик кнопки 'Следующая неделя'"""
    async for session in database.get_session():
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        
        if user and user.group_name:
            await show_schedule_callback(callback, user.group_name, "next")
        else:
            await callback.message.edit_text(
                "❌ У вас не сохранена группа.\n"
                "Введите название группы:",
                reply_markup=get_back_to_group_keyboard()
            )
            await callback.answer()

@router.callback_query(F.data == "prev_week")
async def process_prev_week(callback: types.CallbackQuery):
    """Обработчик кнопки 'Предыдущая неделя'"""
    async for session in database.get_session():
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        
        if user and user.group_name:
            await show_schedule_callback(callback, user.group_name, "prev")
        else:
            await callback.message.edit_text(
                "❌ У вас не сохранена группа.\n"
                "Введите название группы:",
                reply_markup=get_back_to_group_keyboard()
            )
            await callback.answer()

@router.callback_query(F.data.startswith("schedule_"))
async def process_schedule_navigation(callback: types.CallbackQuery):
    """Обработчик навигации по расписанию"""
    # Формат данных: schedule_[type]_[group]
    parts = callback.data.split("_")
    if len(parts) >= 3:
        week_type = parts[1]  # current, next, prev
        group_name = "_".join(parts[2:])  # восстанавливаем группу
        await show_schedule_callback(callback, group_name, week_type)

async def show_schedule_callback(callback: types.CallbackQuery, group_name: str, week_type: str):
    """Показать расписание через callback"""
    week_names = {
        "current": "Текущая неделя",
        "next": "Следующая неделя",
        "prev": "Предыдущая неделя"
    }
    
    # Изменяем текущее сообщение на "Загрузка..."
    await callback.message.edit_text(
        f"⏳ Загружаю расписание...\n"
        f"Группа: <b>{group_name}</b>\n"
        f"{week_names[week_type]}",
        parse_mode="HTML"
    )
    
    # Получаем расписание
    schedule_data = await get_schedule_data(group_name, week_type, callback.from_user.id)
    
    # Форматируем расписание
    schedule_text = format_schedule_for_telegram(schedule_data)
    
    # Обновляем сообщение с результатом
    response_text = (
        f"Расписание для группы <b>{group_name}</b>\n"
        f"{week_names[week_type]}\n\n"
        f"{schedule_text}"
    )

    # Разбиваем длинные сообщения
    if len(response_text) > 4000:
        parts = split_message(response_text)
        for i, part in enumerate(parts):
            if i == 0:
                await callback.message.edit_text(
                    part,
                    parse_mode="HTML",
                    reply_markup=get_schedule_keyboard(group_name, week_type)
                )
            else:
                await callback.message.answer(part, parse_mode="HTML")
    else:
        await callback.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_schedule_keyboard(group_name, week_type)
        )
    
    await callback.answer()

async def get_schedule_data(group_name: str, week_type: str, user_id: int):
    """Получение данных расписания с кэшированием"""
    # Проверяем кэш
    cached_schedule = None
    async for session in database.get_session():
        cached_schedule = await crud.get_cached_schedule(
            session=session,
            group_name=group_name,
            week_type=week_type
        )
        
        # Логируем запрос
        user = await crud.get_user_by_telegram_id(session, user_id)
        if user:
            await crud.log_user_request(
                session=session,
                user_id=user.id,
                command=f"schedule_{week_type}",
                group_name=group_name
            )
    
    if cached_schedule:
        logger.info(f"Использован кэш для группы {group_name}, неделя {week_type}")
        return cached_schedule
    
    # Парсим расписание
    logger.info(f"Парсим расписание для группы {group_name}, неделя {week_type}")
    
    loop = asyncio.get_event_loop()
    driver, wait = await loop.run_in_executor(
        None, parse_vvsu_timetable, group_name
    )
    
    if not driver or not wait:
        logger.error(f"Не удалось загрузить драйвер для группы {group_name}")
        return []
    
    try:
        schedule = []
        if week_type == "current":
            schedule = await loop.run_in_executor(
                None, get_current_week_schedule, driver, wait
            )
        elif week_type == "next":
            schedule = await loop.run_in_executor(
                None, go_to_next_week, driver, wait
            )
        elif week_type == "prev":
            schedule = await loop.run_in_executor(
                None, go_to_previous_week, driver, wait
            )
    finally:
        driver.quit()
    
    # Сохраняем в кэш
    async for session in database.get_session():
        await crud.save_schedule_cache(
            session=session,
            group_name=group_name,
            week_type=week_type,
            schedule_data=schedule
        )
    
    return schedule


def split_message(text: str, max_length: int = 4000) -> list:
    """Разделение длинного сообщения на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        # Ищем последний перенос строки в пределах лимита
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip('\n')
    
    return parts


@router.callback_query(F.data.startswith("week_"))
async def process_week_selector(callback: types.CallbackQuery):
    """Обработчик выбора недели (альтернативный интерфейс)"""
    # Формат: week_[type]_[group]
    parts = callback.data.split("_")
    if len(parts) >= 3:
        week_type = parts[1]  # current, next, prev
        group_name = "_".join(parts[2:])
        await show_schedule_callback(callback, group_name, week_type)
