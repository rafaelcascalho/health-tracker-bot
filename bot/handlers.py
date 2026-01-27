"""Command and callback handlers for the health bot."""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import pytz

import config
from bot.sheets import SheetsClient
from bot.points import (
    calculate_daily_points,
    get_max_points_for_day,
    get_meal_type_by_time,
    is_exercise_day,
)
from bot.messages import (
    format_welcome_message,
    format_today_progress,
    format_week_summary,
    format_water_status,
    format_action_confirmation,
    format_milestone_message,
    format_daily_summary,
    format_meal_logged,
)

logger = logging.getLogger(__name__)

# Action names translation (internal -> Portuguese display)
ACTION_NAMES_PT = {
    "wake_7am": "acordar",
    "cardio": "cardio",
    "breakfast": "cafe",
    "lunch": "almoco",
    "snack": "lanche",
    "dinner": "jantar",
    "water_1": "agua1",
    "water_2": "agua2",
    "water_3": "agua3",
    "bedroom": "quarto",
    "bed": "dormir",
    "pilates": "pilates",
    "gym": "academia",
}

# Reverse mapping (Portuguese -> internal)
ACTION_NAMES_EN = {v: k for k, v in ACTION_NAMES_PT.items()}

# All valid action inputs (both PT and EN)
VALID_ACTIONS = list(ACTION_NAMES_PT.keys()) + list(ACTION_NAMES_EN.keys())


def normalize_action(action: str) -> str:
    """Convert action name to internal format (English)."""
    action = action.lower()
    if action in ACTION_NAMES_EN:
        return ACTION_NAMES_EN[action]
    return action


def get_actions_display() -> str:
    """Get formatted list of actions for display."""
    return ", ".join(ACTION_NAMES_PT.values())


