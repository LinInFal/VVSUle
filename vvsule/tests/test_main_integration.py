"""
Интеграционные тесты для основных функций приложения

"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from vvsule.main import main as bot_main
from vvsule.database.database import database
from vvsule.database.crud import crud


class TestIntegration:
    """Интеграционные тесты основных компонентов"""
    
    @pytest.fixture
    def mock_bot(self):
        """Фикстура для мока бота"""
        mock = AsyncMock()
        mock.token = "test_token"
        return mock
        
    @pytest.fixture
    def mock_session(self):
        """Фикстура для мока сессии БД"""
        mock = AsyncMock()
        return mock
        
    @pytest.mark.asyncio
    async def test_bot_startup_integration(self, mock_bot, mock_session):
        """Тест интеграции запуска бота с моками"""
        # Arrange
        with patch('vvsule.main.Bot', return_value=mock_bot):
            with patch('vvsule.main.Dispatcher'):
                with patch('vvsule.database.database.database.create_tables') as mock_create:
                    with patch('vvsule.main.start_router'):
                        with patch('vvsule.main.schedule_router'):
                            # Act & Assert - проверяем, что функция запускается без ошибок
                            try:
                                # Запускаем на короткое время
                                task = asyncio.create_task(bot_main())
                                await asyncio.sleep(0.1)
                                task.cancel()
                            except asyncio.CancelledError:
                                pass  # Ожидаемое поведение
                                
                            # Проверяем, что были вызваны основные методы
                            mock_create.assert_called_once()
                            
    @pytest.mark.asyncio
    async def test_crud_user_operations_integration(self):
        """Тест интеграции CRUD операций с пользователями"""
        # Arrange
        mock_session = AsyncMock()
        
        # Настраиваем мок для возврата пользователя
        mock_user = Mock()
        mock_user.id = 1
        mock_user.telegram_id = 12345
        mock_user.group_name = "БПИ-25-1"
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        # Act - тестируем несколько операций
        user = await crud.get_user_by_telegram_id(mock_session, 12345)
        
        # Assert
        assert user is not None
        assert user.telegram_id == 12345
        assert user.group_name == "БПИ-25-1"
        
    @pytest.mark.asyncio
    async def test_background_task_integration(self):
        """Тест интеграции фоновых задач парсинга"""
        # Arrange
        from vvsule.background_tasks import parse_and_send_schedule
        
        mock_bot = AsyncMock()
        mock_session = AsyncMock()
        
        # Мокаем зависимости
        with patch('vvsule.background_tasks.database.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            with patch('vvsule.background_tasks.crud.get_cached_schedule') as mock_cache:
                mock_cache.return_value = None  # Нет кэша
                
                with patch('vvsule.background_tasks.parse_vvsu_timetable') as mock_parser:
                    # Мокаем успешный парсинг
                    mock_parser.return_value = {
                        'success': True,
                        'weeks': [[
                            {'Дата': 'Понедельник', 'Время': '09:00', 'Дисциплина': 'Тест'}
                        ]]
                    }
                    
                    with patch('vvsule.background_tasks.crud.save_schedule_cache'):
                        with patch('vvsule.background_tasks.crud.log_user_request'):
                            # Act
                            await parse_and_send_schedule(
                                bot=mock_bot,
                                chat_id=12345,
                                group_name="БПИ-25-1",
                                user_id=67890,
                                week_type="current",
                                offset=0
                            )
                            
                            # Assert
                            mock_bot.send_message.assert_called()
                            mock_parser.assert_called_once_with("БПИ-25-1")
                            
    @pytest.mark.asyncio
    async def test_web_api_integration(self):
        """Тест интеграции веб-API с парсером"""
        # Arrange
        from vvsule.main import get_schedule
        
        mock_request = Mock()
        mock_request.args = {'group': 'БПИ-25-1'}
        
        # Мокаем функцию парсинга
        with patch('vvsule.main.parse_vvsu_timetable') as mock_parser:
            mock_parser.return_value = {
                'success': True,
                'weeks': [[{'Дата': 'Понедельник', 'Время': '09:00'}]]
            }
            
            with patch('vvsule.main.get_cached_schedule', return_value=None):
                with patch('vvsule.main.save_schedule_cache'):
                    with patch('vvsule.main.request', mock_request):
                        # Act
                        import flask
                        with patch('flask.jsonify') as mock_jsonify:
                            mock_jsonify.return_value = Mock()
                            result = get_schedule()
                            
                            # Assert
                            assert result is not None
                            mock_parser.assert_called_once_with('БПИ-25-1')