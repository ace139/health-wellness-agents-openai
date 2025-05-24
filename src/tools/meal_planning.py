"""Meal planning tools for the health and wellness assistant."""
# Standard library imports
from datetime import date, timedelta
from typing import Dict, Optional

# Third-party imports
from openai_agents import function_tool
from sqlalchemy.orm import Session

# Local application imports
from db import crud

# Relative imports
from .utils import (
    format_error_response,
    format_success_response,
    sanitize_string,
    validate_user_id,
)

# Constants
MAX_MEAL_LENGTH = 500


def parse_plan_date(date_str: Optional[str] = None) -> Optional[date]:
    """Parse a date string or return tomorrow's date if None."""
    try:
        if date_str:
            return date.fromisoformat(date_str)
        return date.today() + timedelta(days=1)
    except (ValueError, TypeError):
        return None


@function_tool
def save_meal_plan(
    db: Session,
    user_id: int,
    breakfast: str,
    lunch: str,
    dinner: str,
    plan_date: Optional[str] = None
) -> Dict:
    """
    Save a generated meal plan with validation.
    
    Args:
        db: Database session
        user_id: Valid user ID
        breakfast: Breakfast plan (max 500 chars)
        lunch: Lunch plan (max 500 chars)
        dinner: Dinner plan (max 500 chars)
        plan_date: Optional date for the plan (YYYY-MM-DD), defaults to tomorrow
        
    Returns:
        Dict with success/error status
    """
    # Validate inputs
    validated_id = validate_user_id(user_id)
    if not validated_id:
        return format_error_response("Invalid user ID")
    
    # Sanitize meal descriptions
    
    # Parse plan date or default to tomorrow
    plan_date_obj = parse_plan_date(plan_date)
    if not plan_date_obj:
        return format_error_response("Invalid date format. Please use YYYY-MM-DD")
        
    # Sanitize meal descriptions
    breakfast = sanitize_string(breakfast, MAX_MEAL_LENGTH) if breakfast else ""
    lunch = sanitize_string(lunch, MAX_MEAL_LENGTH) if lunch else ""
    dinner = sanitize_string(dinner, MAX_MEAL_LENGTH) if dinner else ""
    
    if not all([breakfast, lunch, dinner]):
        return format_error_response("All meal descriptions are required")
    
    try:
        # Create or update meal plan
        meal_plan = crud.meal_plan.create_or_update(
            db=db,
            user_id=validated_id,
            date=plan_date_obj,
            breakfast=breakfast,
            lunch=lunch,
            dinner=dinner
        )
        
        return format_success_response(
            message=f"Meal plan saved for {plan_date_obj}",
            plan_id=meal_plan.id,
            date=plan_date_obj.isoformat()
        )
    except Exception as e:
        return format_error_response(f"Failed to save meal plan: {str(e)}")


@function_tool
def get_meal_plan(
    db: Session,
    user_id: int,
    plan_date: Optional[str] = None
) -> Dict:
    """
    Get a meal plan for a specific date.
    
    Args:
        db: Database session
        user_id: Valid user ID
        plan_date: Optional date for the plan (YYYY-MM-DD), defaults to today
        
    Returns:
        Dict with meal plan or error message
    """
    # Validate inputs
    validated_id = validate_user_id(user_id)
    if not validated_id:
        return {"error": "Invalid user ID"}
    
    # Parse plan date or default to today
    try:
        if plan_date:
            plan_date_obj = date.fromisoformat(plan_date)
        else:
            plan_date_obj = date.today()
    except (ValueError, TypeError):
        return format_error_response("Invalid date format. Please use YYYY-MM-DD")
    
    try:
        # Get meal plan
        meal_plan = crud.meal_plan.get_by_date(
            db=db,
            user_id=validated_id,
            date=plan_date_obj
        )
        
        if not meal_plan:
            return format_success_response(
                message=f"No meal plan found for {plan_date_obj}",
                has_plan=False
            )
        
        return format_success_response(
            has_plan=True,
            date=plan_date_obj.isoformat(),
            meal_plan={
                "breakfast": meal_plan.breakfast,
                "lunch": meal_plan.lunch,
                "dinner": meal_plan.dinner,
                "created_at": meal_plan.created_at.isoformat(),
                "updated_at": (
                    meal_plan.updated_at.isoformat() 
                    if meal_plan.updated_at else None
                )
            }
        )
    except Exception as e:
        return format_error_response(f"Failed to get meal plan: {str(e)}")
