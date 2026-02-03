"""Обработчик расписания"""

from aiogram import Router, types, F, Bot
from aiogram.filters import Command
import asyncio
from vvsule.database.crud import crud
from vvsule.database.database import database
from vvsule.keyboards import get_main_menu_keyboard, get_schedule_keyboard
from vvsule.background_tasks import parse_and_send_schedule
import logging


router = Router()


@router.callback_query(F.data == "current_week")
async def process_current_week(callback: types.CallbackQuery, bot: Bot):
    """Обработчик кнопки 'Текущая неделя'"""
    # НЕМЕДЛЕННО отвечаем
    await callback.answer("⌛")
    
    # Получаем группу пользователя
    async for session in database.get_session():
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        
        if user and user.group_name:
            # Редактируем сообщение на "Загрузка..."
            normalized_group = user.group_name.upper()

            await callback.message.edit_text(
                f"⏳ Загружаю расписание для группы <b>{normalized_group}</b>...\n"
                f"⏰ Это может занять некоторое время",
                parse_mode="HTML"
            )
            
            # Запускаем парсинг в фоне, передаем ID сообщения для редактирования
            asyncio.create_task(
                parse_and_send_schedule(
                    bot=bot,
                    chat_id=callback.message.chat.id,
                    group_name=normalized_group,
                    user_id=callback.from_user.id,
                    week_type="current",
                    offset=0,
                    message_id=callback.message.message_id  # Передаем ID сообщения для редактирования
                )
            )
        else:
            await callback.message.edit_text(
                "❌ У вас не сохранена группа.\n"
                "Введите название группы:",
                reply_markup=None
            )


@router.callback_query(F.data.startswith("schedule_"))
async def process_schedule_navigation(callback: types.CallbackQuery, bot: Bot):
    """Обработчик навигации по расписанию"""
    # НЕМЕДЛЕННО отвечаем
    await callback.answer("⌛")
    
    # Формат данных: schedule_[direction]_[group]
    parts = callback.data.split("_")
    if len(parts) >= 3:
        direction = parts[1]  # current, next, prev
        group_name = "_".join(parts[2:])  # восстанавливаем группу
        
        normalized_group = group_name.upper()

        offset = 0
        if direction == "prev":
            offset = -1
        elif direction == "next":
            offset = 1
        elif direction == "current":
            offset = 0
        
        # Редактируем сообщение на "Загрузка..."
        await callback.message.edit_text(
            f"⏳ Загружаю расписание для группы <b>{normalized_group}</b>...",
            parse_mode="HTML"
        )
        
        # Запускаем парсинг в фоне, передаем ID сообщения для редактирования
        asyncio.create_task(
            parse_and_send_schedule(
                bot=bot,
                chat_id=callback.message.chat.id,
                group_name=normalized_group,
                user_id=callback.from_user.id,
                week_type=direction,
                offset=offset,
                message_id=callback.message.message_id  # Передаем ID сообщения для редактирования
            )
        )