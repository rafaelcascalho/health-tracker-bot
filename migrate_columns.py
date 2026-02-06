#!/usr/bin/env python3
"""
One-time migration: insert water_copo column (L) into Daily_Log and update formulas.

Old layout (A-S, 19 columns):
  A=date, B=day, C=wake, D=cardio, E=bkft, F=lunch, G=snack, H=dinner,
  I=water_1, J=water_2, K=water_3, L=bedroom, M=bed,
  N=pilates, O=gym, P=cheat, Q=daily_pts, R=exercise_pts, S=total_pts

New layout (A-T, 20 columns):
  A=date, B=day, C=wake, D=cardio, E=bkft, F=lunch, G=snack, H=dinner,
  I=water_1, J=water_2, K=water_3, L=water_copo, M=bedroom, N=bed,
  O=pilates, P=gym, Q=cheat, R=daily_pts, S=exercise_pts, T=total_pts

Usage:
  python migrate_columns.py --dry-run   # preview changes without writing
  python migrate_columns.py             # apply migration
"""

import sys

import config
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

OLD_COLUMN_COUNT = 19  # A through S

# New header row in Brazilian Portuguese (20 columns, A-T)
HEADERS_PT = [
    "data",            # A
    "dia",             # B
    "acordar_7h",      # C
    "cardio",          # D
    "cafe_da_manha",   # E
    "almoco",          # F
    "lanche",          # G
    "jantar",          # H
    "garrafa_1",       # I
    "garrafa_2",       # J
    "garrafa_3",       # K
    "copo_300ml",      # L (new)
    "quarto",          # M
    "cama",            # N
    "pilates",         # O
    "academia",        # P
    "besteiras",       # Q
    "pts_diarios",     # R
    "pts_exercicio",   # S
    "pts_total",       # T
]


def is_date_value(value: str) -> bool:
    """Check if a value looks like a YYYY-MM-DD date."""
    s = str(value)
    return len(s) == 10 and s[4] == "-" and s[7] == "-"


def migrate(dry_run: bool = False):
    credentials = Credentials.from_service_account_info(
        config.get_google_credentials(), scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()

    # Step 1: Read all existing data from Daily_Log
    print("Reading Daily_Log...")
    result = (
        sheet.values()
        .get(
            spreadsheetId=config.GOOGLE_SHEETS_ID,
            range=f"{config.SHEET_DAILY_LOG}!A:S",
        )
        .execute()
    )

    rows = result.get("values", [])
    if not rows:
        print("No data found in Daily_Log. Nothing to migrate.")
        return

    print(f"Found {len(rows)} rows")

    # Step 2: Check if already migrated (has 20+ columns)
    check = (
        sheet.values()
        .get(
            spreadsheetId=config.GOOGLE_SHEETS_ID,
            range=f"{config.SHEET_DAILY_LOG}!A1:T1",
        )
        .execute()
    )
    first_row = check.get("values", [[]])[0]
    if len(first_row) >= 20:
        print("Daily_Log already has 20+ columns. Migration may have already run.")
        print("Aborting to avoid double-migration. Check the sheet manually.")
        return

    # Step 3: Transform each row
    new_rows = []
    for i, row in enumerate(rows):
        row_num = i + 1  # 1-indexed for sheet formulas

        # Pad short rows to old column count
        while len(row) < OLD_COLUMN_COUNT:
            row.append(0)

        if not is_date_value(row[0]):
            # Header row: replace with Portuguese names
            new_row = list(HEADERS_PT)
        else:
            # Data row: insert water_copo=0 at position 11, shift the rest
            new_row = list(row[0:11])  # A-K: date through water_3
            new_row.append(0)  # L: water_copo (new, default 0)
            new_row.extend(row[11:16])  # M-Q: bedroom, bed, pilates, gym, cheat_meals

            # R: daily_pts = C+D+E+F+G+H + I + J*2 + K*3 + L + M + N
            new_row.append(
                f"=C{row_num}+D{row_num}+E{row_num}+F{row_num}+G{row_num}+H{row_num}"
                f"+I{row_num}+J{row_num}*2+K{row_num}*3+L{row_num}+M{row_num}+N{row_num}"
            )
            # S: exercise_pts = O + P
            new_row.append(f"=O{row_num}+P{row_num}")
            # T: total_pts = R + S
            new_row.append(f"=R{row_num}+S{row_num}")

        new_rows.append(new_row)

    # Step 4: Preview or apply
    print(f"\nTransformed {len(new_rows)} rows (inserted water_copo as column L)")

    # Show sample
    sample_count = min(3, len(new_rows))
    for i in range(sample_count):
        label = "header" if not is_date_value(new_rows[i][0]) else f"data"
        print(f"  Row {i + 1} ({label}): {new_rows[i][:13]}... ({len(new_rows[i])} cols)")

    if dry_run:
        print(f"\n[DRY RUN] No changes written. Run without --dry-run to apply.")
        return

    # Write back to Daily_Log
    print("\nWriting migrated data to Daily_Log...")
    sheet.values().update(
        spreadsheetId=config.GOOGLE_SHEETS_ID,
        range=f"{config.SHEET_DAILY_LOG}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": new_rows},
    ).execute()
    print(f"Daily_Log updated: {len(new_rows)} rows written (A:T)")

    # Regenerate analysis sheets with new column references
    print("\nRegenerating analysis sheets...")
    from bot.sheets import SheetsClient

    client = SheetsClient()
    results = client.setup_all_analysis_sheets()
    for name, status in results.items():
        icon = "OK" if status == "success" else "FAIL"
        print(f"  [{icon}] {name}: {status}")

    print("\nMigration complete!")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if not dry_run:
        print("This will modify your Google Sheet. Use --dry-run to preview first.")
        answer = input("Continue? [y/N] ")
        if answer.lower() != "y":
            print("Aborted.")
            sys.exit(0)
    migrate(dry_run=dry_run)
