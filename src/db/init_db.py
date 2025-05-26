"""Initialize the database with sample data."""

# Standard library imports
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

# Third-party imports
from faker import Faker
from sqlalchemy.orm import Session

# Local application imports
from . import crud, models, schemas
from .database import SessionLocal, init_db

# Initialize Faker
fake = Faker()


# Sample data generators
def generate_sample_users(count: int = 100) -> List[schemas.UserCreate]:
    """Generate sample user data with predictable test cases."""
    users = []
    dietary_prefs = ["vegetarian", "non-vegetarian", "vegan"]
    medical_conditions = [
        "None",
        "Type 2 diabetes",
        "Hypertension",
        "High cholesterol",
        "Heart disease",
        "Asthma",
        "Arthritis",
    ]
    physical_limitations = [
        "None",
        "Mobility issues",
        "Visual impairment",
        "Hearing impairment",
        "Limited dexterity",
    ]

    # First 5 users are predictable test cases
    test_users = [
        {
            "first_name": "Sanjoy",
            "last_name": "Ghosh",
            "city": "Bangalore",
            "email": "sanjoy.ghosh@example.com",
            "date_of_birth": "1990-05-15",
            "dietary_preference": "vegetarian",
            "medical_conditions": "Type 2 diabetes",
            "physical_limitations": "None",
        },
        {
            "first_name": "Jane",
            "last_name": "Smith",
            "city": "Mumbai",
            "email": "jane.smith@example.com",
            "date_of_birth": "1985-08-22",
            "dietary_preference": "non-vegetarian",
            "medical_conditions": "None",
            "physical_limitations": "None",
        },
        {
            "first_name": "Alice",
            "last_name": "Johnson",
            "city": "Delhi",
            "email": "alice.johnson@example.com",
            "date_of_birth": "1978-03-10",
            "dietary_preference": "vegan",
            "medical_conditions": "Type 2 diabetes, Hypertension",
            "physical_limitations": "Mobility issues",
        },
        {
            "first_name": "Bob",
            "last_name": "Wilson",
            "city": "Chennai",
            "email": "bob.wilson@example.com",
            "date_of_birth": "1995-11-30",
            "dietary_preference": "vegetarian",
            "medical_conditions": "High cholesterol",
            "physical_limitations": "None",
        },
        {
            "first_name": "Emma",
            "last_name": "Davis",
            "city": "Pune",
            "email": "emma.davis@example.com",
            "date_of_birth": "1982-07-18",
            "dietary_preference": "non-vegetarian",
            "medical_conditions": "Type 2 diabetes, Heart disease",
            "physical_limitations": "Visual impairment",
        },
    ]

    # Add test users
    for user_data in test_users:
        # Convert date string to date object
        user_data["date_of_birth"] = datetime.strptime(
            user_data["date_of_birth"], "%Y-%m-%d"
        ).date()
        users.append(schemas.UserCreate(**user_data))

    # Generate remaining random users
    for i in range(len(test_users), count):
        first_name = fake.first_name()
        last_name = fake.last_name()
        # Ensure unique email
        email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"

        # Generate conditions and limitations
        num_conditions = random.choices([0, 1, 2], weights=[0.4, 0.4, 0.2])[0]
        conditions = random.sample(medical_conditions, num_conditions)
        conditions = [c for c in conditions if c != "None"]

        num_limitations = random.choices([0, 1], weights=[0.8, 0.2])[0]
        limitations = random.sample(physical_limitations, num_limitations)
        limitations = [limitation for limitation in limitations if limitation != "None"]

        user = schemas.UserCreate(
            first_name=first_name,
            last_name=last_name,
            city=fake.city(),
            email=email,
            date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=90),
            dietary_preference=random.choice(dietary_prefs),
            medical_conditions=", ".join(conditions) or None,
            physical_limitations=", ".join(limitations) or None,
        )
        users.append(user)

    return users


def _get_reading_base_and_variance(
    reading_type: str, is_diabetic: bool
) -> tuple[float, float]:
    """Get base and variance for a reading based on type and diabetic status."""
    if is_diabetic:
        # Diabetic patients: higher and more variable
        if reading_type == "breakfast":
            return random.uniform(130, 180), random.uniform(-20, 30)
        if reading_type == "lunch":
            return random.uniform(150, 200), random.uniform(-30, 40)
        # dinner
        return random.uniform(140, 190), random.uniform(-25, 35)

    # Non-diabetic: mostly normal range
    if reading_type == "breakfast":
        return random.uniform(80, 100), random.uniform(-10, 10)
    if reading_type == "lunch":
        return random.uniform(90, 120), random.uniform(-10, 20)
    # dinner
    return random.uniform(85, 115), random.uniform(-10, 15)


def _add_reading_variation(base: float, variance: float, is_diabetic: bool) -> float:
    """Add random variation to a reading based on diabetic status."""
    if random.random() < 0.05:  # 5% chance of unusual reading
        if is_diabetic:
            variance += random.choice([-50, 60])  # Bigger swings
        else:
            variance += random.choice([-20, 30])  # Smaller swings
    return round(max(50, min(350, base + variance)), 1)


