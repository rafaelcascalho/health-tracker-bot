"""Message templates and builders for the health bot."""

from datetime import datetime
from typing import Optional
import pytz

import config
from bot.points import (
    calculate_daily_points,
    get_category_breakdown,
    get_max_points_for_day,
    get_progress_status,
    calculate_week_max_points,
)


def format_checkmark(done: bool) -> str:
    """Format a checkmark based on completion status."""
    return "✓" if done else "○"


def format_water_status(water_data: dict) -> str:
    """Format water tracking status."""
    w1 = water_data.get("water_1", 0)
    w2 = water_data.get("water_2", 0)
    w3 = water_data.get("water_3", 0)
    wc = water_data.get("water_copo", 0)
    total_pts = w1 + w2 * 2 + w3 * 3 + wc

    lines = [
        "💧 Hidratação",
        "━━━━━━━━━━━━━━━━━",
        f"[{format_checkmark(w1)}] Garrafa 1 (+1 pt)",
        f"[{format_checkmark(w2)}] Garrafa 2 (+2 pts)",
        f"[{format_checkmark(w3)}] Garrafa 3 (+3 pts) ⏰ antes das 20h",
        f"[{format_checkmark(wc)}] Copo de 300 ml (+1 pt)",
        "",
        f"Progresso: {total_pts}/7 pts",
    ]

    return "\n".join(lines)


def format_daily_summary(data: dict, gym_day_choice: Optional[str] = None) -> str:
    """Format end-of-day summary."""
    tz = pytz.timezone(config.TIMEZONE)
    today = datetime.now(tz)
    date_str = today.strftime("%d/%m")
    day_of_week = today.weekday()

    categories = get_category_breakdown(data, day_of_week)
    points = calculate_daily_points(data)
    max_pts = get_max_points_for_day(day_of_week, gym_day_choice)
    is_weekend = day_of_week >= 5

    # Build sleep line
    sleep = categories["sleep"]
    sleep_parts = []
    if not is_weekend:
        sleep_parts.append(format_checkmark(sleep["items"].get("wake_7am", 0)))
    sleep_parts.append(format_checkmark(sleep["items"]["bedroom"]))
    sleep_parts.append(format_checkmark(sleep["items"]["bed"]))
    sleep_checks = "".join(sleep_parts)

    # Build nutrition line
    nutrition = categories["nutrition"]
    nutrition_checks = "".join([
        format_checkmark(nutrition["items"]["breakfast"]),
        format_checkmark(nutrition["items"]["lunch"]),
        format_checkmark(nutrition["items"]["snack"]),
        format_checkmark(nutrition["items"]["dinner"]),
    ])

    # Build hydration line
    hydration = categories["hydration"]
    hydration_checks = "".join([
        format_checkmark(hydration["items"]["water_1"]),
        format_checkmark(hydration["items"]["water_2"]),
        format_checkmark(hydration["items"]["water_3"]),
        format_checkmark(hydration["items"]["water_copo"]),
    ])

    # Build cardio line
    cardio = categories["cardio"]
    cardio_check = format_checkmark(cardio["items"]["cardio"])

    # Build exercise line
    exercise = categories["exercise"]
    exercise_str = ""
    if exercise["items"]["pilates"]:
        exercise_str = "🧘 Pilates"
    elif exercise["items"]["gym"]:
        exercise_str = "🏋️ Academia"
    else:
        exercise_str = "—"

    # Calculate totals
    daily_total = points["grand_total"]
    max_total = max_pts["total"]

    # Perfect day check
    is_perfect = daily_total >= max_total
    status_emoji = "⭐ PERFEITO!" if is_perfect else ""

    lines = [
        f"📊 Resumo do Dia - {date_str}",
        "",
        f"Sono:       {sleep_checks} ({sleep['current']}/{sleep['max']})",
        f"Nutrição:   {nutrition_checks} ({nutrition['current']}/{nutrition['max']})",
        f"Hidratação: {hydration_checks} ({hydration['current']}/{hydration['max']})",
    ]

    if not is_weekend:
        lines.append(f"Cardio:     {cardio_check} ({cardio['current']}/{cardio['max']})")

    lines.extend([
        f"Exercício:  {exercise_str} ({exercise['current']}/{max_pts['exercise']})",
        "",
        f"Total: {daily_total}/{max_total} pts {status_emoji}",
    ])

    return "\n".join(lines)


