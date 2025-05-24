"""Database module for the health and wellness assistant."""

from typing import List

from .config import settings
from .crud import cgm_reading, conversation_log, meal_plan, user, wellbeing_log
from .database import SessionLocal, get_db, get_db_context, get_db_session, init_db
from .models import CGMReading, ConversationLog, MealPlan, User, WellbeingLog
from .schemas import (
    CGMReadingCreate,
    CGMReadingInDB,
    CGMStatistics,
    ConversationLogCreate,
    ConversationLogInDB,
    ConversationRole,
    DietaryPreference,
    MealPlanCreate,
    MealPlanInDB,
    ReadingType,
    UserCreate,
    UserInDB,
    UserUpdate,
    UserWithStats,
    WellbeingLogCreate,
    WellbeingLogInDB,
)

# Re-export models
__all__: List[str] = [
    # Models
    "User",
    "CGMReading",
    "WellbeingLog",
    "MealPlan",
    "ConversationLog",
    # Schemas
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "CGMReadingCreate",
    "CGMReadingInDB",
    "WellbeingLogCreate",
    "WellbeingLogInDB",
    "MealPlanCreate",
    "MealPlanInDB",
    "ConversationLogCreate",
    "ConversationLogInDB",
    "CGMStatistics",
    "UserWithStats",
    "DietaryPreference",
    "ReadingType",
    "ConversationRole",
    # CRUD operations
    "user",
    "cgm_reading",
    "wellbeing_log",
    "meal_plan",
    "conversation_log",
    # Database session
    "SessionLocal",
    "get_db",
    "init_db",
    "get_db_context",
    "get_db_session",
    # Settings
    "settings",
]
