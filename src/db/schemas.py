"""Pydantic models for data validation."""
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


# Enums for type safety
class DietaryPreference(str, Enum):
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non-vegetarian"
    VEGAN = "vegan"


class ReadingType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


class ConversationRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


# Base schemas
class UserBase(BaseModel):
    """Base user schema."""

    email: str = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    city: str = Field(..., description="User's city of residence")
    date_of_birth: date = Field(..., description="User's date of birth")
    dietary_preference: Optional[DietaryPreference] = Field(
        None, description="User's dietary preference"
    )
    medical_conditions: Optional[str] = Field(
        None, description="Comma-separated list of medical conditions"
    )
    physical_limitations: Optional[str] = Field(
        None, description="Comma-separated list of physical limitations"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "city": "New York",
                "date_of_birth": "1985-05-15",
                "dietary_preference": "vegetarian",
                "medical_conditions": "Type 2 diabetes, Hypertension",
                "physical_limitations": "None",
            }
        }


class UserCreate(UserBase):
    """Schema for creating a new user."""

    pass


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    email: Optional[str] = Field(None, description="User's email address")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    city: Optional[str] = Field(None, description="User's city of residence")
    date_of_birth: Optional[date] = Field(None, description="User's date of birth")
    dietary_preference: Optional[DietaryPreference] = Field(
        None, description="User's dietary preference"
    )
    medical_conditions: Optional[str] = Field(
        None, description="Comma-separated list of medical conditions"
    )
    physical_limitations: Optional[str] = Field(
        None, description="Comma-separated list of physical limitations"
    )

    class Config:
        orm_mode = True


class UserInDB(UserBase):
    """User schema for data in the database."""

    id: int = Field(..., description="User's unique identifier")
    created_at: datetime = Field(..., description="When the user was created")

    class Config:
        orm_mode = True


class CGMReadingBase(BaseModel):
    """Base schema for CGM readings."""

    user_id: int = Field(..., description="ID of the user this reading belongs to")
    reading: float = Field(..., description="Glucose reading in mg/dL")
    reading_type: ReadingType = Field(
        ..., description="Type of reading (breakfast, lunch, dinner)"
    )
    timestamp: Optional[datetime] = Field(
        None, description="When the reading was taken (defaults to current time if not provided)"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "user_id": 1,
                "reading": 120.5,
                "reading_type": "breakfast",
                "timestamp": "2023-05-24T08:30:00",
            }
        }


class CGMReadingCreate(CGMReadingBase):
    """Schema for creating a new CGM reading."""

    pass


class CGMReadingInDB(CGMReadingBase):
    """CGM reading schema for data in the database."""

    id: int = Field(..., description="Reading's unique identifier")

    class Config:
        orm_mode = True


class WellbeingLogBase(BaseModel):
    """Base schema for wellbeing logs."""

    user_id: int = Field(..., description="ID of the user this log belongs to")
    feeling: str = Field(..., description="How the user is feeling")
    timestamp: Optional[datetime] = Field(
        None, description="When the log was created (defaults to current time if not provided)"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "user_id": 1,
                "feeling": "Feeling great today!",
                "timestamp": "2023-05-24T10:15:00",
            }
        }


class WellbeingLogCreate(WellbeingLogBase):
    """Schema for creating a new wellbeing log."""

    pass


class WellbeingLogInDB(WellbeingLogBase):
    """Wellbeing log schema for data in the database."""

    id: int = Field(..., description="Log's unique identifier")

    class Config:
        orm_mode = True


class MealPlanBase(BaseModel):
    """Base schema for meal plans."""

    user_id: int = Field(..., description="ID of the user this meal plan is for")
    breakfast: str = Field(..., description="Breakfast meal plan")
    lunch: str = Field(..., description="Lunch meal plan")
    dinner: str = Field(..., description="Dinner meal plan")
    created_for_date: date = Field(..., description="Date this meal plan is for")
    created_at: Optional[datetime] = Field(
        None, description="When the meal plan was created (defaults to current time if not provided)"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "user_id": 1,
                "breakfast": "Oatmeal with berries and nuts",
                "lunch": "Grilled chicken salad with olive oil dressing",
                "dinner": "Baked salmon with quinoa and steamed vegetables",
                "created_for_date": "2023-05-24",
            }
        }


class MealPlanCreate(MealPlanBase):
    """Schema for creating a new meal plan."""

    pass


class MealPlanInDB(MealPlanBase):
    """Meal plan schema for data in the database."""

    id: int = Field(..., description="Meal plan's unique identifier")

    class Config:
        orm_mode = True


class ConversationLogBase(BaseModel):
    """Base schema for conversation logs."""

    user_id: int = Field(..., description="ID of the user in the conversation")
    session_id: str = Field(..., description="Unique identifier for the conversation session")
    role: ConversationRole = Field(..., description="Role in the conversation")
    agent_name: Optional[str] = Field(
        None, description="Name of the agent that generated the message"
    )
    message: str = Field(..., description="The message content")
    timestamp: Optional[datetime] = Field(
        None, description="When the message was sent (defaults to current time if not provided)"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "user_id": 1,
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "user",
                "agent_name": "greeter_agent",
                "message": "Hello, how are you?",
                "timestamp": "2023-05-24T14:30:00",
            }
        }


class ConversationLogCreate(ConversationLogBase):
    """Schema for creating a new conversation log."""

    pass


class ConversationLogInDB(ConversationLogBase):
    """Conversation log schema for data in the database."""

    id: int = Field(..., description="Log's unique identifier")

    class Config:
        orm_mode = True


# Response schemas
class CGMStatistics(BaseModel):
    """Schema for CGM statistics."""

    average: Optional[float] = Field(None, description="Average glucose reading")
    minimum: Optional[float] = Field(None, description="Minimum glucose reading")
    maximum: Optional[float] = Field(None, description="Maximum glucose reading")
    total_readings: int = Field(..., description="Total number of readings")
    by_meal_type: Dict[str, Dict[str, Union[float, int]]] = Field(
        ..., description="Statistics by meal type"
    )

    class Config:
        orm_mode = True


# Combined schemas for API responses
class UserWithStats(UserInDB):
    """User schema with CGM statistics."""

    cgm_stats: Optional[CGMStatistics] = Field(
        None, description="CGM statistics for the user"
    )
    latest_wellbeing: Optional[WellbeingLogInDB] = Field(
        None, description="Latest wellbeing log for the user"
    )
    latest_meal_plan: Optional[MealPlanInDB] = Field(
        None, description="Latest meal plan for the user"
    )

    class Config:
        orm_mode = True
