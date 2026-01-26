# Google Sheets Analysis Formulas

This document contains all formulas needed for the Weekly_Summary, Monthly_Summary, and Dashboard sheets.

**Prerequisites**: The `Daily_Log` sheet must already exist with the correct column structure (A-S).

---

## Daily_Log Column Reference

| Col | Name | Description |
|-----|------|-------------|
| A | date | YYYY-MM-DD |
| B | day | Day name |
| C | wake_7am | 0/1 |
| D | cardio | 0/1 |
| E | breakfast | 0/1 |
| F | lunch | 0/1 |
| G | snack | 0/1 |
| H | dinner | 0/1 |
| I | water_1 | 0/1 (+1 pt) |
| J | water_2 | 0/1 (+2 pts) |
| K | water_3 | 0/1 (+3 pts) |
| L | bedroom | 0/1 |
| M | bed | 0/1 |
| N | pilates | 0/1 |
| O | gym | 0/1 |
| P | cheat_meals | count |
| Q | daily_pts | formula |
| R | exercise_pts | formula |
| S | total_pts | formula |

---

## Sheet 1: Weekly_Summary

### Setup Instructions

1. Create a new sheet named `Weekly_Summary`
2. Run `/setup_sheets` in Telegram - this automatically creates:
   - Headers in Row 1
   - 13 weeks of formulas (Jan 6 - Mar 31, 2026)
3. Or manually add headers: `week_num`, `start_date`, `end_date`, `gym_choice`, `sleep_pts`, `nutrition_pts`, `hydration_pts`, `cardio_pts`, `exercise_pts`, `raw_score`, `cheat_penalty`, `final_score`, `percentage`, `status`

### Column Formulas (Enter in Row 2, drag down)

**Column A - week_num**
```
=ISOWEEKNUM(B2)
```

**Column B - start_date**
```
=DATE(2026,1,6)
```
For subsequent rows: `=B2+7`

**Column C - end_date**
```
=B2+6
```

**Column D - gym_choice**
Manual entry: `friday` or `saturday`

**Column E - sleep_pts**
```
=SUMIFS(Daily_Log!C:C,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)+SUMIFS(Daily_Log!L:L,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)+SUMIFS(Daily_Log!M:M,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)
```
*Sums: wake_7am (C) + bedroom (L) + bed (M) for the week*

**Column F - nutrition_pts**
```
=SUMIFS(Daily_Log!E:E,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)+SUMIFS(Daily_Log!F:F,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)+SUMIFS(Daily_Log!G:G,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)+SUMIFS(Daily_Log!H:H,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)
```
*Sums: breakfast (E) + lunch (F) + snack (G) + dinner (H) for the week*

**Column G - hydration_pts**
```
=SUMIFS(Daily_Log!I:I,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)+SUMIFS(Daily_Log!J:J,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)*2+SUMIFS(Daily_Log!K:K,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)*3
```
*Sums: water_1 (I) + water_2*2 (J) + water_3*3 (K) for the week*

**Column H - cardio_pts**
```
=SUMIFS(Daily_Log!D:D,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)
```
*Sums: cardio (D) for the week*

**Column I - exercise_pts**
```
=SUMIFS(Daily_Log!N:N,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)+SUMIFS(Daily_Log!O:O,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)
```
*Sums: pilates (N) + gym (O) for the week*

**Column J - raw_score**
```
=E2+F2+G2+H2+I2
```

**Column K - cheat_penalty**
```
=SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)*3
```
*Cheat meals * 3 points penalty each*

**Column L - final_score**
```
=MAX(0,J2-K2)
```

**Column M - percentage**
```
=L2/103
```
*Format this column as Percentage*

**Column N - status**
```
=IF(M2>=1,"Perfect",IF(M2>=0.85,"Successful",IF(M2>=0.7,"Needs Improvement","Danger")))
```

---

## Sheet 2: Monthly_Summary

### Setup Instructions

1. Create a new sheet named `Monthly_Summary`
2. Run `/setup_sheets` in Telegram - this automatically creates:
   - Headers in Row 1
   - 3 months of formulas (Jan, Feb, Mar 2026)
