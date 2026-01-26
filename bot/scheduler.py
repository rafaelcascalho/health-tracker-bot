"""Scheduler setup and scheduled jobs for the health bot."""

import logging
from datetime import datetime, time, tzinfo
from telegram.ext import Application
import pytz

import config
from bot.sheets import SheetsClient
from bot.handlers import build_action_keyboard, build_water_keyboard
from bot.messages import (
    format_reminder,
    format_water_status,
    format_daily_summary,
)
from bot.points import is_exercise_day

logger = logging.getLogger(__name__)


def get_sheets_client() -> SheetsClient:
    """Get or create sheets client."""
    return SheetsClient()


def parse_time(time_str: str, tz: tzinfo) -> time:
    """Parse time string (HH:MM) to timezone-aware time object."""
    hour, minute = map(int, time_str.split(":"))
    return time(hour=hour, minute=minute, tzinfo=tz)


async def send_reminder(
    context,
    reminder_type: str,
    action: str = None,
    include_keyboard: bool = True,
) -> None:
    """Send a reminder message.

    Args:
        context: Telegram context
        reminder_type: Type of reminder
        action: Action for the keyboard button (optional)
        include_keyboard: Whether to include action button
    """
    try:
        tz = pytz.timezone(config.TIMEZONE)
        is_weekend = datetime.now(tz).weekday() >= 5

        message = format_reminder(reminder_type, is_weekend)

        if include_keyboard and action:
            keyboard = build_action_keyboard(action)
            await context.bot.send_message(
                chat_id=config.TELEGRAM_USER_ID,
                text=message,
                reply_markup=keyboard,
            )
        else:
            await context.bot.send_message(
                chat_id=config.TELEGRAM_USER_ID,
                text=message,
            )
    except Exception as e:
        logger.error(f"Error sending reminder {reminder_type}: {e}")


