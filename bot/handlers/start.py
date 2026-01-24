"""
Обработчик приветствия. Регистрирует пользователя в БД.
Выводит описание бота и список доступных команд.

"""
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter    
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.crud import crud
from database.database import database
from keyboards.main_menu import get_group_input_keyboard

router = Router()

class GroupInput(StatesGroup):
    """Состояния для ввода группы"""
    waiting_for_group = State()

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

🎓 Этот бот для вывода расписания занятий ВВГУ

    """

    # Отправляем сообщение с кнопкой для ввода группы
    await message.answer(welcome_text, reply_markup=get_group_input_keyboard())

@router.callback_query(F.data == "input_group")
async def process_input_group(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия кнопки 'Ввести группу'"""
    await callback.message.edit_text("📝 Введите вашу группу:\n\nПример: БПИ-25-1", reply_markup=None)
    await state.set_state(GroupInput.waiting_for_group)
    await callback.answer()

@router.message(StateFilter(GroupInput.waiting_for_group))
async def process_group_input(message: types.Message, state: FSMContext):
    """Обработчик ввода группы"""
    group_name = message.text.strip()
    
    # Сохраняем группу в БД
    async for session in database.get_session():
        await crud.update_user_group(
            session=session,
            telegram_id=message.from_user.id,
            group_name=group_name
        )
    
    # Переходим к выбору недели
    from keyboards.main_menu import get_main_menu_keyboard
    await message.answer(
        f"✅ Группа сохранена: <b>{group_name}</b>\n\n"
        "Выберите неделю для просмотра расписания:",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(group_name)
    )
    await state.clear()

@router.callback_query(F.data == "change_group")
async def process_change_group(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик смены группы"""
    await process_input_group(callback, state)