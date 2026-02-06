"""Google Sheets API wrapper for health tracking."""

from datetime import datetime, date, timedelta
from typing import Optional
import pytz

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import config


class SheetsClient:
    """Client for interacting with Google Sheets."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    # Mapping for meal types to Brazilian Portuguese
    MEAL_TYPE_NAMES = {
        "B": "Café da manhã",
        "L": "Almoço",
        "S": "Lanche",
        "D": "Jantar",
    }

    def __init__(self):
        self.credentials = Credentials.from_service_account_info(
            config.get_google_credentials(), scopes=self.SCOPES
        )
        self.service = build("sheets", "v4", credentials=self.credentials)
        self.sheet = self.service.spreadsheets()
        self.spreadsheet_id = config.GOOGLE_SHEETS_ID
        self.tz = pytz.timezone(config.TIMEZONE)

    def _get_today_str(self) -> str:
        """Get today's date as YYYY-MM-DD string."""
        return datetime.now(self.tz).strftime("%Y-%m-%d")

    def _get_day_name(self) -> str:
        """Get today's day name."""
        return datetime.now(self.tz).strftime("%A")

    def _col_letter(self, col_index: int) -> str:
        """Convert column index (0-based) to letter (A, B, C, ...)."""
        return chr(ord("A") + col_index)

    def get_or_create_today_row(self) -> int:
        """Get today's row number, creating it if it doesn't exist.

        Returns:
            Row number (1-indexed) for today's entry.
        """
        today = self._get_today_str()

        # Get all dates from column A
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_DAILY_LOG}!A:A",
        ).execute()

        values = result.get("values", [])

        # Find today's row
        for i, row in enumerate(values):
            if row and row[0] == today:
                return i + 1  # 1-indexed

        # Create new row for today
        row_num = len(values) + 1
        day_name = self._get_day_name()

        # Initialize row with date, day name, and zeros for all actions
        new_row = [today, day_name] + [0] * (len(config.DAILY_COLUMNS) - 2)

        # Add formulas for points columns
        # daily_pts = sum of wake through bed (C through N), with water_2 *2, water_3 *3
        # Columns: C=wake, D=cardio, E=breakfast, F=lunch, G=snack, H=dinner,
        #          I=water_1, J=water_2, K=water_3, L=water_copo, M=bedroom, N=bed
        new_row[config.DAILY_COLUMNS["daily_pts"]] = (
            f"=C{row_num}+D{row_num}+E{row_num}+F{row_num}+G{row_num}+H{row_num}"
            f"+I{row_num}+J{row_num}*2+K{row_num}*3+L{row_num}+M{row_num}+N{row_num}"
        )
        # exercise_pts = pilates + gym
        new_row[config.DAILY_COLUMNS["exercise_pts"]] = f"=O{row_num}+P{row_num}"
        # total_pts = daily + exercise
        new_row[config.DAILY_COLUMNS["total_pts"]] = f"=R{row_num}+S{row_num}"

        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_DAILY_LOG}!A{row_num}",
            valueInputOption="USER_ENTERED",
            body={"values": [new_row]},
        ).execute()

        return row_num

    def update_action(self, action: str, value: int = 1) -> bool:
        """Update a specific action for today.

        Args:
            action: Action name (e.g., 'cardio', 'water_1')
            value: Value to set (default 1)

        Returns:
            True if successful.
        """
        if action not in config.DAILY_COLUMNS:
            raise ValueError(f"Unknown action: {action}")

        row = self.get_or_create_today_row()
        col_index = config.DAILY_COLUMNS[action]
        col_letter = self._col_letter(col_index)

        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_DAILY_LOG}!{col_letter}{row}",
            valueInputOption="RAW",
            body={"values": [[value]]},
        ).execute()

        return True

    def get_action_value(self, action: str) -> int:
        """Get the current value of an action for today.

        Args:
            action: Action name

        Returns:
            Current value (0 or 1 typically)
        """
        if action not in config.DAILY_COLUMNS:
            raise ValueError(f"Unknown action: {action}")

        row = self.get_or_create_today_row()
        col_index = config.DAILY_COLUMNS[action]
        col_letter = self._col_letter(col_index)

        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_DAILY_LOG}!{col_letter}{row}",
        ).execute()

        values = result.get("values", [[0]])
        try:
            return int(values[0][0]) if values and values[0] else 0
        except (ValueError, TypeError):
            return 0

    def get_today_data(self) -> dict:
        """Get all data for today.

        Returns:
            Dictionary with all action values for today.
        """
        row = self.get_or_create_today_row()

        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_DAILY_LOG}!A{row}:T{row}",
        ).execute()

        values = result.get("values", [[]])[0]

        # Pad with zeros if needed
        while len(values) < len(config.DAILY_COLUMNS):
            values.append(0)

        data = {}
        for name, idx in config.DAILY_COLUMNS.items():
            try:
                val = values[idx] if idx < len(values) else 0
                # Try to convert to int, keep as string if fails
                data[name] = int(val) if str(val).isdigit() else val
            except (ValueError, TypeError):
                data[name] = values[idx] if idx < len(values) else 0

        return data

    def increment_cheat_meals(self) -> int:
        """Increment the cheat meals counter for today.

        Returns:
            New cheat meal count.
        """
        current = self.get_action_value("cheat_meals")
        new_value = current + 1
        self.update_action("cheat_meals", new_value)
        return new_value

    def log_meal(
        self, meal_type: str, description: str, is_cheat: bool = False
    ) -> bool:
        """Log a meal to the Meals_Log sheet.

        Args:
            meal_type: B, L, S, or D
            description: Meal description
            is_cheat: Whether this is a cheat meal

        Returns:
            True if successful.
        """
        now = datetime.now(self.tz)
        timestamp = now.isoformat()
        date_str = now.strftime("%Y-%m-%d")

        # Convert meal type to full Portuguese name
        meal_name = self.MEAL_TYPE_NAMES.get(meal_type, meal_type)

        new_row = [
            timestamp,
            date_str,
            meal_name,
            description,
            "Sim" if is_cheat else "Não",
        ]

        self.sheet.values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_MEALS_LOG}!A:E",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [new_row]},
        ).execute()

        return True

    def get_water_status(self) -> dict:
        """Get current water bottle status.

        Returns:
            Dictionary with water_1, water_2, water_3 values and total points.
        """
        data = self.get_today_data()
        return {
            "water_1": data.get("water_1", 0),
            "water_2": data.get("water_2", 0),
            "water_3": data.get("water_3", 0),
            "water_copo": data.get("water_copo", 0),
            "total_points": (
                data.get("water_1", 0)
                + data.get("water_2", 0) * 2
                + data.get("water_3", 0) * 3
                + data.get("water_copo", 0)
            ),
        }

    def get_config_value(self, key: str) -> Optional[str]:
        """Get a value from the Config sheet.

        Args:
            key: Configuration key to look up

        Returns:
            Value if found, None otherwise.
        """
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_CONFIG}!A:B",
        ).execute()

        values = result.get("values", [])
        for row in values:
            if len(row) >= 2 and row[0] == key:
                return row[1]
        return None

    def set_config_value(self, key: str, value: str) -> bool:
        """Set a value in the Config sheet.

        Args:
            key: Configuration key
            value: Value to set

        Returns:
            True if successful.
        """
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_CONFIG}!A:B",
        ).execute()

        values = result.get("values", [])

        # Find existing key
        for i, row in enumerate(values):
            if row and row[0] == key:
                self.sheet.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{config.SHEET_CONFIG}!B{i + 1}",
                    valueInputOption="RAW",
                    body={"values": [[value]]},
                ).execute()
                return True

        # Add new key
        self.sheet.values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_CONFIG}!A:B",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [[key, value]]},
        ).execute()

        return True

    def get_gym_day_choice(self) -> Optional[str]:
        """Get the gym day choice for the current week.

        Returns:
            'friday' or 'saturday', or None if not set.
        """
        return self.get_config_value("gym_day_choice")

    def set_gym_day_choice(self, day: str) -> bool:
        """Set the gym day choice for the current week.

        Args:
            day: 'friday' or 'saturday'

        Returns:
            True if successful.
        """
        if day.lower() not in ("friday", "saturday"):
            raise ValueError("Gym day must be 'friday' or 'saturday'")
        return self.set_config_value("gym_day_choice", day.lower())

    def get_week_data(self) -> list[dict]:
        """Get data for the current week (Monday to today).

        Returns:
            List of daily data dictionaries.
        """
        now = datetime.now(self.tz)
        # Find Monday of this week
        monday = now - timedelta(days=now.weekday())

        # Get all data from Daily_Log
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_DAILY_LOG}!A:T",
        ).execute()

        values = result.get("values", [])
        week_data = []

        monday_str = monday.strftime("%Y-%m-%d")

        for row in values:
            if row and row[0] >= monday_str:
                data = {}
                for name, idx in config.DAILY_COLUMNS.items():
                    try:
                        val = row[idx] if idx < len(row) else 0
                        data[name] = int(val) if str(val).isdigit() else val
                    except (ValueError, TypeError, IndexError):
                        data[name] = 0
                week_data.append(data)

        return week_data

    def log_weight(self, weight: float) -> bool:
        """Log current weight.

        Args:
            weight: Weight in kg

        Returns:
            True if successful.
        """
        return self.set_config_value("current_weight", str(weight))

    def get_weight(self) -> Optional[float]:
        """Get current weight.

        Returns:
            Weight in kg, or None if not set.
        """
        value = self.get_config_value("current_weight")
        if value:
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def setup_weekly_summary_sheet(self) -> bool:
        """Set up the Weekly_Summary sheet with headers and 13 weeks of formulas.

        Creates headers in row 1 and formula rows for Jan 6 - Mar 30, 2026.

        Returns:
            True if successful.
        """
        headers = [
            "num_semana",
            "data_inicio",
            "data_fim",
            "dia_academia",
            "pts_sono",
            "pts_nutricao",
            "pts_hidratacao",
            "pts_cardio",
            "pts_exercicio",
            "pontuacao_bruta",
            "penalidade_besteira",
            "pontuacao_final",
            "porcentagem",
            "status",
        ]

        # Generate 13 weeks: Jan 6 - Mar 30, 2026
        weeks = [
            ("2026-01-06", ""),  # Week 1
            ("2026-01-13", ""),  # Week 2
            ("2026-01-20", ""),  # Week 3
            ("2026-01-27", ""),  # Week 4
            ("2026-02-03", ""),  # Week 5
            ("2026-02-10", ""),  # Week 6
            ("2026-02-17", ""),  # Week 7
            ("2026-02-24", ""),  # Week 8
            ("2026-03-03", ""),  # Week 9
            ("2026-03-10", ""),  # Week 10
            ("2026-03-17", ""),  # Week 11
            ("2026-03-24", ""),  # Week 12
            ("2026-03-31", ""),  # Week 13
        ]

        all_rows = [headers]

        for i, (start_date, gym_choice) in enumerate(weeks):
            row_num = i + 2  # Row numbers start at 2
            row_formulas = [
                f"=ISOWEEKNUM(B{row_num})",  # A: week_num
                start_date,  # B: start_date
                f"=B{row_num}+6",  # C: end_date
                gym_choice,  # D: gym_choice (manual)
                # E: sleep_pts (C=wake, M=bedroom, N=bed)
                f'=SUMIFS(Daily_Log!C:C,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!M:M,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!N:N,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # F: nutrition_pts
                f'=SUMIFS(Daily_Log!E:E,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!F:F,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!G:G,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!H:H,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # G: hydration_pts (I=water_1, J=water_2*2, K=water_3*3, L=water_copo)
                f'=SUMIFS(Daily_Log!I:I,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!J:J,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*2'
                f'+SUMIFS(Daily_Log!K:K,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*3'
                f'+SUMIFS(Daily_Log!L:L,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # H: cardio_pts
                f'=SUMIFS(Daily_Log!D:D,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # I: exercise_pts (O=pilates, P=gym)
                f'=SUMIFS(Daily_Log!O:O,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                f"=E{row_num}+F{row_num}+G{row_num}+H{row_num}+I{row_num}",  # J: raw_score
                # K: cheat_penalty (Q=cheat_meals)
                f'=SUMIFS(Daily_Log!Q:Q,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*3',
                f"=MAX(0,J{row_num}-K{row_num})",  # L: final_score
                f"=L{row_num}/106",  # M: percentage
                # N: status
                f'=IF(M{row_num}>=1,"Perfeito",IF(M{row_num}>=0.85,"Sucesso",'
                f'IF(M{row_num}>=0.7,"Precisa Melhorar","Perigo")))',
            ]
            all_rows.append(row_formulas)

        # Write all rows at once
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_WEEKLY_SUMMARY}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": all_rows},
        ).execute()

        return True

    def setup_monthly_summary_sheet(self) -> bool:
        """Set up the Monthly_Summary sheet with headers and 3 months of formulas.

        Creates headers in row 1 and formula rows for Jan, Feb, Mar 2026.

        Returns:
            True if successful.
        """
        headers = [
            "mes",
            "data_inicio",
            "data_fim",
            "dias_registrados",
            "pts_total",
            "max_possivel",
            "besteiras",
            "penalidade_besteira",
            "pontuacao_final",
            "media_diaria",
            "dias_perfeitos",
            "status",
        ]

        # 3 months: January, February, March 2026
        months = [
            "2026-01-01",
            "2026-02-01",
            "2026-03-01",
        ]

        all_rows = [headers]

        for i, start_date in enumerate(months):
            row_num = i + 2  # Row numbers start at 2
            row_formulas = [
                f'=TEXT(B{row_num},"YYYY-MM")',  # A: month
                start_date,  # B: start_date
                f"=EOMONTH(B{row_num},0)",  # C: end_date
                # D: days_tracked
                f'=COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # E: total_pts (T=total_pts)
                f'=SUMIFS(Daily_Log!T:T,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # F: max_possible (weekday=15, weekend=13, +exercise days)
                f'=COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!B:B,"<>Saturday",Daily_Log!B:B,"<>Sunday")*15'
                f'+COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!B:B,"Saturday")*13'
                f'+COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!B:B,"Sunday")*13'
                f'+COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!O:O,">"&0)'
                f'+COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!P:P,">"&0)',
                # G: cheat_meals (Q=cheat_meals)
                f'=SUMIFS(Daily_Log!Q:Q,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                f"=G{row_num}*3",  # H: cheat_penalty
                f"=MAX(0,E{row_num}-H{row_num})",  # I: final_score
                f"=IF(D{row_num}>0,I{row_num}/D{row_num},0)",  # J: avg_daily
                # K: perfect_days (R=daily_pts: 15 on weekdays, 13 on weekends)
                f'=COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!R:R,15)'
                f'+COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!R:R,13,Daily_Log!B:B,"Saturday")'
                f'+COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!R:R,13,Daily_Log!B:B,"Sunday")',
                # L: status
                f'=IF(J{row_num}>=15,"Perfeito",IF(J{row_num}>=12,"Excelente",'
                f'IF(J{row_num}>=10,"Bom",IF(J{row_num}>=8,"Precisa Melhorar","Perigo"))))',
            ]
            all_rows.append(row_formulas)

        # Write all rows at once
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_MONTHLY_SUMMARY}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": all_rows},
        ).execute()

        return True

    def setup_dashboard_sheet(self) -> bool:
        """Set up the Dashboard sheet with labels and formulas.

        Returns:
            True if successful.
        """
        # Week start formula helper (Monday of current week)
        week_start = "(TODAY()-WEEKDAY(TODAY(),2)+1)"

        # Build dashboard data
        dashboard_data = [
            # Seção A: Semana Atual (Linhas 1-6)
            ["SEMANA ATUAL", "", "", ""],
            ["Semana", "=ISOWEEKNUM(TODAY())", "", ""],
            [
                "Dias Registrados",
                f'=COUNTIFS(Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "",
                "",
            ],
            [
                "Pontos",
                f'=SUMIFS(Daily_Log!T:T,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "",
                "",
            ],
            [
                "Max Possível",
                f'=COUNTIFS(Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY(),Daily_Log!B:B,"<>Saturday",Daily_Log!B:B,"<>Sunday")*15'
                f'+COUNTIFS(Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY(),Daily_Log!B:B,"Saturday")*13'
                f'+COUNTIFS(Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY(),Daily_Log!B:B,"Sunday")*13'
                f'+COUNTIFS(Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY(),Daily_Log!O:O,">"&0)'
                f'+COUNTIFS(Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY(),Daily_Log!P:P,">"&0)',
                "",
                "",
            ],
            ["Progresso", "=IF(B5>0,B4/B5,0)", "", ""],
            # Linha 7: Vazia
            ["", "", "", ""],
            # Seção B: Hoje (Linhas 8-14)
            ["HOJE", "", "", ""],
            ["Data", "=TODAY()", "", ""],
            [
                "Pts Diários",
                "=IFERROR(INDEX(Daily_Log!R:R,MATCH(TODAY(),Daily_Log!A:A,0)),0)",
                "",
                "",
            ],
            [
                "Exercício",
                "=IFERROR(INDEX(Daily_Log!S:S,MATCH(TODAY(),Daily_Log!A:A,0)),0)",
                "",
                "",
            ],
            ["Total", "=B10+B11", "", ""],
            [
                "Besteiras",
                "=IFERROR(INDEX(Daily_Log!Q:Q,MATCH(TODAY(),Daily_Log!A:A,0)),0)",
                "",
                "",
            ],
            [
                "Status",
                '=IF(B12>=IF(WEEKDAY(TODAY(),2)>=6,13,15),"Perfeito",IF(B12>=10,"Bom","Atrasado"))',
                "",
                "",
            ],
            # Linha 15: Vazia
            ["", "", "", ""],
            # Seção C: Estatísticas (Linhas 16-22)
            ["ESTATÍSTICAS", "", "", ""],
            ["Total de Dias", "=COUNTA(Daily_Log!A:A)-1", "", ""],
            [
                "Dias Perfeitos",
                "=COUNTIF(Daily_Log!R:R,15)"
                '+COUNTIFS(Daily_Log!R:R,13,Daily_Log!B:B,"Saturday")'
                '+COUNTIFS(Daily_Log!R:R,13,Daily_Log!B:B,"Sunday")',
                "",
                "",
            ],
            ["Média Pts Diários", "=IFERROR(AVERAGE(Daily_Log!T:T),0)", "", ""],
            ["Total Besteiras", "=SUM(Daily_Log!Q:Q)", "", ""],
            ["Melhor Semana", "=MAX(Weekly_Summary!L:L)", "", ""],
            [
                "Peso Atual",
                '=IFERROR(INDEX(Config!B:B,MATCH("current_weight",Config!A:A,0)),"--")',
                "",
                "",
            ],
            # Linha 23: Vazia
            ["", "", "", ""],
            # Seção D: Semana por Categoria (Linhas 24-30)
            ["SEMANA POR CATEGORIA", "", "", ""],
            # Sono (C=acordar, M=quarto, N=cama)
            [
                "Sono",
                f'=SUMIFS(Daily_Log!C:C,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!M:M,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!N:N,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/19",
                "",
            ],
            # Nutrição
            [
                "Nutrição",
                f'=SUMIFS(Daily_Log!E:E,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!F:F,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!G:G,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!H:H,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/28",
                "",
            ],
            # Hidratação (I=garrafa_1, J=garrafa_2*2, K=garrafa_3*3, L=copo_300ml)
            [
                "Hidratação",
                f'=SUMIFS(Daily_Log!I:I,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!J:J,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())*2'
                f'+SUMIFS(Daily_Log!K:K,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())*3'
                f'+SUMIFS(Daily_Log!L:L,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/49",
                "",
            ],
            # Cardio (somente dias úteis, max 5)
            [
                "Cardio",
                f'=SUMIFS(Daily_Log!D:D,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/5",
                "",
            ],
            # Exercício (O=pilates, P=academia)
            [
                "Exercício",
                f'=SUMIFS(Daily_Log!O:O,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/5",
                "",
            ],
            # Total
            ["TOTAL", "=SUM(B25:B29)", "/106", ""],
        ]

        # Write all dashboard data
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_DASHBOARD}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": dashboard_data},
        ).execute()

        return True

    def setup_all_analysis_sheets(self) -> dict:
        """Set up Weekly_Summary, Monthly_Summary, and Dashboard sheets.

        Returns:
            Dictionary with status for each sheet.
        """
        results = {}

        try:
            self.setup_weekly_summary_sheet()
            results["weekly_summary"] = "success"
        except Exception as e:
            results["weekly_summary"] = f"error: {e}"

        try:
            self.setup_monthly_summary_sheet()
            results["monthly_summary"] = "success"
        except Exception as e:
            results["monthly_summary"] = f"error: {e}"

        try:
            self.setup_dashboard_sheet()
            results["dashboard"] = "success"
        except Exception as e:
            results["dashboard"] = f"error: {e}"

        return results

    def add_weekly_summary_row(self, start_date: str, gym_choice: str = "") -> bool:
        """Add a new week row to Weekly_Summary.

        Args:
            start_date: Week start date (Monday) as YYYY-MM-DD
            gym_choice: 'friday' or 'saturday' (optional)

        Returns:
            True if successful.
        """
        # Get current row count
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_WEEKLY_SUMMARY}!A:A",
        ).execute()
        values = result.get("values", [])
        row_num = len(values) + 1

        # Row formulas (same structure, just with different row number)
        row_formulas = [
            f"=ISOWEEKNUM(B{row_num})",  # A: week_num
            start_date,  # B: start_date
            f"=B{row_num}+6",  # C: end_date
            gym_choice,  # D: gym_choice
            # E: sleep_pts (C=wake, M=bedroom, N=bed)
            f'=SUMIFS(Daily_Log!C:C,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!M:M,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!N:N,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # F: nutrition_pts
            f'=SUMIFS(Daily_Log!E:E,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!F:F,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!G:G,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!H:H,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # G: hydration_pts (I=water_1, J=water_2*2, K=water_3*3, L=water_copo)
            f'=SUMIFS(Daily_Log!I:I,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!J:J,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*2'
            f'+SUMIFS(Daily_Log!K:K,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*3'
            f'+SUMIFS(Daily_Log!L:L,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # H: cardio_pts
            f'=SUMIFS(Daily_Log!D:D,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # I: exercise_pts (O=pilates, P=gym)
            f'=SUMIFS(Daily_Log!O:O,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            f"=E{row_num}+F{row_num}+G{row_num}+H{row_num}+I{row_num}",  # J: raw_score
            # K: cheat_penalty (Q=cheat_meals)
            f'=SUMIFS(Daily_Log!Q:Q,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*3',
            f"=MAX(0,J{row_num}-K{row_num})",  # L: final_score
            f"=L{row_num}/106",  # M: percentage
            # N: status
            f'=IF(M{row_num}>=1,"Perfeito",IF(M{row_num}>=0.85,"Sucesso",'
            f'IF(M{row_num}>=0.7,"Precisa Melhorar","Perigo")))',
        ]

        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_WEEKLY_SUMMARY}!A{row_num}",
            valueInputOption="USER_ENTERED",
            body={"values": [row_formulas]},
        ).execute()

        return True

    def add_monthly_summary_row(self, start_date: str) -> bool:
        """Add a new month row to Monthly_Summary.

        Args:
            start_date: First day of month as YYYY-MM-DD

        Returns:
            True if successful.
        """
        # Get current row count
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_MONTHLY_SUMMARY}!A:A",
        ).execute()
        values = result.get("values", [])
        row_num = len(values) + 1

        row_formulas = [
            f'=TEXT(B{row_num},"YYYY-MM")',  # A: month
            start_date,  # B: start_date
            f"=EOMONTH(B{row_num},0)",  # C: end_date
            # D: days_tracked
            f'=COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # E: total_pts (T=total_pts)
            f'=SUMIFS(Daily_Log!T:T,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # F: max_possible (O=pilates, P=gym)
            f"=D{row_num}*15+SUMPRODUCT((Daily_Log!A:A>=B{row_num})*(Daily_Log!A:A<=C{row_num})"
            "*(Daily_Log!O:O+Daily_Log!P:P>0))",
            # G: cheat_meals (Q=cheat_meals)
            f'=SUMIFS(Daily_Log!Q:Q,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            f"=G{row_num}*3",  # H: cheat_penalty
            f"=MAX(0,E{row_num}-H{row_num})",  # I: final_score
            f"=IF(D{row_num}>0,I{row_num}/D{row_num},0)",  # J: avg_daily
            # K: perfect_days (R=daily_pts: 15 on weekdays, 13 on weekends)
            f'=COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!R:R,15)'
            f'+COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!R:R,13,Daily_Log!B:B,"Saturday")'
            f'+COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!R:R,13,Daily_Log!B:B,"Sunday")',
            # L: status
            f'=IF(J{row_num}>=15,"Perfeito",IF(J{row_num}>=12,"Excelente",'
            f'IF(J{row_num}>=10,"Bom",IF(J{row_num}>=8,"Precisa Melhorar","Perigo"))))',
        ]

        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_MONTHLY_SUMMARY}!A{row_num}",
            valueInputOption="USER_ENTERED",
            body={"values": [row_formulas]},
        ).execute()

        return True