def format_week_summary(week_data: list[dict], gym_day_choice: Optional[str] = None) -> str:
    """Format weekly summary."""
    if not week_data:
        return "📊 Sem dados para essa semana ainda."

    tz = pytz.timezone(config.TIMEZONE)
    today = datetime.now(tz)

    total_points = 0
    total_cheat = 0
    days_logged = len(week_data)

    for day_data in week_data:
        points = calculate_daily_points(day_data)
        total_points += points["grand_total"]
        total_cheat += day_data.get("cheat_meals", 0)

    max_weekly = calculate_week_max_points(gym_day_choice)
    cheat_penalty = total_cheat * 3
    final_score = max(0, total_points - cheat_penalty)
    percentage = (final_score / max_weekly) * 100 if max_weekly > 0 else 0
    status = get_progress_status(percentage)

    # Translate status
    status_pt = {
        "Perfect": "Perfeito",
        "Successful": "Sucesso",
        "Needs Improvement": "Precisa Melhorar",
        "Danger": "Perigo",
    }.get(status, status)

    lines = [
        f"📊 Resumo Semanal",
        f"━━━━━━━━━━━━━━━━━",
        f"Dias registrados: {days_logged}/7",
        f"Pontos brutos: {total_points}",
        f"Cheat meals: {total_cheat} (-{cheat_penalty} pts)",
        f"Pontuação final: {final_score}/{max_weekly}",
        f"Progresso: {percentage:.1f}%",
        f"Status: {status_pt}",
    ]

    return "\n".join(lines)


def _get_day_name_pt(day_of_week: int) -> str:
    """Get Portuguese day name."""
    days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    return days[day_of_week]


def format_today_progress(data: dict, gym_day_choice: Optional[str] = None) -> str:
    """Format today's progress overview."""
    tz = pytz.timezone(config.TIMEZONE)
    today = datetime.now(tz)
    day_of_week = today.weekday()
    day_name = _get_day_name_pt(day_of_week)

    points = calculate_daily_points(data)
    max_pts = get_max_points_for_day(day_of_week, gym_day_choice)

    current = points["grand_total"]
    maximum = max_pts["total"]
    percentage = (current / maximum) * 100 if maximum > 0 else 0

    lines = [
        f"📈 Progresso de Hoje ({day_name})",
        f"━━━━━━━━━━━━━━━━━",
        "",
    ]

    # List completed items
    completed = []
    pending = []

    is_weekend = day_of_week >= 5

    actions = []
    if not is_weekend:
        actions.append(("wake_7am", "Acordar às 7h", data.get("wake_7am", 0)))
        actions.append(("cardio", "Cardio", data.get("cardio", 0)))
    actions.extend([
        ("breakfast", "Café da manhã", data.get("breakfast", 0)),
        ("lunch", "Almoço", data.get("lunch", 0)),
        ("snack", "Lanche", data.get("snack", 0)),
        ("dinner", "Jantar", data.get("dinner", 0)),
        ("water_1", "Água #1", data.get("water_1", 0)),
        ("water_2", "Água #2", data.get("water_2", 0)),
        ("water_3", "Água #3", data.get("water_3", 0)),
        ("water_copo", "Copo de 300 ml", data.get("water_copo", 0)),
        ("bedroom", "Quarto às 22h", data.get("bedroom", 0)),
        ("bed", "Cama às 22:30", data.get("bed", 0)),
    ])

    # Add exercise based on day
    if day_of_week in config.PILATES_DAYS:
        actions.append(("pilates", "Pilates", data.get("pilates", 0)))
    if day_of_week in config.GYM_DAYS_FIXED:
        actions.append(("gym", "Academia", data.get("gym", 0)))
    elif gym_day_choice == "friday" and day_of_week == 4:
        actions.append(("gym", "Academia", data.get("gym", 0)))
    elif gym_day_choice == "saturday" and day_of_week == 5:
        actions.append(("gym", "Academia", data.get("gym", 0)))

    for _, name, done in actions:
        if done:
            completed.append(f"✓ {name}")
        else:
            pending.append(f"○ {name}")

    if completed:
        lines.append("Concluído:")
        lines.extend([f"  {item}" for item in completed])
        lines.append("")

    if pending:
        lines.append("Pendente:")
        lines.extend([f"  {item}" for item in pending])
        lines.append("")

    lines.append(f"Progresso: {current}/{maximum} pts ({percentage:.0f}%)")

    return "\n".join(lines)


