"""
Загружает настройки из .env и предоставляет структурированный доступ.
Содержит классы для настроек БД, Telegram.

"""
import os
from typing import List
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    host: str
    port: str
    name: str
    user: str
    password: str
    
    @property
    def url(self) -> str:
        # Для asyncpg драйвера
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

@dataclass
class TelegramConfig:
    """Конфигурация Telegram бота"""
    token: str
    admin_ids: List[int]
    super_admin: int

@dataclass
class Config:
    """Основная конфигурация приложения"""
    db: DatabaseConfig
    telegram: TelegramConfig
    debug: bool
    log_level: str
    
    @classmethod
    def load(cls):
        """Загрузка конфигурации из .env"""
        # Telegram
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise ValueError("BOT_TOKEN не найден!")
        
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        admin_ids = []
        if admin_ids_str:
            for id_str in admin_ids_str.split(","):
                id_str = id_str.strip()
                if id_str:
                    try:
                        admin_ids.append(int(id_str))
                    except ValueError:
                        print(f"⚠️ Некорректный ID администратора: {id_str}")
        
        super_admin = int(os.getenv("SUPER_ADMIN", "0"))
        
        # Database
        db_config = DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            name=os.getenv("DB_NAME", "vvsu_bot_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )
        
        return cls(
            db=db_config,
            telegram=TelegramConfig(
                token=token,
                admin_ids=admin_ids,
                super_admin=super_admin
            ),
            debug=os.getenv("DEBUG", "False").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper()
        )

config = Config.load()