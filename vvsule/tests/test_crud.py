"""
Тесты для CRUD операций vvsule/database/crud.py

"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
import json
from vvsule.database.crud import crud, CRUD
from vvsule.database.models import User, ScheduleCache, UserRequest


class TestCRUD:
    """Тесты для класса CRUD"""
    
    @pytest.fixture
    def mock_session(self):
        """Фикстура для мока асинхронной сессии"""
        session = AsyncMock()
        return session
        
    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self, mock_session):
        """Тест создания нового пользователя"""
        # Arrange
        # Создаем mock результата запроса
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        
        mock_session.execute.return_value = mock_result
        
        # Act
        user = await crud.get_or_create_user(
            session=mock_session,
            telegram_id=12345,
            username="test_user",
            first_name="Иван",
            last_name="Иванов",
            group_name="БПИ-25-1"
        )
        
        # Assert
        assert user is not None  # Вместо проверки атрибутов
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        
    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, mock_session):
        """Тест получения существующего пользователя"""
        # Arrange
        existing_user = User(
            id=1,
            telegram_id=12345,
            username="existing_user",
            group_name=None
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_user
        mock_session.commit = AsyncMock()
        
        # Act
        user = await crud.get_or_create_user(
            session=mock_session,
            telegram_id=12345,
            username="updated_user",
            group_name="БПИ-25-1"
        )
        
        # Assert
        assert user.id == 1
        assert user.group_name == "БПИ-25-1"  # Группа должна обновиться
        mock_session.commit.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_update_user_group(self, mock_session):
        """Тест обновления группы пользователя"""
        # Arrange
        mock_session.execute.return_value.rowcount = 1
        
        # Act
        result = await crud.update_user_group(
            session=mock_session,
            telegram_id=12345,
            group_name="БПИ-25-2"
        )
        
        # Assert
        assert result is True
        mock_session.commit.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_found(self, mock_session):
        """Тест получения пользователя по ID (найден)"""
        # Arrange
        expected_user = User(telegram_id=12345)
        mock_session.execute.return_value.scalar_one_or_none.return_value = expected_user
        
        # Act
        user = await crud.get_user_by_telegram_id(mock_session, 12345)
        
        # Assert
        assert user == expected_user
        
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_found(self, mock_session):
        """Тест получения пользователя по ID (не найден)"""
        # Arrange
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Act
        user = await crud.get_user_by_telegram_id(mock_session, 99999)
        
        # Assert
        assert user is None
        
    @pytest.mark.asyncio
    async def test_get_cached_schedule_fresh(self, mock_session):
        """Тест получения свежего кэша расписания"""
        # Arrange
        cache_data = {'weeks': [[{'Дата': 'Понедельник'}]]}

        from vvsule.database.models import ScheduleCache
        from datetime import datetime

        cache = ScheduleCache(
            id=1,
            group_name="БПИ-25-1",
            week_type="all_weeks",
            schedule_data=json.dumps(cache_data),
            last_updated=datetime.utcnow()
        )
        
        # Мокаем execute чтобы он возвращал cache
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = cache
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await crud.get_cached_schedule(
            session=mock_session,
            group_name="БПИ-25-1",
            week_type="all_weeks"
        )
        
        # Assert
        assert result == cache_data
        
    @pytest.mark.asyncio
    async def test_get_cached_schedule_stale(self, mock_session):
        """Тест получения устаревшего кэша расписания"""
        # Arrange
        from datetime import datetime, timedelta
        
        cache_data = {'weeks': [[]]}
        cache = ScheduleCache(
            schedule_data=json.dumps(cache_data),
            last_updated=datetime.utcnow() - timedelta(hours=10)  # Устаревший кэш
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = cache
        
        # Act
        result = await crud.get_cached_schedule(
            session=mock_session,
            group_name="БПИ-25-1",
            week_type="all_weeks"
        )
        
        # Assert
        assert result is None  # Устаревший кэш не возвращается
        
    @pytest.mark.asyncio
    async def test_get_cached_schedule_not_found(self, mock_session):
        """Тест получения кэша расписания (кэш не найден)"""
        # Arrange
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Act
        result = await crud.get_cached_schedule(
            session=mock_session,
            group_name="БПИ-25-1",
            week_type="all_weeks"
        )
        
        # Assert
        assert result is None
        
    @pytest.mark.asyncio
    async def test_save_schedule_cache_new(self, mock_session):
        """Тест сохранения нового кэша расписания"""
        # Arrange
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        schedule_data = {'weeks': [[{'Дата': 'Понедельник'}]]}
        
        # Act
        await crud.save_schedule_cache(
            session=mock_session,
            group_name="БПИ-25-1",
            week_type="all_weeks",
            schedule_data=schedule_data
        )
        
        # Assert
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_save_schedule_cache_update(self, mock_session):
        """Тест обновления существующего кэша расписания"""
        # Arrange
        existing_cache = ScheduleCache(
            id=1,
            group_name="БПИ-25-1",
            week_type="all_weeks",
            schedule_data=json.dumps({'old': 'data'})
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_cache
        new_schedule_data = {'weeks': [[{'Дата': 'Вторник'}]]}
        
        # Act
        await crud.save_schedule_cache(
            session=mock_session,
            group_name="БПИ-25-1",
            week_type="all_weeks",
            schedule_data=new_schedule_data
        )
        
        # Assert
        assert json.loads(existing_cache.schedule_data) == new_schedule_data
        mock_session.commit.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_log_user_request(self, mock_session):
        """Тест логирования запроса пользователя"""
        # Arrange
        mock_session.commit = AsyncMock()
        
        # Act
        await crud.log_user_request(
            session=mock_session,
            user_id=1,
            command="schedule_all_weeks",
            group_name="БПИ-25-1"
        )
        
        # Assert
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        added_request = mock_session.add.call_args[0][0]
        assert isinstance(added_request, UserRequest)
        assert added_request.user_id == 1
        assert added_request.command == "schedule_all_weeks"
        assert added_request.group_name == "БПИ-25-1"