3. Or manually add headers: `month`, `start_date`, `end_date`, `days_tracked`, `total_pts`, `max_possible`, `cheat_meals`, `cheat_penalty`, `final_score`, `avg_daily`, `perfect_days`, `status`

### Column Formulas (Enter in Row 2, drag down)

**Column A - month**
```
=TEXT(B2,"YYYY-MM")
```

**Column B - start_date**
Manual: Enter first day of month (e.g., `2026-01-01`)

**Column C - end_date**
```
=EOMONTH(B2,0)
```

**Column D - days_tracked**
```
=COUNTIFS(Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)
```

**Column E - total_pts**
```
=SUMIFS(Daily_Log!S:S,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)
```

**Column F - max_possible**
```
=D2*14+SUMPRODUCT((Daily_Log!A:A>=B2)*(Daily_Log!A:A<=C2)*(Daily_Log!N:N+Daily_Log!O:O>0))
```
*14 base pts per day + bonus for exercise days*

**Column G - cheat_meals**
```
=SUMIFS(Daily_Log!P:P,Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2)
```

**Column H - cheat_penalty**
```
=G2*3
```

**Column I - final_score**
```
=MAX(0,E2-H2)
```

**Column J - avg_daily**
```
=IF(D2>0,I2/D2,0)
```

**Column K - perfect_days**
```
=COUNTIFS(Daily_Log!A:A,">="&B2,Daily_Log!A:A,"<="&C2,Daily_Log!Q:Q,14)
```
*Days with 14 daily_pts (excluding exercise)*

**Column L - status**
```
=IF(J2>=14,"Perfect",IF(J2>=12,"Excellent",IF(J2>=10,"Good",IF(J2>=8,"Needs Work","Danger"))))
```

---

## Sheet 3: Dashboard

### Setup Instructions

1. Create a new sheet named `Dashboard`
2. Run `/setup_sheets` in Telegram - this automatically creates all labels and formulas
3. Or manually enter labels and formulas as shown below
4. The layout uses specific cell positions

### Section A: Current Week (Rows 1-6)

| Cell | Content |
|------|---------|
| A1 | `CURRENT WEEK` |
| A2 | `Week #` |
| B2 | `=ISOWEEKNUM(TODAY())` |
| A3 | `Days Tracked` |
| B3 | `=COUNTIFS(Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())` |
| A4 | `Points` |
| B4 | `=SUMIFS(Daily_Log!S:S,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())` |
| A5 | `Max Possible` |
| B5 | `=B3*15` |
| A6 | `Progress` |
| B6 | `=IF(B5>0,B4/B5,0)` |

*Format B6 as Percentage*

### Section B: Today (Rows 8-14)

| Cell | Content |
|------|---------|
| A8 | `TODAY` |
| A9 | `Date` |
| B9 | `=TODAY()` |
| A10 | `Daily Pts` |
| B10 | `=IFERROR(INDEX(Daily_Log!Q:Q,MATCH(TODAY(),Daily_Log!A:A,0)),0)` |
| A11 | `Exercise` |
| B11 | `=IFERROR(INDEX(Daily_Log!R:R,MATCH(TODAY(),Daily_Log!A:A,0)),0)` |
| A12 | `Total` |
| B12 | `=B10+B11` |
| A13 | `Cheat Meals` |
| B13 | `=IFERROR(INDEX(Daily_Log!P:P,MATCH(TODAY(),Daily_Log!A:A,0)),0)` |
| A14 | `Status` |
| B14 | `=IF(B12>=15,"Perfect",IF(B12>=10,"Good","Behind"))` |

### Section C: Stats (Rows 16-22)

| Cell | Content |
|------|---------|
| A16 | `STATS` |
| A17 | `Total Days` |
| B17 | `=COUNTA(Daily_Log!A:A)-1` |
| A18 | `Perfect Days` |
| B18 | `=COUNTIF(Daily_Log!Q:Q,14)` |
| A19 | `Avg Daily Pts` |
| B19 | `=IFERROR(AVERAGE(Daily_Log!S:S),0)` |
| A20 | `Total Cheat` |
| B20 | `=SUM(Daily_Log!P:P)` |
| A21 | `Best Week` |
| B21 | `=MAX(Weekly_Summary!L:L)` |
| A22 | `Current Weight` |
| B22 | `=IFERROR(INDEX(Config!B:B,MATCH("current_weight",Config!A:A,0)),"--")` |

