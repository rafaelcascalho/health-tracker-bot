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

        # Initialize row with date, day name, and zeros
        new_row = [today, day_name] + [0] * (len(config.DAILY_COLUMNS) - 2)

        # Add formulas for points columns
        # daily_pts = sum of wake through bed (C through M)
        new_row[config.DAILY_COLUMNS["daily_pts"]] = (
            f"=C{row_num}+D{row_num}+E{row_num}+F{row_num}+G{row_num}+H{row_num}"
            f"+I{row_num}+J{row_num}*2+K{row_num}*3+L{row_num}+M{row_num}"
        )
        # exercise_pts = pilates + gym
        new_row[config.DAILY_COLUMNS["exercise_pts"]] = f"=N{row_num}+O{row_num}"
        # total_pts = daily + exercise
        new_row[config.DAILY_COLUMNS["total_pts"]] = f"=Q{row_num}+R{row_num}"

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
            range=f"{config.SHEET_DAILY_LOG}!A{row}:S{row}",
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

        new_row = [timestamp, date_str, meal_type, description, 1 if is_cheat else 0]

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
            "total_points": (
                data.get("water_1", 0)
                + data.get("water_2", 0) * 2
                + data.get("water_3", 0) * 3
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
            range=f"{config.SHEET_DAILY_LOG}!A:S",
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
            "week_num",
            "start_date",
            "end_date",
            "gym_choice",
            "sleep_pts",
            "nutrition_pts",
            "hydration_pts",
            "cardio_pts",
            "exercise_pts",
            "raw_score",
            "cheat_penalty",
            "final_score",
            "percentage",
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
                # E: sleep_pts
                f'=SUMIFS(Daily_Log!C:C,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!L:L,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!M:M,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # F: nutrition_pts
                f'=SUMIFS(Daily_Log!E:E,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!F:F,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!G:G,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!H:H,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # G: hydration_pts
                f'=SUMIFS(Daily_Log!I:I,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!J:J,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*2'
                f'+SUMIFS(Daily_Log!K:K,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*3',
                # H: cardio_pts
                f'=SUMIFS(Daily_Log!D:D,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # I: exercise_pts
                f'=SUMIFS(Daily_Log!N:N,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
                f'+SUMIFS(Daily_Log!O:O,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                f"=E{row_num}+F{row_num}+G{row_num}+H{row_num}+I{row_num}",  # J: raw_score
                # K: cheat_penalty
                f'=SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*3',
                f"=MAX(0,J{row_num}-K{row_num})",  # L: final_score
                f"=L{row_num}/103",  # M: percentage
                # N: status
                f'=IF(M{row_num}>=1,"Perfect",IF(M{row_num}>=0.85,"Successful",'
                f'IF(M{row_num}>=0.7,"Needs Improvement","Danger")))',
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
            "month",
            "start_date",
            "end_date",
            "days_tracked",
            "total_pts",
            "max_possible",
            "cheat_meals",
            "cheat_penalty",
            "final_score",
            "avg_daily",
            "perfect_days",
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
                # E: total_pts
                f'=SUMIFS(Daily_Log!S:S,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                # F: max_possible
                f"=D{row_num}*14+SUMPRODUCT((Daily_Log!A:A>=B{row_num})*(Daily_Log!A:A<=C{row_num})"
                "*(Daily_Log!N:N+Daily_Log!O:O>0))",
                # G: cheat_meals
                f'=SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
                f"=G{row_num}*3",  # H: cheat_penalty
                f"=MAX(0,E{row_num}-H{row_num})",  # I: final_score
                f"=IF(D{row_num}>0,I{row_num}/D{row_num},0)",  # J: avg_daily
                # K: perfect_days
                f'=COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!Q:Q,14)',
                # L: status
                f'=IF(J{row_num}>=14,"Perfect",IF(J{row_num}>=12,"Excellent",'
                f'IF(J{row_num}>=10,"Good",IF(J{row_num}>=8,"Needs Work","Danger"))))',
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
            # Section A: Current Week (Rows 1-6)
            ["CURRENT WEEK", "", "", ""],
            ["Week #", "=ISOWEEKNUM(TODAY())", "", ""],
            [
                "Days Tracked",
                f'=COUNTIFS(Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "",
                "",
            ],
            [
                "Points",
                f'=SUMIFS(Daily_Log!S:S,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "",
                "",
            ],
            ["Max Possible", "=B3*15", "", ""],
            ["Progress", "=IF(B5>0,B4/B5,0)", "", ""],
            # Row 7: Empty
            ["", "", "", ""],
            # Section B: Today (Rows 8-14)
            ["TODAY", "", "", ""],
            ["Date", "=TODAY()", "", ""],
            [
                "Daily Pts",
                "=IFERROR(INDEX(Daily_Log!Q:Q,MATCH(TODAY(),Daily_Log!A:A,0)),0)",
                "",
                "",
            ],
            [
                "Exercise",
                "=IFERROR(INDEX(Daily_Log!R:R,MATCH(TODAY(),Daily_Log!A:A,0)),0)",
                "",
                "",
            ],
            ["Total", "=B10+B11", "", ""],
            [
                "Cheat Meals",
                "=IFERROR(INDEX(Daily_Log!P:P,MATCH(TODAY(),Daily_Log!A:A,0)),0)",
                "",
                "",
            ],
            [
                "Status",
                '=IF(B12>=15,"Perfect",IF(B12>=10,"Good","Behind"))',
                "",
                "",
            ],
            # Row 15: Empty
            ["", "", "", ""],
            # Section C: Stats (Rows 16-22)
            ["STATS", "", "", ""],
            ["Total Days", "=COUNTA(Daily_Log!A:A)-1", "", ""],
            ["Perfect Days", "=COUNTIF(Daily_Log!Q:Q,14)", "", ""],
            ["Avg Daily Pts", "=IFERROR(AVERAGE(Daily_Log!S:S),0)", "", ""],
            ["Total Cheat", "=SUM(Daily_Log!P:P)", "", ""],
            ["Best Week", "=MAX(Weekly_Summary!L:L)", "", ""],
            [
                "Current Weight",
                '=IFERROR(INDEX(Config!B:B,MATCH("current_weight",Config!A:A,0)),"--")',
                "",
                "",
            ],
            # Row 23: Empty
            ["", "", "", ""],
            # Section D: This Week by Category (Rows 24-30)
            ["THIS WEEK BY CATEGORY", "", "", ""],
            # Sleep
            [
                "Sleep",
                f'=SUMIFS(Daily_Log!C:C,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!L:L,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!M:M,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/21",
                "",
            ],
            # Nutrition
            [
                "Nutrition",
                f'=SUMIFS(Daily_Log!E:E,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!F:F,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!G:G,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!H:H,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/28",
                "",
            ],
            # Hydration
            [
                "Hydration",
                f'=SUMIFS(Daily_Log!I:I,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!J:J,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())*2'
                f'+SUMIFS(Daily_Log!K:K,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())*3',
                "/42",
                "",
            ],
            # Cardio
            [
                "Cardio",
                f'=SUMIFS(Daily_Log!D:D,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/7",
                "",
            ],
            # Exercise
            [
                "Exercise",
                f'=SUMIFS(Daily_Log!N:N,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())'
                f'+SUMIFS(Daily_Log!O:O,Daily_Log!A:A,">="&{week_start},Daily_Log!A:A,"<="&TODAY())',
                "/5",
                "",
            ],
            # Total
            ["TOTAL", "=SUM(B25:B29)", "/103", ""],
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
            # E: sleep_pts
            f'=SUMIFS(Daily_Log!C:C,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!L:L,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!M:M,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # F: nutrition_pts
            f'=SUMIFS(Daily_Log!E:E,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!F:F,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!G:G,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!H:H,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # G: hydration_pts
            f'=SUMIFS(Daily_Log!I:I,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!J:J,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*2'
            f'+SUMIFS(Daily_Log!K:K,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*3',
            # H: cardio_pts
            f'=SUMIFS(Daily_Log!D:D,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # I: exercise_pts
            f'=SUMIFS(Daily_Log!N:N,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})'
            f'+SUMIFS(Daily_Log!O:O,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            f"=E{row_num}+F{row_num}+G{row_num}+H{row_num}+I{row_num}",  # J: raw_score
            # K: cheat_penalty
            f'=SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})*3',
            f"=MAX(0,J{row_num}-K{row_num})",  # L: final_score
            f"=L{row_num}/103",  # M: percentage
            # N: status
            f'=IF(M{row_num}>=1,"Perfect",IF(M{row_num}>=0.85,"Successful",'
            f'IF(M{row_num}>=0.7,"Needs Improvement","Danger")))',
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
            # E: total_pts
            f'=SUMIFS(Daily_Log!S:S,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            # F: max_possible
            f"=D{row_num}*14+SUMPRODUCT((Daily_Log!A:A>=B{row_num})*(Daily_Log!A:A<=C{row_num})"
            "*(Daily_Log!N:N+Daily_Log!O:O>0))",
            # G: cheat_meals
            f'=SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num})',
            f"=G{row_num}*3",  # H: cheat_penalty
            f"=MAX(0,E{row_num}-H{row_num})",  # I: final_score
            f"=IF(D{row_num}>0,I{row_num}/D{row_num},0)",  # J: avg_daily
            # K: perfect_days
            f'=COUNTIFS(Daily_Log!A:A,">="&B{row_num},Daily_Log!A:A,"<="&C{row_num},Daily_Log!Q:Q,14)',
            # L: status
            f'=IF(J{row_num}>=14,"Perfect",IF(J{row_num}>=12,"Excellent",'
            f'IF(J{row_num}>=10,"Good",IF(J{row_num}>=8,"Needs Work","Danger"))))',
        ]

        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{config.SHEET_MONTHLY_SUMMARY}!A{row_num}",
            valueInputOption="USER_ENTERED",
            body={"values": [row_formulas]},
        ).execute()

        return True