def _create_cgm_reading(
    db: Session, user_id: int, reading_type: str, timestamp: datetime, reading: float
) -> None:
    """Create and save a single CGM reading.

    Args:
        db: Database session
        user_id: ID of the user
        reading_type: Type of reading (breakfast, lunch, dinner)
        timestamp: When the reading was taken
        reading: The blood glucose reading value
    """
    cgm_reading = schemas.CGMReadingCreate(
        user_id=user_id, reading=reading, reading_type=reading_type, timestamp=timestamp
    )
    crud.cgm_reading.create(db, obj_in=cgm_reading)


def _generate_readings_for_day(
    db: Session, user_id: int, date: datetime, is_diabetic: bool
) -> None:
    """Generate readings for a single day."""
    reading_times = [8, 13, 20]  # 8am, 1pm, 8pm

    for i, reading_type in enumerate(["breakfast", "lunch", "dinner"]):
        # Create timestamp for the reading
        ts = date.replace(
            hour=reading_times[i], minute=random.randint(0, 59), second=0, microsecond=0
        )

        # Get base reading and variance
        base, variance = _get_reading_base_and_variance(reading_type, is_diabetic)

        # Add variation and clamp to valid range
        reading = _add_reading_variation(base, variance, is_diabetic)

        # Create and save the reading with the calculated value
        _create_cgm_reading(db, user_id, reading_type, ts, reading)


def generate_cgm_readings(
    db: Session, user_ids: List[int], days_back: int = 30
) -> None:
    """Generate realistic CGM readings based on medical conditions."""
    now = datetime.now(timezone.utc)

    # Get all users' medical conditions in one query for efficiency
    users = db.query(models.User).filter(models.User.id.in_(user_ids)).all()
    user_conditions = {
        user.id: "diabetes" in (user.medical_conditions or "").lower() for user in users
    }

    for user_id, is_diabetic in user_conditions.items():
        for day in range(days_back):
            date = now - timedelta(days=day)
            _generate_readings_for_day(db, user_id, date, is_diabetic)


def generate_wellbeing_logs(
    db: Session, user_ids: List[int], days_back: int = 30
) -> None:
    """Generate sample wellbeing logs."""
    feelings = [
        "Feeling great!",
        "A bit tired today.",
        "Very energetic!",
        "Not feeling my best.",
        "Feeling motivated!",
        "A bit stressed out.",
        "Really happy today!",
        "Could be better.",
        "Feeling optimistic!",
        "A bit under the weather.",
    ]

    now = datetime.utcnow()

    for user_id in user_ids:
        # Generate logs for the last 'days_back' days
        for day in range(days_back):
            # 70% chance of a log on any given day
            if random.random() < 0.7:
                log_date = now - timedelta(days=day)
                # Random time during the day
                log_time = log_date.replace(
                    hour=random.randint(8, 20),  # Between 8 AM and 8 PM
                    minute=random.randint(0, 59),
                    second=0,
                    microsecond=0,
                )

                log = schemas.WellbeingLogCreate(
                    user_id=user_id, feeling=random.choice(feelings), timestamp=log_time
                )
                crud.wellbeing_log.create(db, obj_in=log)


def display_test_users(db: Session, limit: int = 5) -> None:
    """Display test users for reference."""
    users = db.query(models.User).order_by(models.User.id).limit(limit).all()

    print("\n" + "=" * 80)
    print("TEST USERS FOR DEMO:")
    print("=" * 80)

    for user in users:
        print(f"\nID: {user.id}")
        print(f"Name: {user.first_name} {user.last_name}")
        print(f"Email: {user.email}")
        print(f"Diet: {user.dietary_preference or 'Not specified'}")
        print(f"Conditions: {user.medical_conditions or 'None'}")
        print(f"Limitations: {user.physical_limitations or 'None'}")

    print("\n" + "=" * 80)


def main() -> None:
    """Initialize the database with sample data."""
    # Create database directory if it doesn't exist
    db_path = Path("db")
    db_path.mkdir(exist_ok=True)

    # Initialize the database (creates tables)
    print("Initializing database...")
    init_db()

    db = SessionLocal()
    try:
        # Generate sample users
        print("Generating sample users...")
        users = generate_sample_users(20)  # Generate 20 users for demo
        user_ids = []

        for user in users:
            db_user = crud.user.create(db, obj_in=user)
            user_ids.append(db_user.id)

        print(f"Generated {len(user_ids)} users.")

        # Generate CGM readings
        print("Generating CGM readings...")
        generate_cgm_readings(db, user_ids, days_back=30)

        # Generate wellbeing logs
        print("Generating wellbeing logs...")
        generate_wellbeing_logs(db, user_ids, days_back=30)

        # Display test users for reference
        display_test_users(db)

        print("\n✅ Database initialization complete!")
        print(f"Database location: {db_path.absolute()}/health_assistant.db")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