### Section D: This Week by Category (Rows 24-30)

| Cell | Content |
|------|---------|
| A24 | `THIS WEEK BY CATEGORY` |
| A25 | `Sleep` |
| B25 | `=SUMIFS(Daily_Log!C:C,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())+SUMIFS(Daily_Log!L:L,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())+SUMIFS(Daily_Log!M:M,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())` |
| C25 | `/21` |
| A26 | `Nutrition` |
| B26 | `=SUMIFS(Daily_Log!E:E,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())+SUMIFS(Daily_Log!F:F,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())+SUMIFS(Daily_Log!G:G,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())+SUMIFS(Daily_Log!H:H,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())` |
| C26 | `/28` |
| A27 | `Hydration` |
| B27 | `=SUMIFS(Daily_Log!I:I,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())+SUMIFS(Daily_Log!J:J,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())*2+SUMIFS(Daily_Log!K:K,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())*3` |
| C27 | `/42` |
| A28 | `Cardio` |
| B28 | `=SUMIFS(Daily_Log!D:D,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())` |
| C28 | `/7` |
| A29 | `Exercise` |
| B29 | `=SUMIFS(Daily_Log!N:N,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())+SUMIFS(Daily_Log!O:O,Daily_Log!A:A,">="&(TODAY()-WEEKDAY(TODAY(),2)+1),Daily_Log!A:A,"<="&TODAY())` |
| C29 | `/5` |
| A30 | `TOTAL` |
| B30 | `=SUM(B25:B29)` |
| C30 | `/103` |

---

## Conditional Formatting Rules

### Weekly_Summary - Status Column (N)

1. Select column N (N2:N)
2. Format > Conditional formatting
3. Add rules:
   - **Green** (#b7e1cd): Custom formula `=OR(N2="Perfect",N2="Successful")`
   - **Yellow** (#fce8b2): Text is exactly "Needs Improvement"
   - **Red** (#f4c7c3): Text is exactly "Danger"

### Monthly_Summary - Status Column (L)

1. Select column L (L2:L)
2. Add rules:
   - **Green** (#b7e1cd): Custom formula `=OR(L2="Perfect",L2="Excellent")`
   - **Yellow** (#fce8b2): Text is exactly "Good"
   - **Orange** (#f9cb9c): Text is exactly "Needs Work"
   - **Red** (#f4c7c3): Text is exactly "Danger"

### Dashboard - Progress Cell (B6)

1. Select B6
2. Format > Conditional formatting
3. Color scale: Min (Red) - Midpoint 50% (Yellow) - Max (Green)

### Daily_Log - Action Columns (C:O)

1. Select C2:O (extend to your data range)
2. Add rule:
   - **Green fill** (#b7e1cd): Custom formula `=C2=1`

---

## Max Points Reference

| Category | Daily Max | Weekly Max (7 days) |
|----------|-----------|---------------------|
| Sleep (wake+bedroom+bed) | 3 | 21 |
| Nutrition (B+L+S+D) | 4 | 28 |
| Hydration (1+2+3 pts) | 6 | 42 |
| Cardio | 1 | 7 |
| Exercise (pilates+gym) | varies | 5 |
| **Daily Total** | **14** + exercise | - |
| **Weekly Total** | - | **103** |

---

## Verification Checklist

- [ ] Daily_Log sheet has headers in row 1 with columns A-S
- [ ] Weekly_Summary formulas auto-calculate when Daily_Log has data
- [ ] Monthly_Summary shows correct date ranges
- [ ] Dashboard TODAY section shows 0 if no data for today
- [ ] Dashboard CURRENT WEEK uses Monday as start
- [ ] Percentage columns are formatted as %
- [ ] Conditional formatting colors appear correctly

---

## Troubleshooting

**#REF! errors**: Check that sheet names match exactly (`Daily_Log`, `Weekly_Summary`, `Config`)

**#VALUE! errors**: Ensure date columns contain actual dates, not text

**0 values when data exists**: Verify date format in Daily_Log matches YYYY-MM-DD

**WEEKDAY function**: Uses `WEEKDAY(date,2)` where 2 = Monday is day 1