def get_sheets_client() -> SheetsClient:
    """Get or create sheets client."""
    return SheetsClient()


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized to use the bot."""
    return user_id == config.TELEGRAM_USER_ID


async def unauthorized_response(update: Update) -> None:
    """Send unauthorized response."""
    await update.message.reply_text("⛔ Não autorizado. Este bot é privado.")


# Command Handlers


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    await update.message.reply_text(format_welcome_message())


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today command - show today's progress."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    try:
        sheets = get_sheets_client()
        data = sheets.get_today_data()
        gym_day = sheets.get_gym_day_choice()
        message = format_today_progress(data, gym_day)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in today_command: {e}")
        await update.message.reply_text("❌ Erro ao buscar dados de hoje.")


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /week command - show weekly summary."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    try:
        sheets = get_sheets_client()
        week_data = sheets.get_week_data()
        gym_day = sheets.get_gym_day_choice()
        message = format_week_summary(week_data, gym_day)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in week_command: {e}")
        await update.message.reply_text("❌ Erro ao buscar dados semanais.")


async def water_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /water command - show water tracker with buttons."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    try:
        sheets = get_sheets_client()
        water_data = sheets.get_water_status()
        message = format_water_status(water_data)
        keyboard = build_water_keyboard(water_data)
        await update.message.reply_text(message, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in water_command: {e}")
        await update.message.reply_text("❌ Erro ao buscar status da água.")


async def meal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /meal <description> command - log a meal."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    if not context.args:
        await update.message.reply_text("Uso: /meal <descrição>\nExemplo: /meal ovos mexidos + torrada")
        return

    description = " ".join(context.args)
    meal_type = get_meal_type_by_time()

    try:
        sheets = get_sheets_client()
        sheets.log_meal(meal_type, description, is_cheat=False)

        # Also mark the meal action as done
        action_map = {"B": "breakfast", "L": "lunch", "S": "snack", "D": "dinner"}
        action = action_map.get(meal_type)
        if action:
            sheets.update_action(action, 1)

        message = format_meal_logged(meal_type, description, is_cheat=False)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in meal_command: {e}")
        await update.message.reply_text("❌ Erro ao registrar refeição.")


async def cheat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cheat <description> command - log a cheat meal."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    if not context.args:
        await update.message.reply_text("Uso: /cheat <descrição>\nExemplo: /cheat pizza e cerveja")
        return

    description = " ".join(context.args)
    meal_type = get_meal_type_by_time()

    try:
        sheets = get_sheets_client()
        sheets.log_meal(meal_type, description, is_cheat=True)
        sheets.increment_cheat_meals()

        message = format_meal_logged(meal_type, description, is_cheat=True)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in cheat_command: {e}")
        await update.message.reply_text("❌ Erro ao registrar cheat meal.")


async def gym_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gym friday|saturday command - set gym day choice."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    valid_days = ("friday", "saturday", "sexta", "sabado", "sábado")
    if not context.args or context.args[0].lower() not in valid_days:
        await update.message.reply_text("Uso: /gym sexta ou /gym sabado")
        return

    day_input = context.args[0].lower()
    # Normalize to English for storage
    if day_input in ("sexta", "friday"):
        day = "friday"
        day_pt = "Sexta"
    else:
        day = "saturday"
        day_pt = "Sábado"

    try:
        sheets = get_sheets_client()
        sheets.set_gym_day_choice(day)
        await update.message.reply_text(f"✓ Dia da academia definido para {day_pt} nesta semana!")
    except Exception as e:
        logger.error(f"Error in gym_command: {e}")
        await update.message.reply_text("❌ Erro ao definir dia da academia.")


async def weight_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /weight <kg> command - log weight."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    if not context.args:
        try:
            sheets = get_sheets_client()
            current = sheets.get_weight()
            if current:
                await update.message.reply_text(f"Peso atual: {current} kg\n\nUso: /weight <kg>")
            else:
                await update.message.reply_text("Nenhum peso registrado ainda.\n\nUso: /weight <kg>")
        except Exception as e:
            logger.error(f"Error getting weight: {e}")
            await update.message.reply_text("Uso: /weight <kg>")
        return

    try:
        weight = float(context.args[0].replace(",", "."))
        sheets = get_sheets_client()
        sheets.log_weight(weight)
        await update.message.reply_text(f"✓ Peso registrado: {weight} kg")
    except ValueError:
        await update.message.reply_text("Por favor, insira um número válido.\nExemplo: /weight 75.5")
    except Exception as e:
        logger.error(f"Error in weight_command: {e}")
        await update.message.reply_text("❌ Erro ao registrar peso.")


async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /undo <action> command - undo last action."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    if not context.args:
        await update.message.reply_text(
            f"Uso: /undo <ação>\nAções disponíveis: {get_actions_display()}"
        )
        return

    action_input = context.args[0].lower()
    action = normalize_action(action_input)

    if action not in ACTION_NAMES_PT:
        await update.message.reply_text(
            f"❌ Ação desconhecida: {action_input}\nAções disponíveis: {get_actions_display()}"
        )
        return

    try:
        sheets = get_sheets_client()
        sheets.update_action(action, 0)
        action_pt = ACTION_NAMES_PT.get(action, action)
        await update.message.reply_text(f"✓ Desfeito: {action_pt}")
    except ValueError as e:
        await update.message.reply_text(f"❌ Ação desconhecida: {action_input}")
    except Exception as e:
        logger.error(f"Error in undo_command: {e}")
        await update.message.reply_text("❌ Erro ao desfazer ação.")


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /done <action> command - manually log an action."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    if not context.args:
        await update.message.reply_text(
            f"Uso: /done <ação>\nAções disponíveis: {get_actions_display()}"
        )
        return

    action_input = context.args[0].lower()
    action = normalize_action(action_input)

    if action not in ACTION_NAMES_PT:
        await update.message.reply_text(
            f"❌ Ação desconhecida: {action_input}\nAções disponíveis: {get_actions_display()}"
        )
        return

    try:
        sheets = get_sheets_client()

        # Check if already done
        current_value = sheets.get_action_value(action)
        if current_value:
            action_pt = ACTION_NAMES_PT.get(action, action)
            await update.message.reply_text(f"✓ {action_pt} já registrado hoje!")
            return

        # Update action
        sheets.update_action(action, 1)

        # Get updated data and calculate points
        data = sheets.get_today_data()
        gym_day = sheets.get_gym_day_choice()

        tz = pytz.timezone(config.TIMEZONE)
        day_of_week = datetime.now(tz).weekday()

        points = calculate_daily_points(data)
        max_pts = get_max_points_for_day(day_of_week, gym_day)

        # Get points for this action
        action_points = config.POINTS.get(action, 1)

        # Format confirmation
        confirmation = format_action_confirmation(
            action,
            action_points,
            points["grand_total"],
            max_pts["total"]
        )

        # Check for milestones
        milestone_msg = ""
        percentage = points["grand_total"] / max_pts["total"] * 100 if max_pts["total"] > 0 else 0

        if percentage >= 100:
            milestone_msg = "\n\n" + format_milestone_message("perfect_day")
        elif percentage >= 50 and (points["grand_total"] - action_points) / max_pts["total"] * 100 < 50:
            milestone_msg = "\n\n" + format_milestone_message("halfway")

        if action == "water_3":
            milestone_msg += "\n" + format_milestone_message("water_hard_mode")

        await update.message.reply_text(confirmation + milestone_msg)

    except Exception as e:
        logger.error(f"Error in done_command: {e}")
        await update.message.reply_text("❌ Erro ao registrar ação.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show all available commands."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    help_text = """📋 *Comandos Disponíveis*

