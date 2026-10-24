# Customer demo script (≤ 5 minutes)

**Audience:** day-ahead procurement team at a UK utility. **Goal:** show that the pilot answers their two questions with evidence they can trust.
Before recording: open the deployed app once so the backend is awake and January data is cached (first load is slower).

## 0:00 – The problem (40 s)
"You buy power on the day-ahead market, the day before delivery. To know how much you must buy from thermal plants, you lean on the wind forecast. Two questions: *what forecast did we actually have when we had to decide?* and *how far off was it?* This pilot answers both, using only Elexon's national wind data for January 2026."

## 0:40 – Overview page (90 s)
- Point at the title and the **decision cutoff banner**: "We assume you decide at 09:00 UK time the day before. For each half-hour we use only the latest forecast published before that. A better forecast published at 14:00 is deliberately ignored – you didn't have it."
- Pick a day (e.g. 15 Jan). Show the **forecast vs actual chart**: "Dashed green is what you were told; navy is what happened. Units are MW."
- Read the four KPI cards: MAE ("typically off by X MW"), RMSE ("big misses weigh more"), MBE ("positive = we were told too much wind, so we under-bought"), WAPE ("error as a share of real output").
- Show the **over/under split**: "Which direction did the forecast mislead us, and by how much."

## 2:10 – Forecast Explorer (60 s)
"Don't take our word for it." Open one day, sort by absolute error. Show a row: target time, forecast, actual, error, **when that forecast was published**, and the cutoff. "Every number is traceable to a specific forecast publication."
Mention honestly: "The forecast feed is hourly, so we compare the hourly periods – coverage is shown, nothing is estimated."

## 3:10 – Accuracy Analysis (75 s)
- Full January: aggregate metrics, then **daily accuracy** chart: "Here are the days to be cautious about."
- **Error distribution**: "Is the forecast balanced, or does it lean one way?"
- **Largest errors table**: "These are the periods that would have hurt most; you can check what the weather was doing."

## 4:25 – Business value and close (35 s)
- Quantified forecast error lets you set a **safety margin** for thermal purchases instead of guessing.
- Bias (MBE) shows whether to systematically buy more or less.
- Same method works for other months by changing the date scope.
"Next steps: extend to other months, add intraday views, and agree the exact decision-time with your desk."
