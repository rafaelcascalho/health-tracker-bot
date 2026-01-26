"""Main entry point for the health tracking bot."""

import logging
import sys
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

import config
from bot.handlers import (
    start_command,
    today_command,
    week_command,
    water_command,
    meal_command,
    cheat_command,
    gym_command,
    weight_command,
    undo_command,
    setup_sheets_command,
    add_week_command,
    add_month_command,
    button_callback,
)
from bot.scheduler import setup_scheduler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def validate_config() -> bool:
    """Validate required configuration."""
    errors = []

    if not config.TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is not set")

    if not config.TELEGRAM_USER_ID:
        errors.append("TELEGRAM_USER_ID is not set")

    if not config.GOOGLE_SHEETS_ID:
        errors.append("GOOGLE_SHEETS_ID is not set")

    try:
        config.get_google_credentials()
    except ValueError as e:
        errors.append(str(e))

    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return False

    return True


def main() -> None:
    """Start the bot."""
    logger.info("Starting Health Tracking Bot...")

    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)

    # Create application
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("week", week_command))
    application.add_handler(CommandHandler("water", water_command))
    application.add_handler(CommandHandler("meal", meal_command))
    application.add_handler(CommandHandler("cheat", cheat_command))
    application.add_handler(CommandHandler("gym", gym_command))
    application.add_handler(CommandHandler("weight", weight_command))
    application.add_handler(CommandHandler("undo", undo_command))
    application.add_handler(CommandHandler("setup_sheets", setup_sheets_command))
    application.add_handler(CommandHandler("add_week", add_week_command))
    application.add_handler(CommandHandler("add_month", add_month_command))

    # Register callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Set up scheduler
    setup_scheduler(application)

    logger.info("Bot configured successfully. Starting polling...")

    # Start the bot
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
