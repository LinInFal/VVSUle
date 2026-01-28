"""Фоновые задачи для парсинга расписания"""

import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from vvsule.database.crud import crud
from vvsule.database.database import database
from vvsule.parser import parse_vvsu_timetable
from vvsule.keyboards import get_schedule_keyboard
from vvsule.user_state import get_user_week_position, update_user_week_position, set_user_week_position


async def parse_and_send_schedule(bot: Bot, chat_id: int, group_name: str, user_id: int, 
                                  week_type: str, offset: int, message_id: int = None):
    """Фоновая задача парсинга и отправки/редактирования расписания"""
    try:
        logging.info(f"=== НАЧАЛО фонового парсинга для {group_name} ===")
        
        # Сначала проверяем кэш
        cached_schedule = None
        async for session in database.get_session():
            logging.info(f"Проверяю кэш для группы {group_name}")
            cached_schedule = await crud.get_cached_schedule(
                session=session,
                group_name=group_name,
                week_type="all_weeks"
            )
            
            if cached_schedule:
                logging.info(f"Найден кэш для {group_name}: {len(cached_schedule.get('weeks', []))} недель")
            else:
                logging.info(f"Кэш для {group_name} не найден")
            
            # Логируем запрос
            user = await crud.get_user_by_telegram_id(session, user_id)
            if user:
                await crud.log_user_request(
                    session=session,
                    user_id=user.id,
                    command="schedule_all_weeks",
                    group_name=group_name
                )
        
        all_weeks_data = cached_schedule
        
        if not all_weeks_data:
            logging.info(f"Начинаю парсинг ВСЕХ недель для {group_name}")
            # Парсим расписание
            loop = asyncio.get_event_loop()
            all_weeks_data = await loop.run_in_executor(
                None, parse_vvsu_timetable, group_name
            )
            
            if all_weeks_data:
                logging.info(f"Парсинг завершен: {len(all_weeks_data.get('weeks', []))} недель")
            
            # Сохраняем в кэш если успешно
            if all_weeks_data and all_weeks_data.get('success') is True:
                logging.info(f"Сохраняю в кэш для {group_name}")
                async for session in database.get_session():
                    try:
                        await crud.save_schedule_cache(
                            session=session,
                            group_name=group_name,
                            week_type="all_weeks",
                            schedule_data=all_weeks_data
                        )
                        logging.info(f"Кэш сохранен: {len(all_weeks_data.get('weeks', []))} недель")
                    except Exception as e:
                        logging.error(f"Ошибка при сохранении в кэш: {e}")
        
        # Проверяем результат
        if not all_weeks_data:
            logging.error(f"all_weeks_data is None для {group_name}")
            error_text = f"❌ Не удалось загрузить расписание: Пустой результат"
            if message_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(chat_id, error_text, parse_mode="HTML")
            return
        
        if all_weeks_data.get('success') is not True:
            error_msg = all_weeks_data.get('error', 'Неизвестная ошибка')
            logging.error(f"Ошибка в данных: {error_msg}")
            error_text = f"❌ Не удалось загрузить расписание: {error_msg}"
            if message_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(chat_id, error_text, parse_mode="HTML")
            return
        
        # Обрабатываем расписание
        weeks = all_weeks_data.get('weeks', [])
        total_weeks = len(weeks)
        
        logging.info(f"Получено недель: {total_weeks}")
        
        if total_weeks == 0:
            logging.warning(f"Пустое расписание для {group_name}")
            error_text = f"❌ Расписание для группы {group_name} не найдено"
            if message_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(chat_id, error_text, parse_mode="HTML")
            return
        
        # Определяем индекс недели
        week_index = calculate_week_index(week_type, offset, total_weeks, user_id, group_name)
        
        logging.info(f"Выбираю неделю {week_index + 1} из {total_weeks}")
        
        # Берем нужную неделю
        if 0 <= week_index < total_weeks:
            schedule_data = weeks[week_index]
            logging.info(f"Занятий в неделе {week_index + 1}: {len(schedule_data)}")
        else:
            schedule_data = []
            logging.warning(f"Неделя {week_index + 1} не найдена")
        
        # Форматируем расписание
        schedule_text = format_schedule_for_telegram(schedule_data)
        week_name = get_week_name_with_number(week_type, offset, week_index, total_weeks)
        
        response_text = (
            f"Расписание для группы <b>{group_name}</b>\n"
            f"{week_name}\n"
            f"Неделя {week_index + 1} из {total_weeks}\n\n"
            f"{schedule_text}"
        )
        
        # Создаем клавиатуру
        keyboard = get_schedule_keyboard(group_name, week_type)
        
        logging.info(f"Подготавливаю сообщение ({len(response_text)} символов)")
        
        # Отправляем или редактируем сообщение
        await send_or_edit_schedule_message(
            bot=bot,
            chat_id=chat_id,
            message_id=message_id,
            text=response_text,
            keyboard=keyboard
        )
        
        logging.info(f"=== УСПЕШНО завершено для {group_name} ===")
        
    except Exception as e:
        logging.error(f"=== ОШИБКА в фоновой задаче: {e} ===", exc_info=True)
        try:
            error_text = f"❌ Произошла ошибка при загрузке расписания"
            if message_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(chat_id, error_text, parse_mode="HTML")
        except Exception as send_error:
            logging.error(f"Не удалось отправить сообщение об ошибке: {send_error}")