*Progresso:*
/hoje - Ver progresso de hoje
/semana - Ver resumo da semana

*Registrar ações:*
/feito <ação> - Registrar uma ação manualmente
/desfazer <ação> - Desfazer uma ação

*Ações disponíveis:*
acordar, cardio, cafe, almoco, lanche, jantar,
agua1, agua2, agua3, quarto, dormir, pilates, academia

*Refeições:*
/refeicao <descrição> - Registrar refeição
/besteira <descrição> - Registrar cheat meal

*Água e Peso:*
/agua - Ver status da água com botões
/peso <kg> - Registrar peso (ou ver atual)

*Academia:*
/academia sexta - Definir academia para sexta
/academia sabado - Definir academia para sábado

*Administração:*
/add_semana <data> [dia] - Adicionar semana
/add_mes <data> - Adicionar mês
/setup_sheets - Configurar planilhas

*Exemplos:*
• /feito academia
• /feito cardio
• /desfazer cafe
• /refeicao ovos mexidos
• /peso 75.5
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def setup_sheets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setup_sheets command - initialize Weekly_Summary, Monthly_Summary, and Dashboard."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    await update.message.reply_text("Configurando planilhas de análise...")

    try:
        sheets = get_sheets_client()
        results = sheets.setup_all_analysis_sheets()

        # Format results
        status_lines = []
        for sheet_name, status in results.items():
            icon = "✓" if status == "success" else "❌"
            status_text = "sucesso" if status == "success" else status
            status_lines.append(f"{icon} {sheet_name}: {status_text}")

        message = "Configuração concluída:\n\n" + "\n".join(status_lines)
        message += "\n\nNota: Certifique-se de que essas abas já existem na planilha."
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in setup_sheets_command: {e}")
        await update.message.reply_text(f"❌ Erro ao configurar planilhas: {e}")


async def add_week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_week <start_date> [gym_day] - add a new week to Weekly_Summary."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    if not context.args:
        await update.message.reply_text(
            "Uso: /add_week <data_início> [dia_academia]\n"
            "Exemplo: /add_week 2026-01-13 friday"
        )
        return

    start_date = context.args[0]
    gym_choice = context.args[1].lower() if len(context.args) > 1 else ""

    try:
        sheets = get_sheets_client()
        sheets.add_weekly_summary_row(start_date, gym_choice)
        await update.message.reply_text(f"✓ Semana adicionada iniciando em {start_date}")
    except Exception as e:
        logger.error(f"Error in add_week_command: {e}")
        await update.message.reply_text(f"❌ Erro ao adicionar semana: {e}")


