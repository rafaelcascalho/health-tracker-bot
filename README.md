# Health Tracking Bot

A Telegram bot for tracking daily health habits with scheduled reminders, interactive buttons, and Google Sheets integration.

## Features

- **Scheduled Reminders**: Automatic notifications for meals, hydration, exercise, and sleep
- **Interactive Buttons**: One-tap tracking for all activities
- **Point System**: Gamified tracking with daily and weekly scores
- **Google Sheets Backend**: All data stored in a spreadsheet for easy viewing and analysis
- **Water Tracking**: Progressive water bottle tracking with bonus points
- **Exercise Scheduling**: Pilates (Mon/Wed) and Gym (Tue/Thu + choice day)

## Setup

### 1. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Send `/setcommands` to BotFather and paste:
   ```
   start - Welcome message and help
   today - Show today's progress
   week - Show weekly summary
   water - Water tracker with buttons
   meal - Log a meal (usage: /meal description)
   cheat - Log a cheat meal (usage: /cheat description)
   gym - Set gym day (usage: /gym friday or /gym saturday)
   weight - Log weight (usage: /weight kg)
   undo - Undo an action (usage: /undo action_name)
   setup_sheets - Initialize analysis sheets with formulas
   add_week - Add week to Weekly_Summary
   add_month - Add month to Monthly_Summary
   ```

### 2. Get Your Telegram User ID

1. Search for `@userinfobot` on Telegram
2. Send any message to it
3. It will reply with your user ID (a number)

### 3. Create Google Sheets

1. Go to [Google Sheets](https://sheets.google.com) and create a new spreadsheet
2. Create the following sheets (tabs):
   - `Daily_Log`
   - `Meals_Log`
   - `Weekly_Summary`
   - `Monthly_Summary`
   - `Dashboard`
   - `Config`

3. In `Daily_Log`, add headers in row 1:
   ```
   date | day | wake_7am | cardio | breakfast | lunch | snack | dinner | water_1 | water_2 | water_3 | bedroom | bed | pilates | gym | cheat_meals | daily_pts | exercise_pts | total_pts
   ```

4. In `Meals_Log`, add headers in row 1:
   ```
   timestamp | date | meal_type | description | is_cheat
   ```

5. In `Config`, add these rows:
   ```
   gym_day_choice | friday
   current_weight |
   ```

6. Copy the spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit`

### 4. Set Up Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create a Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Give it a name and create
   - Click on the service account email
   - Go to "Keys" tab > "Add Key" > "Create new key" > JSON
   - Download the JSON file
5. Share your Google Sheet with the service account email (found in the JSON file as `client_email`), giving it "Editor" access

### 5. Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in the values:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_USER_ID=your_user_id
   GOOGLE_SHEETS_ID=your_spreadsheet_id
   GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
   ```

### 6. Install Dependencies

```bash
pip install -r requirements.txt
```

### 7. Run the Bot

```bash
python -m bot.main
```

## Deployment to Railway

1. Push your code to GitHub
2. Go to [Railway.app](https://railway.app) and create a new project
3. Connect your GitHub repository
4. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_USER_ID`
   - `GOOGLE_SHEETS_ID`
   - `GOOGLE_CREDENTIALS` (paste the entire JSON content as a string)
5. Deploy!

## Daily Schedule

| Time | Reminder | Days |
|------|----------|------|
| 7:00 | Wake + Cardio | Mon-Fri |
| 8:00 | Breakfast | Daily |
| 10:00 | Cardio | Sat-Sun |
| 12:00 | Lunch | Daily |
| 14:00 | Hydration | Daily |
| 16:00 | Snack | Daily |
| 18:00 | Exercise | Mon/Wed (Pilates), Tue/Thu/Choice (Gym) |
| 19:00 | Dinner + Water Warning | Daily |
| 21:30 | Chores | Daily |
| 22:00 | Bedroom | Daily |
| 22:30 | Bed + Summary | Daily |

## Point System

### Daily Points (14 max)
- Wake by 7am: 1 pt
- Cardio: 1 pt
- Meals (4): 4 pts
- Water: 1 + 2 + 3 = 6 pts
- Bedroom by 10pm: 1 pt
- Bed by 10:30pm: 1 pt

### Exercise Points
- Pilates (Mon/Wed): 1 pt each
- Gym (Tue/Thu + Fri or Sat): 1 pt each

### Weekly Maximum: 103 pts
- Daily (14 × 7): 98 pts
- Pilates (2): 2 pts
- Gym (3): 3 pts

### Cheat Penalty
- Each cheat meal: -3 pts from weekly total

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and help |
| `/today` | Show today's progress |
| `/week` | Show weekly summary |
| `/water` | Water tracker with buttons |
| `/meal <desc>` | Log a meal |
| `/cheat <desc>` | Log a cheat meal |
| `/gym friday\|saturday` | Set gym day |
| `/weight <kg>` | Log weight |
| `/undo <action>` | Undo an action |
| `/setup_sheets` | Initialize Weekly_Summary, Monthly_Summary, and Dashboard sheets with formulas |
| `/add_week <date> [day]` | Add a new week row (e.g., `/add_week 2026-01-13 friday`) |
| `/add_month <date>` | Add a new month row (e.g., `/add_month 2026-02-01`) |

## Analysis Sheets Setup

The bot automatically sets up 3 months of tracking (Jan-Mar 2026). After creating the sheet tabs:

1. Run `/setup_sheets` in Telegram to populate:
   - **Weekly_Summary**: 13 weeks (Jan 6 - Mar 31, 2026)
   - **Monthly_Summary**: 3 months (Jan, Feb, Mar 2026)
   - **Dashboard**: Real-time stats and progress

For detailed formula reference, see `GOOGLE_SHEETS_FORMULAS.md`.

## License

MIT
