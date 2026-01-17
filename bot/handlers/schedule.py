"""
Обрабатывает команды /schedule, /schedule next, /schedule prev.
Парсит расписание ВВГУ, кэширует в БД, форматирует ответ.

"""
from aiogram import Router, types
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


@router.message(Command("s"))
async def cmd_schedule(message: types.Message):
    """Обработчик команды /schedule (текущая неделя)"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer(
            "❌ Не указана группа!\n"
            "Используйте: /s [название_группы]\n"
            "Например: /s БПИ-24-2"
        )
        return

    group_name = args[1]
    await process_schedule_request(message, group_name, "current")

@router.message(Command("s_next"))
async def cmd_schedule(message: types.Message):
    """Обработчик команды /schedule next (следующая неделя)"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer(
            "❌ Не указана группа!\n"
            "Используйте: /s_next [название_группы]\n"
            "Например: /s_next БПИ-24-2"
        )
        return    

    group_name = args[1]
    await process_schedule_request(message, group_name, "next")
    
@router.message(Command("s_prev"))
async def cmd_schedule(message: types.Message):
    """Обработчик команды /schedule prev (предыдущая неделя)"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer(
            "❌ Не указана группа!\n"
            "Используйте: /s_prev [название_группы]\n"
            "Например: /s_prev БПИ-24-2"
        )
        return    

    group_name = args[1]
    await process_schedule_request(message, group_name, "prev")

async def process_schedule_request(message: types.Message, group_name: str, week_type: str):
    """Общая функция обработки запроса расписания"""
    # Отправляем сообщение о начале загрузки
    loading_msg = await message.answer(f"⏳ Загружаю расписание для группы {group_name}...")
 
    try:
        # Проверяем кэш
        cached_schedule = None
        async for session in database.get_session():
            cached_schedule = await crud.get_cached_schedule(
                session=session,
                group_name=group_name,
                week_type=week_type
            )
            
            # Логируем запрос
            user = await crud.get_or_create_user(
                session=session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            
            if user:
                await crud.log_user_request(
                    session=session,
                    user_id=user.id,
                    command=f"schedule_{week_type}",
                    group_name=group_name
                )
            
            # Сохраняем группу пользователя
            await crud.update_user_group(
                session=session,
                telegram_id=message.from_user.id,
                group_name=group_name
            )
        
        if cached_schedule:
            # Используем кэшированные данные
            await loading_msg.delete()
            schedule_text = format_schedule_for_telegram(cached_schedule)
            await message.answer(
                f"📅 Расписание для группы <b>{group_name}</b>\n"
                f"{'Текущая неделя' if week_type == 'current' else 'Следующая неделя' if week_type == 'next' else 'Предыдущая неделя'}\n\n"
                f"{schedule_text}",
                parse_mode="HTML"
            )
            return
        
        # Парсим расписание
        await loading_msg.edit_text(f"🔄 Парсим расписание для группы {group_name}...")
        
        # Запускаем парсинг в отдельном потоке
        loop = asyncio.get_event_loop()
        driver, wait = await loop.run_in_executor(
            None, parse_vvsu_timetable, group_name
        )
        
        if not driver or not wait:
            await loading_msg.delete()
            await message.answer(f"❌ Не удалось загрузить расписание для группы {group_name}.")
            return
        
        schedule = []
        try:
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
            # Всегда закрываем драйвер
            driver.quit()
        
        # Сохраняем в кэш
        async for session in database.get_session():
            await crud.save_schedule_cache(
                session=session,
                group_name=group_name,
                week_type=week_type,
                schedule_data=schedule
            )
        
        # Форматируем и отправляем расписание
        await loading_msg.delete()
        schedule_text = format_schedule_for_telegram(schedule)
        
        if schedule_text == "❌ Расписание не найдено или произошла ошибка при загрузке.":
            await message.answer(schedule_text)
        else:
            response_text = (
                f"📅 Расписание для группы <b>{group_name}</b>\n"
                f"{'Текущая неделя' if week_type == 'current' else 'Следующая неделя' if week_type == 'next' else 'Предыдущая неделя'}\n\n"
                f"{schedule_text}"
            )
            
            # Разбиваем сообщение если оно слишком длинное (Telegram имеет лимит 4096 символов)
            if len(response_text) > 4000:
                parts = []
                current_part = ""
                lines = response_text.split('\n')
                
                for line in lines:
                    if len(current_part) + len(line) + 1 > 4000:
                        parts.append(current_part)
                        current_part = line + '\n'
                    else:
                        current_part += line + '\n'
                
                if current_part:
                    parts.append(current_part)
                
                for i, part in enumerate(parts):
                    await message.answer(part, parse_mode="HTML")
            else:
                await message.answer(response_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error parsing schedule: {e}")
        try:
            await loading_msg.delete()
        except:
            pass
        await message.answer(f"❌ Произошла ошибка при загрузке расписания. Попробуйте позже.")
