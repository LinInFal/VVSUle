"""
Обработчик приветствия. Регистрирует пользователя в БД.
Выводит описание бота и список доступных команд.

"""
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database.crud import crud
from database.database import database

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user = message.from_user

    # Сохраняем/обновляем пользователя в БД
    async for session in database.get_session():
        await crud.get_or_create_user(
            session=session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

    # Формируем приветственное сообщение
    welcome_text = f"""
👋 Привет, {user.first_name}!

Этот бот для вывода расписания занятий ВВГУ 🎓

📋 Доступные команды:

/schedule [группа] - Расписание на текущую неделю
/schedule next [группа] - Расписание на следующую неделю
/schedule prev [группа] - Расписание за предыдущую неделю

    """

    await message.answer(welcome_text)