"""Point calculation logic for health tracking."""

from datetime import datetime
from typing import Optional
import pytz

import config


def calculate_daily_points(data: dict) -> dict:
    """Calculate points breakdown for a day.

    Args:
        data: Dictionary with action values

    Returns:
        Dictionary with point breakdown
    """
    points = {
        "wake_7am": data.get("wake_7am", 0) * config.POINTS["wake_7am"],
        "cardio": data.get("cardio", 0) * config.POINTS["cardio"],
        "breakfast": data.get("breakfast", 0) * config.POINTS["breakfast"],
        "lunch": data.get("lunch", 0) * config.POINTS["lunch"],
        "snack": data.get("snack", 0) * config.POINTS["snack"],
        "dinner": data.get("dinner", 0) * config.POINTS["dinner"],
        "water_1": data.get("water_1", 0) * config.POINTS["water_1"],
        "water_2": data.get("water_2", 0) * config.POINTS["water_2"],
        "water_3": data.get("water_3", 0) * config.POINTS["water_3"],
        "bedroom": data.get("bedroom", 0) * config.POINTS["bedroom"],
        "bed": data.get("bed", 0) * config.POINTS["bed"],
        "pilates": data.get("pilates", 0) * config.POINTS["pilates"],
        "gym": data.get("gym", 0) * config.POINTS["gym"],
    }

    points["daily_total"] = (
        points["wake_7am"]
        + points["cardio"]
        + points["breakfast"]
        + points["lunch"]
        + points["snack"]
        + points["dinner"]
        + points["water_1"]
        + points["water_2"]
        + points["water_3"]
        + points["bedroom"]
        + points["bed"]
    )

    points["exercise_total"] = points["pilates"] + points["gym"]
    points["grand_total"] = points["daily_total"] + points["exercise_total"]

    return points


def get_max_points_for_day(day_of_week: int, gym_day_choice: Optional[str] = None) -> dict:
    """Get maximum possible points for a specific day.

    Args:
        day_of_week: 0=Monday, 6=Sunday
        gym_day_choice: 'friday' or 'saturday' for gym day

    Returns:
        Dictionary with max points breakdown
    """
    max_pts = {
        "daily": config.MAX_DAILY_POINTS,
        "exercise": 0,
        "total": config.MAX_DAILY_POINTS,
    }

    # Pilates days (Monday, Wednesday)
    if day_of_week in config.PILATES_DAYS:
        max_pts["exercise"] = 1
        max_pts["total"] += 1

    # Gym days (Tuesday, Thursday + Friday or Saturday)
    gym_days = list(config.GYM_DAYS_FIXED)
    if gym_day_choice == "friday":
        gym_days.append(4)
    elif gym_day_choice == "saturday":
        gym_days.append(5)

    if day_of_week in gym_days:
        max_pts["exercise"] = 1
        max_pts["total"] += 1

    return max_pts


def calculate_week_max_points(gym_day_choice: Optional[str] = None) -> int:
    """Calculate maximum weekly points.

    Weekly breakdown:
    - Daily points: 14 * 7 = 98
    - Pilates (Mon/Wed): 2
    - Gym (Tue/Thu + 1): 3

    Total: 103

    Args:
        gym_day_choice: 'friday' or 'saturday'

    Returns:
        Maximum possible weekly points (103)
    """
    return 103  # Fixed: 98 daily + 2 pilates + 3 gym


def calculate_cheat_penalty(cheat_count: int) -> int:
    """Calculate penalty for cheat meals.

    Current rule: 3 pts penalty per cheat meal.

    Args:
        cheat_count: Number of cheat meals this week

    Returns:
        Total penalty points
    """
    return cheat_count * 3


def get_progress_status(percentage: float) -> str:
    """Get status label based on percentage.

    Args:
        percentage: Percentage of max points (0-100)

    Returns:
        Status label
    """
    if percentage >= 100:
        return "Perfect"
    elif percentage >= 85:
        return "Successful"
    elif percentage >= 70:
        return "Needs Improvement"
    else:
        return "Danger"


def get_category_breakdown(data: dict) -> dict:
    """Get breakdown by category.

    Categories:
    - Sleep: wake_7am, bedroom, bed (3 pts max)
    - Nutrition: breakfast, lunch, snack, dinner (4 pts max)
    - Hydration: water_1, water_2, water_3 (6 pts max)
    - Cardio: cardio (1 pt max)
    - Exercise: pilates, gym (1 pt max per day)

    Args:
        data: Daily data dictionary

    Returns:
        Dictionary with category scores
    """
    return {
        "sleep": {
            "current": (
                data.get("wake_7am", 0)
                + data.get("bedroom", 0)
                + data.get("bed", 0)
            ),
            "max": 3,
            "items": {
                "wake_7am": data.get("wake_7am", 0),
                "bedroom": data.get("bedroom", 0),
                "bed": data.get("bed", 0),
            },
        },
        "nutrition": {
            "current": (
                data.get("breakfast", 0)
                + data.get("lunch", 0)
                + data.get("snack", 0)
                + data.get("dinner", 0)
            ),
            "max": 4,
            "items": {
                "breakfast": data.get("breakfast", 0),
                "lunch": data.get("lunch", 0),
                "snack": data.get("snack", 0),
                "dinner": data.get("dinner", 0),
            },
        },
        "hydration": {
            "current": (
                data.get("water_1", 0)
                + data.get("water_2", 0) * 2
                + data.get("water_3", 0) * 3
            ),
            "max": 6,
            "items": {
                "water_1": data.get("water_1", 0),
                "water_2": data.get("water_2", 0),
                "water_3": data.get("water_3", 0),
            },
        },
        "cardio": {
            "current": data.get("cardio", 0),
            "max": 1,
            "items": {"cardio": data.get("cardio", 0)},
        },
        "exercise": {
            "current": data.get("pilates", 0) + data.get("gym", 0),
            "max": 1,  # Per day
            "items": {
                "pilates": data.get("pilates", 0),
                "gym": data.get("gym", 0),
            },
        },
    }


def is_exercise_day(day_of_week: int, exercise_type: str, gym_day_choice: Optional[str] = None) -> bool:
    """Check if today is a day for a specific exercise.

    Args:
        day_of_week: 0=Monday, 6=Sunday
        exercise_type: 'pilates' or 'gym'
        gym_day_choice: 'friday' or 'saturday'

    Returns:
        True if exercise is scheduled for this day
    """
    if exercise_type == "pilates":
        return day_of_week in config.PILATES_DAYS

    if exercise_type == "gym":
        gym_days = list(config.GYM_DAYS_FIXED)
        if gym_day_choice == "friday":
            gym_days.append(4)
        elif gym_day_choice == "saturday":
            gym_days.append(5)
        return day_of_week in gym_days

    return False


def get_meal_type_by_time(hour: Optional[int] = None) -> str:
    """Determine meal type based on current time.

    Args:
        hour: Hour of day (0-23), uses current time if None

    Returns:
        Meal type: B, L, S, or D
    """
    if hour is None:
        tz = pytz.timezone(config.TIMEZONE)
        hour = datetime.now(tz).hour

    for meal_type, (start, end) in config.MEAL_WINDOWS.items():
        if start <= hour < end:
            return meal_type

    return "D"  # Default to dinner
