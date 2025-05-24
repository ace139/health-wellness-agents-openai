"""CRUD operations for the health and wellness assistant."""
# Standard library imports
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

# Third-party imports
from sqlalchemy import func
from sqlalchemy.orm import Session

# Local application imports
from . import models, schemas

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class CRUDBase:
    """Base class for CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_in_data = obj_in.dict() if hasattr(obj_in, "dict") else obj_in
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """Update a record."""
        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> ModelType:
        """Remove a record."""
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj


class CRUDUser(CRUDBase):
    """CRUD operations for User model."""

    def get_by_email(self, db: Session, email: str) -> Optional[models.User]:
        """Get a user by email."""
        return db.query(self.model).filter(self.model.email == email).first()

    def create(self, db: Session, *, obj_in: schemas.UserCreate) -> models.User:
        """Create a new user."""
        db_obj = models.User(
            email=obj_in.email,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            city=obj_in.city,
            date_of_birth=obj_in.date_of_birth,
            dietary_preference=obj_in.dietary_preference,
            medical_conditions=obj_in.medical_conditions,
            physical_limitations=obj_in.physical_limitations,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: models.User,
        obj_in: Union[schemas.UserUpdate, Dict[str, Any]],
    ) -> models.User:
        """Update a user."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDCGMReading(CRUDBase):
    """CRUD operations for CGMReading model."""

    def get_multi_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.CGMReading]:
        """Get CGM readings for a specific user."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(self.model.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_latest_by_user(
        self, db: Session, user_id: int
    ) -> Optional[models.CGMReading]:
        """Get the latest CGM reading for a user."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(self.model.timestamp.desc())
            .first()
        )

    def get_stats(
        self, db: Session, user_id: int, days: int = 7
    ) -> Dict[str, Any]:
        """Get CGM statistics for a user."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get basic stats
        stats = (
            db.query(
                func.avg(models.CGMReading.reading).label("average"),
                func.min(models.CGMReading.reading).label("minimum"),
                func.max(models.CGMReading.reading).label("maximum"),
                func.count(models.CGMReading.id).label("count"),
            )
            .filter(
                models.CGMReading.user_id == user_id,
                models.CGMReading.timestamp >= cutoff_date,
            )
            .first()
        )

        # Get stats by meal type
        by_meal = {}
        meal_types = ["breakfast", "lunch", "dinner"]
        
        for meal in meal_types:
            meal_stats = (
                db.query(
                    func.avg(models.CGMReading.reading).label("average"),
                    func.count(models.CGMReading.id).label("count"),
                )
                .filter(
                    models.CGMReading.user_id == user_id,
                    models.CGMReading.timestamp >= cutoff_date,
                    models.CGMReading.reading_type == meal,
                )
                .first()
            )
            
            if meal_stats and meal_stats[1] > 0:  # Only include if we have data
                by_meal[meal] = {
                    "average": round(float(meal_stats[0]), 1),
                    "count": meal_stats[1],
                }

        return {
            "average": round(float(stats[0]), 1) if stats[0] is not None else None,
            "minimum": round(float(stats[1]), 1) if stats[1] is not None else None,
            "maximum": round(float(stats[2]), 1) if stats[2] is not None else None,
            "total_readings": stats[3],
            "by_meal_type": by_meal,
        }


class CRUDWellbeingLog(CRUDBase):
    """CRUD operations for WellbeingLog model."""

    def get_multi_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.WellbeingLog]:
        """Get wellbeing logs for a specific user."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(self.model.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_latest_by_user(
        self, db: Session, user_id: int
    ) -> Optional[models.WellbeingLog]:
        """Get the latest wellbeing log for a user."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(self.model.timestamp.desc())
            .first()
        )


class CRUDMealPlan(CRUDBase):
    """CRUD operations for MealPlan model."""

    def get_by_date(
        self, db: Session, user_id: int, date: date
    ) -> Optional[models.MealPlan]:
        """Get a meal plan for a specific date."""
        return (
            db.query(self.model)
            .filter(
                models.MealPlan.user_id == user_id,
                models.MealPlan.created_for_date == date,
            )
            .first()
        )

    def get_multi_by_date_range(
        self, db: Session, user_id: int, start_date: date, end_date: date
    ) -> List[models.MealPlan]:
        """Get meal plans for a date range."""
        return (
            db.query(self.model)
            .filter(
                models.MealPlan.user_id == user_id,
                models.MealPlan.created_for_date >= start_date,
                models.MealPlan.created_for_date <= end_date,
            )
            .order_by(models.MealPlan.created_for_date)
            .all()
        )

    def create_or_update(
        self,
        db: Session,
        *,
        user_id: int,
        date: date,
        breakfast: str,
        lunch: str,
        dinner: str,
    ) -> models.MealPlan:
        """Create or update a meal plan for a specific date."""
        meal_plan = self.get_by_date(db, user_id=user_id, date=date)
        
        if meal_plan:
            # Update existing meal plan
            meal_plan.breakfast = breakfast
            meal_plan.lunch = lunch
            meal_plan.dinner = dinner
        else:
            # Create new meal plan
            meal_plan = models.MealPlan(
                user_id=user_id,
                created_for_date=date,
                breakfast=breakfast,
                lunch=lunch,
                dinner=dinner,
            )
            db.add(meal_plan)
        
        db.commit()
        db.refresh(meal_plan)
        return meal_plan


class CRUDConversationLog(CRUDBase):
    """CRUD operations for ConversationLog model."""

    def get_multi_by_session(
        self, db: Session, session_id: str, limit: int = 100
    ) -> List[models.ConversationLog]:
        """Get conversation logs for a specific session."""
        return (
            db.query(self.model)
            .filter(self.model.session_id == session_id)
            .order_by(self.model.timestamp.asc())
            .limit(limit)
            .all()
        )

    def get_multi_by_user(
        self, db: Session, user_id: int, limit: int = 100
    ) -> List[models.ConversationLog]:
        """Get conversation logs for a specific user."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(self.model.timestamp.desc())
            .limit(limit)
            .all()
        )

    def create(
        self,
        db: Session,
        *,
        user_id: int,
        session_id: str,
        role: str,
        message: str,
        agent_name: Optional[str] = None,
    ) -> models.ConversationLog:
        """Create a new conversation log entry."""
        db_obj = models.ConversationLog(
            user_id=user_id,
            session_id=session_id,
            role=role,
            agent_name=agent_name,
            message=message,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


# Initialize CRUD classes
user = CRUDUser(models.User)
cgm_reading = CRUDCGMReading(models.CGMReading)
wellbeing_log = CRUDWellbeingLog(models.WellbeingLog)
meal_plan = CRUDMealPlan(models.MealPlan)
conversation_log = CRUDConversationLog(models.ConversationLog)