async def add_month_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_month <start_date> - add a new month to Monthly_Summary."""
    if not is_authorized(update.effective_user.id):
        await unauthorized_response(update)
        return

    if not context.args:
        await update.message.reply_text(
            "Uso: /add_month <data_início>\n"
            "Exemplo: /add_month 2026-02-01"
        )
        return

    start_date = context.args[0]

    try:
        sheets = get_sheets_client()
        sheets.add_monthly_summary_row(start_date)
        await update.message.reply_text(f"✓ Mês adicionado iniciando em {start_date}")
    except Exception as e:
        logger.error(f"Error in add_month_command: {e}")
        await update.message.reply_text(f"❌ Erro ao adicionar mês: {e}")


# Keyboard Builders


def build_water_keyboard(water_data: dict) -> InlineKeyboardMarkup:
    """Build water tracking keyboard."""
    buttons = []

    if not water_data.get("water_1"):
        buttons.append(InlineKeyboardButton("💧 Garrafa 1", callback_data="action:water_1"))
    if not water_data.get("water_2"):
        buttons.append(InlineKeyboardButton("💧 Garrafa 2", callback_data="action:water_2"))
    if not water_data.get("water_3"):
        buttons.append(InlineKeyboardButton("💧 Garrafa 3", callback_data="action:water_3"))

    # Arrange buttons in rows
    keyboard = []
    for i in range(0, len(buttons), 2):
        keyboard.append(buttons[i:i+2])

    return InlineKeyboardMarkup(keyboard) if keyboard else InlineKeyboardMarkup([])


def build_action_keyboard(action: str) -> InlineKeyboardMarkup:
    """Build single action keyboard."""
    button_labels = {
        "wake_7am": "✓ Acordei",
        "cardio": "✓ Feito",
        "breakfast": "✓ Comi",
        "lunch": "✓ Comi",
        "snack": "✓ Comi",
        "dinner": "✓ Comi",
        "pilates": "✓ Feito",
        "gym": "✓ Feito",
        "bedroom": "✓ Feito",
        "bed": "✓ Feito",
    }

    label = button_labels.get(action, "✓ Feito")
    keyboard = [[InlineKeyboardButton(label, callback_data=f"action:{action}")]]
    return InlineKeyboardMarkup(keyboard)


# Callback Handler


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        await query.edit_message_text("⛔ Não autorizado.")
        return

    data = query.data

    if data.startswith("action:"):
        action = data.split(":")[1]
        await handle_action_callback(query, action)


async def handle_action_callback(query, action: str) -> None:
    """Handle action button callback."""
    try:
        sheets = get_sheets_client()

        # Check if already done
        current_value = sheets.get_action_value(action)
        if current_value:
            await query.edit_message_text(f"✓ {action} já registrado hoje!")
            return

        # Update action
        sheets.update_action(action, 1)

        # Get updated data and calculate points
        data = sheets.get_today_data()
        gym_day = sheets.get_gym_day_choice()

        tz = pytz.timezone(config.TIMEZONE)
        day_of_week = datetime.now(tz).weekday()

        points = calculate_daily_points(data)
        max_pts = get_max_points_for_day(day_of_week, gym_day)

        # Get points for this action
        action_points = config.POINTS.get(action, 1)

        # Format confirmation
        confirmation = format_action_confirmation(
            action,
            action_points,
            points["grand_total"],
            max_pts["total"]
        )

        # Check for milestones
        milestone_msg = ""
        percentage = points["grand_total"] / max_pts["total"] * 100 if max_pts["total"] > 0 else 0

        if percentage >= 100:
            milestone_msg = "\n\n" + format_milestone_message("perfect_day")
        elif percentage >= 50 and (points["grand_total"] - action_points) / max_pts["total"] * 100 < 50:
            milestone_msg = "\n\n" + format_milestone_message("halfway")

        if action == "water_3":
            milestone_msg += "\n" + format_milestone_message("water_hard_mode")

        # Update message
        await query.edit_message_text(confirmation + milestone_msg)

    except Exception as e:
        logger.error(f"Error in handle_action_callback: {e}")
        await query.edit_message_text("❌ Erro ao atualizar ação.")
