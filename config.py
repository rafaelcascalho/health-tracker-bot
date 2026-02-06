import os
import json
from dotenv import load_dotenv

load_dotenv()

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))

# Google Sheets settings
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")

# Google credentials - supports both file path and JSON string
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")


def get_google_credentials():
    """Get Google credentials from file or environment variable."""
    if GOOGLE_CREDENTIALS_JSON:
        return json.loads(GOOGLE_CREDENTIALS_JSON)
    elif GOOGLE_CREDENTIALS_FILE and os.path.exists(GOOGLE_CREDENTIALS_FILE):
        with open(GOOGLE_CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    else:
        raise ValueError(
            "Google credentials not found. Set GOOGLE_CREDENTIALS or GOOGLE_CREDENTIALS_FILE"
        )


# Timezone
TIMEZONE = "America/Sao_Paulo"

# Sheet names
SHEET_DAILY_LOG = "Daily_Log"
SHEET_MEALS_LOG = "Meals_Log"
SHEET_WEEKLY_SUMMARY = "Weekly_Summary"
SHEET_MONTHLY_SUMMARY = "Monthly_Summary"
SHEET_DASHBOARD = "Dashboard"
SHEET_CONFIG = "Config"

# Column mappings for Daily_Log (0-indexed)
DAILY_COLUMNS = {
    "date": 0,  # A
    "day": 1,  # B
    "wake_7am": 2,  # C
    "cardio": 3,  # D
    "breakfast": 4,  # E
    "lunch": 5,  # F
    "snack": 6,  # G
    "dinner": 7,  # H
    "water_1": 8,  # I
    "water_2": 9,  # J
    "water_3": 10,  # K
    "water_copo": 11,  # L (Copo de 300 ml)
    "bedroom": 12,  # M
    "bed": 13,  # N
    "pilates": 14,  # O
    "gym": 15,  # P
    "cheat_meals": 16,  # Q
    "daily_pts": 17,  # R
    "exercise_pts": 18,  # S
    "total_pts": 19,  # T
}

# Points configuration
POINTS = {
    "wake_7am": 1,
    "cardio": 1,
    "breakfast": 1,
    "lunch": 1,
    "snack": 1,
    "dinner": 1,
    "water_1": 1,
    "water_2": 2,
    "water_3": 3,
    "water_copo": 1,
    "bedroom": 1,
    "bed": 1,
    "pilates": 1,
    "gym": 1,
}

# Max daily points (excluding exercise which varies by day)
# Weekday: wake + cardio + 4 meals + 3 water (6 pts) + copo (1 pt) + bedroom + bed = 15
# Weekend: no wake/cardio, so 15 - 2 = 13
MAX_DAILY_POINTS = 15
MAX_DAILY_POINTS_WEEKEND = 13

# Schedule times (24h format)
SCHEDULE = {
    "wake_reminder": "07:00",
    "wake_reminder_weekend": "10:00",
    "cardio_weekday": "07:00",
    "breakfast": "08:00",
    "lunch": "12:00",
    "hydration_check": "14:00",
    "snack": "16:00",
    "exercise": "18:00",
    "dinner": "19:00",
    "water_warning": "19:00",
    "chores": "21:30",
    "bedroom": "22:00",
    "bed": "22:30",
}

# Days for specific activities
PILATES_DAYS = [0, 2]  # Monday, Wednesday (0-indexed from Monday)
GYM_DAYS_FIXED = [1, 3]  # Tuesday, Thursday
GYM_DAYS_CHOICE = [4, 5]  # Friday or Saturday (user chooses)

# Meal time windows (for auto-detection)
MEAL_WINDOWS = {
    "B": (8, 11),  # Breakfast: 8am-11am
    "L": (11, 14),  # Lunch: 11am-2pm
    "S": (14, 17),  # Snack: 2pm-5pm
    "D": (17, 24),  # Dinner: 5pm onwards
}
