"""
Определяет таблицы PostgreSQL как Python-классы.
User - пользователи бота
ScheduleCache - кэш расписания
UserRequest - логи запросов.

"""
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime


Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    group_name = Column(String(50))  # Сохраняем группу пользователя
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', group='{self.group_name}')>"


class ScheduleCache(Base):
    __tablename__ = "schedule_cache"
    
    id = Column(Integer, primary_key=True)
    group_name = Column(String(50), nullable=False)
    week_type = Column(String(20), nullable=False)  # 'current', 'next', 'prev'
    schedule_data = Column(String)  # JSON строка с расписанием
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Уникальное ограничение на комбинацию group_name и week_type
    __table_args__ = (
        UniqueConstraint('group_name', 'week_type', name='uq_group_week'),
    )
    
    def __repr__(self):
        return f"<ScheduleCache(group='{self.group_name}', week_type='{self.week_type}')>"


class UserRequest(Base):
    __tablename__ = "user_requests"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    command = Column(String(50), nullable=False)
    group_name = Column(String(50))
    requested_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserRequest(user_id={self.user_id}, command='{self.command}')>"