async def send_water_tracker(context) -> None:
    """Send water tracking message with buttons."""
    try:
        sheets = get_sheets_client()
        water_data = sheets.get_water_status()
        message = format_water_status(water_data)
        keyboard = build_water_keyboard(water_data)

        await context.bot.send_message(
            chat_id=config.TELEGRAM_USER_ID,
            text=message,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Error sending water tracker: {e}")


async def send_water_warning(context) -> None:
    """Send water warning if behind target."""
    try:
        sheets = get_sheets_client()
        water_data = sheets.get_water_status()

        # Check if all bottles are done
        if water_data.get("water_1") and water_data.get("water_2") and water_data.get("water_3"):
            return  # All done, no warning needed

        message = "⚠️ Water reminder! Don't forget to hydrate!\n\n"
        message += format_water_status(water_data)
        keyboard = build_water_keyboard(water_data)

        await context.bot.send_message(
            chat_id=config.TELEGRAM_USER_ID,
            text=message,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Error sending water warning: {e}")


async def send_daily_summary(context) -> None:
    """Send end-of-day summary."""
    try:
        sheets = get_sheets_client()
        data = sheets.get_today_data()
        gym_day = sheets.get_gym_day_choice()
        message = format_daily_summary(data, gym_day)

        await context.bot.send_message(
            chat_id=config.TELEGRAM_USER_ID,
            text=message,
        )
    except Exception as e:
        logger.error(f"Error sending daily summary: {e}")


# Job callbacks for each scheduled reminder


async def wake_reminder_job(context) -> None:
    """7am wake reminder (weekdays only)."""
    tz = pytz.timezone(config.TIMEZONE)
    if datetime.now(tz).weekday() < 5:  # Monday-Friday
        await send_reminder(context, "wake", "wake_7am")


async def cardio_weekday_job(context) -> None:
    """7am cardio reminder (weekdays only)."""
    tz = pytz.timezone(config.TIMEZONE)
    if datetime.now(tz).weekday() < 5:  # Monday-Friday
        await send_reminder(context, "cardio", "cardio")


async def cardio_weekend_job(context) -> None:
    """10am cardio reminder (weekends only)."""
    tz = pytz.timezone(config.TIMEZONE)
    if datetime.now(tz).weekday() >= 5:  # Saturday-Sunday
        await send_reminder(context, "cardio", "cardio")


async def breakfast_job(context) -> None:
    """8am breakfast reminder."""
    await send_reminder(context, "breakfast", "breakfast")


async def lunch_job(context) -> None:
    """12pm lunch reminder."""
    await send_reminder(context, "lunch", "lunch")


async def hydration_job(context) -> None:
    """2pm hydration check."""
    await send_water_tracker(context)


async def snack_job(context) -> None:
    """4pm snack reminder."""
    await send_reminder(context, "snack", "snack")


async def exercise_job(context) -> None:
    """6pm exercise reminder (pilates or gym based on day)."""
    tz = pytz.timezone(config.TIMEZONE)
    day_of_week = datetime.now(tz).weekday()

    try:
        sheets = get_sheets_client()
        gym_day = sheets.get_gym_day_choice()

        if is_exercise_day(day_of_week, "pilates"):
            await send_reminder(context, "pilates", "pilates")
        elif is_exercise_day(day_of_week, "gym", gym_day):
            await send_reminder(context, "gym", "gym")
    except Exception as e:
        logger.error(f"Error in exercise_job: {e}")


async def dinner_job(context) -> None:
    """7pm dinner reminder."""
    await send_reminder(context, "dinner", "dinner")


async def water_warning_job(context) -> None:
    """7pm water warning (if behind)."""
    await send_water_warning(context)


async def chores_job(context) -> None:
    """9:30pm chores reminder (no button)."""
    await send_reminder(context, "chores", include_keyboard=False)


async def bedroom_job(context) -> None:
    """10pm bedroom reminder."""
    await send_reminder(context, "bedroom", "bedroom")


async def bed_job(context) -> None:
    """10:30pm bed reminder with daily summary."""
    await send_reminder(context, "bed", "bed")
    await send_daily_summary(context)


def setup_scheduler(application: Application) -> None:
    """Set up all scheduled jobs.

    Args:
        application: Telegram bot application
    """
    tz = pytz.timezone(config.TIMEZONE)
    job_queue = application.job_queue

    # Parse schedule times with timezone
    times = {k: parse_time(v, tz) for k, v in config.SCHEDULE.items()}

    # Schedule all jobs
    # Wake reminder - 7am weekdays
    job_queue.run_daily(
        wake_reminder_job,
        time=times["wake_reminder"],
        days=(0, 1, 2, 3, 4),  # Mon-Fri
        name="wake_reminder",
    )

    # Cardio weekday - 7am weekdays
    job_queue.run_daily(
        cardio_weekday_job,
        time=times["cardio_weekday"],
        days=(0, 1, 2, 3, 4),  # Mon-Fri
        name="cardio_weekday",
    )

    # Cardio weekend - 10am weekends
    job_queue.run_daily(
        cardio_weekend_job,
        time=times["cardio_weekend"],
        days=(5, 6),  # Sat-Sun
        name="cardio_weekend",
    )

    # Breakfast - 8am daily
    job_queue.run_daily(
        breakfast_job,
        time=times["breakfast"],
        name="breakfast",
    )

    # Lunch - 12pm daily
    job_queue.run_daily(
        lunch_job,
        time=times["lunch"],
        name="lunch",
    )

    # Hydration check - 2pm daily
    job_queue.run_daily(
        hydration_job,
        time=times["hydration_check"],
        name="hydration",
    )

    # Snack - 4pm daily
    job_queue.run_daily(
        snack_job,
        time=times["snack"],
        name="snack",
    )

    # Exercise - 6pm (varies by day)
    job_queue.run_daily(
        exercise_job,
        time=times["exercise"],
        name="exercise",
    )

    # Dinner - 7pm daily
    job_queue.run_daily(
        dinner_job,
        time=times["dinner"],
        name="dinner",
    )

    # Water warning - 7pm daily
    job_queue.run_daily(
        water_warning_job,
        time=times["water_warning"],
        name="water_warning",
    )

    # Chores - 9:30pm daily
    job_queue.run_daily(
        chores_job,
        time=times["chores"],
        name="chores",
    )

    # Bedroom - 10pm daily
    job_queue.run_daily(
        bedroom_job,
        time=times["bedroom"],
        name="bedroom",
    )

    # Bed - 10:30pm daily
    job_queue.run_daily(
        bed_job,
        time=times["bed"],
        name="bed",
    )

    logger.info("Scheduler set up with all daily jobs")
