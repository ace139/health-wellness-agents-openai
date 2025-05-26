"""Database models for the health and wellness assistant."""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, declarative_base, relationship, sessionmaker

from .config import settings

# Create SQLAlchemy engine and session
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

# Enable foreign key support for SQLite
if settings.DB_DRIVER == "sqlite":

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class User(Base):
    """User model representing a health assistant user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    dietary_preference = Column(
        String(20),
        nullable=True,
        comment="User's dietary preference (vegetarian, non-vegetarian, vegan)",
    )
    medical_conditions = Column(
        Text,
        nullable=True,
        comment="Comma-separated list of medical conditions",
    )
    physical_limitations = Column(
        Text,
        nullable=True,
        comment="Comma-separated list of physical limitations",
    )
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    cgm_readings: Mapped[List["CGMReading"]] = relationship(
        "CGMReading",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    wellbeing_logs: Mapped[List["WellbeingLog"]] = relationship(
        "WellbeingLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    meal_plans: Mapped[List["MealPlan"]] = relationship(
        "MealPlan",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    conversation_logs: Mapped[List["ConversationLog"]] = relationship(
        "ConversationLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class CGMReading(Base):
    """Continuous Glucose Monitor reading model."""

    __tablename__ = "cgm_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reading = Column(
        Float,
        nullable=False,
        comment="Glucose reading in mg/dL",
    )
    reading_type = Column(
        String(20),
        nullable=False,
        comment="Type of reading (breakfast, lunch, dinner)",
    )
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="cgm_readings")

    def __repr__(self) -> str:
        return (
            f"<CGMReading(id={self.id}, "
            f"user_id={self.user_id}, "
            f"reading={self.reading}, "
            f"type='{self.reading_type}')"
        )


class WellbeingLog(Base):
    """Wellbeing log model for tracking user feelings."""

    __tablename__ = "wellbeing_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    feeling = Column(
        Text,
        nullable=False,
        comment="How the user is feeling",
    )
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="wellbeing_logs")

    def __repr__(self) -> str:
        return (
            f"<WellbeingLog(id={self.id}, "
            f"user_id={self.user_id}, "
            f"feeling='{self.feeling[:20]}...')"
        )


class MealPlan(Base):
    """Meal plan model for storing user meal plans."""

    __tablename__ = "meal_plans"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "created_for_date",
            name="_user_date_uc",  # One plan per user per day
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    breakfast = Column(
        Text,
        nullable=False,
        comment="Breakfast meal plan",
    )
    lunch = Column(
        Text,
        nullable=False,
        comment="Lunch meal plan",
    )
    dinner = Column(
        Text,
        nullable=False,
        comment="Dinner meal plan",
    )
    created_for_date = Column(Date, nullable=False, index=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="meal_plans")

    def __repr__(self) -> str:
        return (
            f"<MealPlan(id={self.id}, "
            f"user_id={self.user_id}, "
            f"date='{self.created_for_date}')"
        )


class ConversationLog(Base):
    """Conversation log model for storing chat history."""

    __tablename__ = "conversation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id = Column(
        String(100),
        nullable=False,
        index=True,
    )
    role = Column(
        String(20),
        nullable=False,
        comment="Role in the conversation (user, agent, system)",
    )
    agent_name = Column(
        String(50),
        nullable=True,
        comment="Name of the agent that generated the message",
    )
    message = Column(
        Text,
        nullable=False,
        comment="The message content",
    )
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="conversation_logs")

    def __repr__(self) -> str:
        return (
            f"<ConversationLog(id={self.id}, "
            f"user_id={self.user_id}, "
            f"role='{self.role}')"
        )


def init_db() -> None:
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)
