import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Ensure pykrx is available
try:
    from pykrx import stock
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pykrx'])
    from pykrx import stock

# -------------------------------------------------------------------
# Paths (relative to this script)
# -------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PORTFOLIO_CSV = os.path.join(BASE_DIR, "portfolio_KR.csv")
TEMPLATE_HTML = os.path.join(BASE_DIR, "index_tpl.html")
OUTPUT_CSV = os.path.join(BASE_DIR, "daily_report_20260619_kr.csv")
OUTPUT_HTML = os.path.join(BASE_DIR, "index.html")

# -------------------------------------------------------------------
# Load portfolio (skip the header line in the CSV)
# -------------------------------------------------------------------
cols = ["market", "account", "name", "quantity", "buy_price", "Ticker"]
portfolio = pd.read_csv(PORTFOLIO_CSV, header=None, names=cols, skiprows=1)

# -------------------------------------------------------------------
# Helper to fetch yesterday's close price
#   1️⃣ Try yfinance with .KS and .KQ suffixes (covers KOSPI/KOSDAQ)
#   2️⃣ Fallback to pykrx for Korean domestic market (requires YYYYMMDD format)
# -------------------------------------------------------------------
def fetch_prev_close(ticker: str):
    # yfinance attempt
    for suffix in [".KS", ".KQ"]:
        yf_ticker = f"{ticker}{suffix}"
        try:
            hist = yf.Ticker(yf_ticker).history(period="2d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            continue
    # pykrx fallback – use yesterday's trading day
    try:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")
        price = stock.get_market_price_day(date_str, ticker)
        if price is not None and price != 0:
            return float(price)
    except Exception:
        pass
    return None

# -------------------------------------------------------------------
# Retrieve previous close for each ticker
# -------------------------------------------------------------------
portfolio["prev_close"] = portfolio["Ticker"].apply(fetch_prev_close)

# -------------------------------------------------------------------
# Calculate valuation, profit, profit_rate (ignore rows where price is missing)
# -------------------------------------------------------------------
portfolio["valuation"] = portfolio.apply(
    lambda r: r["quantity"] * r["prev_close"] if pd.notna(r["prev_close"]) else None,
    axis=1,
)
portfolio["profit"] = portfolio.apply(
    lambda r: (r["prev_close"] - r["buy_price"]) * r["quantity"] if pd.notna(r["prev_close"]) else None,
    axis=1,
)
portfolio["profit_rate"] = portfolio.apply(
    lambda r: ((r["prev_close"] - r["buy_price"]) / r["buy_price"] * 100) if pd.notna(r["prev_close"]) else None,
    axis=1,
)

# -------------------------------------------------------------------
# Prepare output DataFrame (use original column names for sorting, rename later)
# -------------------------------------------------------------------
out = portfolio[["account", "name", "quantity", "buy_price", "prev_close", "valuation", "profit", "profit_rate"]].copy()
# Sort by profit descending, treating NaN as lowest
out["profit_sort"] = out["profit"].fillna(float('-inf'))
out.sort_values(by="profit_sort", ascending=False, inplace=True)
out.drop(columns="profit_sort", inplace=True)

# Rename columns to Korean headers
out.columns = [
    "\uacc4\uc88c",
    "\uc885\ubaa9\uba85",
    "\ubcf4\uc720\uc218\ub7c9",
    "\ub9e4\uc785\uac00(\uc6d0)",
    "\uc5b4\uc81c\uc885\uac00(\uc6d0)",
    "\ud3c9\uac00\uae08\uc561(\uc6d0)",
    "\uc218\uc775(\uc6d0)",
    "\uc218\uc775\ub960(%)",
]

# Save CSV (UTF-8 with BOM for Excel)
out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

# -------------------------------------------------------------------
# Build HTML rows (profit cells get class based on sign)
# -------------------------------------------------------------------
rows_html = []
for _, row in out.iterrows():
    profit = row["\uc218\uc775(\uc6d0)"]
    profit_rate = row["\uc218\uc775\ub960(%)"]
    cls = "positive" if pd.notna(profit) and profit >= 0 else "negative"
    def fmt(v):
        return "" if pd.isna(v) else str(int(v))
    rows_html.append(
        f"<tr>"
        f"<td>{row['\uacc4\uc88c']}</td>"
        f"<td>{row['\uc885\ubaa9\uba85']}</td>"
        f"<td>{fmt(row['\ubcf4\uc720\uc218\ub7c9'])}</td>"
        f"<td>{fmt(row['\ub9e4\uc785\uac00(\uc6d0)'])}</td>"
        f"<td>{fmt(row['\uc5b4\uc81c\uc885\uac00(\uc6d0)'])}</td>"
        f"<td>{fmt(row['\ud3c9\uac00\uae08\uc561(\uc6d0)'])}</td>"
        f"<td class=\"{cls}\">{fmt(row['\uc218\uc775(\uc6d0)'])}</td>"
        f"<td class=\"{cls}\">{f'{profit_rate:.2f}%' if pd.notna(profit_rate) else ''}</td>"
        f"</tr>"
    )

# -------------------------------------------------------------------
# Insert rows into template and update "Last updated" date
# -------------------------------------------------------------------
with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
    template = f.read()

today_str = datetime.now().strftime("%Y-%m-%d")
template = template.replace("Last updated: 2026-06-16", f"Last updated: {today_str}")

import re
new_body = "\n".join(rows_html)
output_html = re.sub(r"(<tbody>)(.*?)(</tbody>)", f"\1\n{new_body}\n\3", template, flags=re.DOTALL)

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(output_html)

print("Report generated:", OUTPUT_CSV, "and", OUTPUT_HTML)
