"""
CRUD операции.
Функции для работы с пользователями, кэшем, логированием.

"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from .models import User, ScheduleCache, UserRequest
import json


class CRUD:
    # ========== User Operations ==========
    async def get_or_create_user(
            self,
            session: AsyncSession,
            telegram_id: int,
            username: str = None,
            first_name: str = None,
            last_name: str = None,
            group_name: str = None
    ) -> User:
        """Получение или создание пользователя"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                group_name=group_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Обновляем последнюю активность
            user.last_activity = datetime.utcnow()
            if group_name:
                user.group_name = group_name
            await session.commit()

        return user

    async def update_user_group(
            self,
            session: AsyncSession,
            telegram_id: int,
            group_name: str
    ) -> bool:
        """Обновление группы пользователя"""
        result = await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(group_name=group_name)
        )
        await session.commit()
        return result.rowcount > 0

    async def get_user_by_telegram_id(
            self,
            session: AsyncSession,
            telegram_id: int
    ) -> User:
        """Получение пользователя по Telegram ID"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    # ========== Schedule Cache Operations ==========
    async def get_cached_schedule(
            self,
            session: AsyncSession,
            group_name: str,
            week_type: str
    ) -> dict:
        """Получение кэшированного расписания"""
        result = await session.execute(
            select(ScheduleCache)
            .where(
                ScheduleCache.group_name == group_name,
                ScheduleCache.week_type == week_type
            )
        )
        cache = result.scalar_one_or_none()

        if cache:
            # Проверяем, не устарели ли данные (больше 1 часа)
            time_diff = datetime.utcnow() - cache.last_updated
            if time_diff.total_seconds() < 3600:  # 1 час
                return json.loads(cache.schedule_data)

        return None

    async def save_schedule_cache(
            self,
            session: AsyncSession,
            group_name: str,
            week_type: str,
            schedule_data: dict
    ):
        """Сохранение расписания в кэш"""
        result = await session.execute(
            select(ScheduleCache)
            .where(
                ScheduleCache.group_name == group_name,
                ScheduleCache.week_type == week_type
            )
        )
        cache = result.scalar_one_or_none()

        if cache:
            cache.schedule_data = json.dumps(schedule_data, ensure_ascii=False)
            cache.last_updated = datetime.utcnow()
        else:
            cache = ScheduleCache(
                group_name=group_name,
                week_type=week_type,
                schedule_data=json.dumps(schedule_data, ensure_ascii=False)
            )
            session.add(cache)

        await session.commit()

    # ========== Logging Operations ==========
    async def log_user_request(
            self,
            session: AsyncSession,
            user_id: int,
            command: str,
            group_name: str = None
    ):
        """Логирование запроса пользователя"""
        request = UserRequest(
            user_id=user_id,
            command=command,
            group_name=group_name
        )
        session.add(request)
        await session.commit()


# Создаем экземпляр CRUD
crud = CRUD()