async def send_or_edit_schedule_message(bot: Bot, chat_id: int, message_id: int, 
                                       text: str, keyboard: InlineKeyboardMarkup):
    """Отправляет новое сообщение или редактирует существующее"""
    try:
        if len(text) > 4000:
            # Для длинных сообщений разбиваем на части
            parts = split_message(text)
            logging.info(f"Разбиваю на {len(parts)} частей")
            
            if message_id:
                # Редактируем первую часть
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=parts[0],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                # Остальные части отправляем новыми сообщениями
                for part in parts[1:]:
                    await bot.send_message(chat_id, part, parse_mode="HTML")
            else:
                # Отправляем первую часть с клавиатурой
                msg = await bot.send_message(
                    chat_id,
                    parts[0],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                # Остальные части отправляем новыми сообщениями
                for part in parts[1:]:
                    await bot.send_message(chat_id, part, parse_mode="HTML")
        else:
            if message_id:
                # Редактируем существующее сообщение
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                # Отправляем новое сообщение
                await bot.send_message(
                    chat_id,
                    text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
    except Exception as e:
        logging.error(f"Ошибка при отправке/редактировании сообщения: {e}")
        # Если не удалось отредактировать (например, сообщение слишком старое),
        # отправляем новое
        if message_id:
            try:
                await bot.send_message(
                    chat_id,
                    text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception as e2:
                logging.error(f"Не удалось отправить новое сообщение: {e2}")


def calculate_week_index(week_type: str, offset: int, total_weeks: int, user_id: int, group_name: str) -> int:
    """Вычисляет индекс недели для отображения"""
    if week_type == "current":
        # Сбрасываем позицию на первую неделю
        set_user_week_position(user_id, group_name, 0)
        return 0
    
    # Для навигации используем сохраненную позицию
    return update_user_week_position(user_id, group_name, offset, total_weeks)


def get_week_name_with_number(week_type: str, offset: int, week_index: int, total_weeks: int) -> str:
    """Получить название недели с номером"""
    week_names = {
        "current": "📅 Текущая неделя",
        "next": "➡️ Следующая неделя", 
        "prev": "⬅️ Предыдущая неделя"
    }
    
    base_name = week_names.get(week_type, f"Неделя {week_index + 1}")
    return f"{base_name}"


def format_schedule_for_telegram(schedule: list) -> str:
    """Форматирование расписания для Telegram"""
    if not schedule:
        return "📭 На этой неделе занятий нет"
    
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
    
    if not result_lines:
        return "📭 На этой неделе занятий нет"
    
    return "\n".join(result_lines)


def split_message(text: str, max_length: int = 4000) -> list:
    """Разделение длинного сообщения на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip('\n')
    
    return parts