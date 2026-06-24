import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Try to import pykrx; install if missing
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
OUTPUT_CSV = os.path.join(BASE_DIR, f"daily_report_20260619_kr.csv")
OUTPUT_HTML = os.path.join(BASE_DIR, "index.html")

# -------------------------------------------------------------------
# Load portfolio (skip the header line present in the CSV)
# -------------------------------------------------------------------
cols = ["market", "account", "name", "quantity", "buy_price", "Ticker"]
portfolio = pd.read_csv(PORTFOLIO_CSV, header=None, names=cols, skiprows=1)

# -------------------------------------------------------------------
# Helper: get previous close price via yfinance, fall back to pykrx
# -------------------------------------------------------------------
def fetch_prev_close(ticker: str):
    # First try yfinance (.KS suffix for Korean market)
    yf_ticker = f"{ticker}.KS"
    try:
        hist = yf.Ticker(yf_ticker).history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass  # ignore yfinance errors

    # Fallback to pykrx – use yesterday's date
    try:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")
        # pykrx expects string ticker without leading zeros? It works with the code as string.
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
# Compute valuation, profit, profit_rate (skip rows without price)
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
# Prepare output DataFrame with Korean column headers
# -------------------------------------------------------------------
out_df = portfolio[["account", "name", "quantity", "buy_price", "prev_close", "valuation", "profit", "profit_rate"]].copy()
out_df.columns = [
    "계좌",
    "종목명",
    "보유수량",
    "매입가(원)",
    "어제종가(원)",
    "평가금액(원)",
    "수익(원)",
    "수익률(%)",
]

# Sort by profit descending (treat None as lowest)
out_df["수익(원)"] = out_df["수익(원)"].fillna(float('-inf'))
out_df.sort_values(by="수익(원)", ascending=False, inplace=True)
out_df["수익(원)"] = out_df["수익(원)"].replace(float('-inf'), pd.NA)

# Save CSV (UTF-8‑sig for Excel compatibility)
out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

# -------------------------------------------------------------------
# Build HTML rows with color classes for profit sign
# -------------------------------------------------------------------
rows_html = []
for _, row in out_df.iterrows():
    profit = row["수익(원)"]
    profit_rate = row["수익률(%)"]
    cls = "positive" if pd.notna(profit) and profit >= 0 else "negative"
    def fmt(val):
        return "" if pd.isna(val) else str(int(val))
    rows_html.append(
        f"<tr>"
        f"<td>{row['계좌']}</td>"
        f"<td>{row['종목명']}</td>"
        f"<td>{fmt(row['보유수량'])}</td>"
        f"<td>{fmt(row['매입가(원)'])}</td>"
        f"<td>{fmt(row['어제종가(원)'])}</td>"
        f"<td>{fmt(row['평가금액(원)'])}</td>"
        f"<td class='{{cls}}'>{fmt(row['수익(원)'])}</td>"
        f"<td class='{{cls}}'>{f'{profit_rate:.2f}%' if pd.notna(profit_rate) else ''}</td>"
        f"</tr>"
    )

# -------------------------------------------------------------------
# Insert rows into the HTML template and update the date stamp
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