def format_action_confirmation(
    action: str,
    points_earned: int,
    current_total: int,
    max_total: int,
) -> str:
    """Format confirmation message after action completion."""
    action_names = {
        "wake_7am": "Acordar cedo",
        "cardio": "Cardio",
        "breakfast": "Café da manhã",
        "lunch": "Almoço",
        "snack": "Lanche",
        "dinner": "Jantar",
        "water_1": "Água #1",
        "water_2": "Água #2",
        "water_3": "Água #3 (modo difícil!)",
        "water_copo": "Copo de 300 ml",
        "bedroom": "Hora do quarto",
        "bed": "Hora de dormir",
        "pilates": "Pilates",
        "gym": "Academia",
    }

    name = action_names.get(action, action)
    return f"✓ {name} feito! +{points_earned} pt{'s' if points_earned > 1 else ''} ({current_total}/{max_total} hoje)"


def format_milestone_message(milestone: str) -> str:
    """Format milestone celebration message."""
    messages = {
        "halfway": "Metade do caminho! 💪",
        "perfect_day": "DIA PERFEITO! 🎉 Pontuação máxima!",
        "water_hard_mode": "Modo difícil completo! 💧🔥 +3 pts",
        "gym_streak": "Consistência na academia! 🏋️",
    }
    return messages.get(milestone, "")


def format_reminder(reminder_type: str, is_weekend: bool = False) -> str:
    """Format a reminder message."""
    reminders = {
        "wake": "⏰ Bom dia! Hora de levantar!",
        "cardio": "🏃 Hora do cardio! Bora se mexer!",
        "cardio_weekend": "🏃 Cardio de fim de semana! Comece o dia ativo!",
        "breakfast": "🍳 Hora do café da manhã! Alimente-se bem!",
        "lunch": "🍽️ Hora do almoço! Faça uma pausa e coma bem.",
        "snack": "🍎 Hora do lanche! Mantenha a energia.",
        "dinner": "🍲 Hora do jantar! Hora da refeição noturna.",
        "pilates": "🧘 Hora do pilates! Alongar e fortalecer.",
        "gym": "🏋️ Hora da academia! Bora treinar!",
        "hydration": "💧 Check de hidratação! Como está a água?",
        "water_warning": "⚠️ Lembrete de água! Não esqueça de se hidratar!",
        "chores": "🏠 Lembrete de tarefas! Organize antes de dormir.",
        "bedroom": "🌙 Hora do quarto! Comece a relaxar.",
        "bed": "😴 Hora de dormir! Descanse bem.",
    }

    if reminder_type == "cardio" and is_weekend:
        reminder_type = "cardio_weekend"

    return reminders.get(reminder_type, f"Lembrete: {reminder_type}")


def format_welcome_message() -> str:
    """Format welcome message for new users."""
    return """
👋 Bem-vindo ao Health Tracker Bot!

Vou te ajudar a acompanhar seus hábitos diários e ganhar pontos por:

🛏️ Sono (3 pts)
- Acordar às 7h
- No quarto às 22h
- Na cama às 22:30

🍽️ Nutrição (4 pts)
- Café da manhã, Almoço, Lanche, Jantar

💧 Hidratação (7 pts)
- Garrafa 1: +1 pt
- Garrafa 2: +2 pts
- Garrafa 3: +3 pts (antes das 20h)
- Copo de 300 ml: +1 pt

🏃 Cardio (1 pt)
- Sessão diária (seg-sex)
- Sem cardio nos fins de semana

🏋️ Exercício (varia)
- Pilates: Seg/Qua
- Academia: Ter/Qui + Sex OU Sáb

Comandos:
/today - Progresso de hoje
/week - Resumo semanal
/water - Acompanhar água
/meal <comida> - Registrar refeição
/cheat <comida> - Registrar cheat meal
/gym friday|saturday - Definir dia da academia
/weight <kg> - Registrar peso

Vamos ficar saudáveis! 💪
""".strip()


def format_meal_logged(meal_type: str, description: str, is_cheat: bool) -> str:
    """Format meal logged confirmation."""
    type_names = {"B": "Café da manhã", "L": "Almoço", "S": "Lanche", "D": "Jantar"}
    name = type_names.get(meal_type, "Refeição")

    if is_cheat:
        return f"🍔 Cheat {name.lower()} registrado: {description}\n⚠️ -3 pts de penalidade no fim da semana"
    else:
        return f"✓ {name} registrado: {description}"
