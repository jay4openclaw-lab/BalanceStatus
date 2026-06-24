import os
import pandas as pd
import yfinance as yf
from datetime import datetime
import re

# Paths relative to this script
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PORTFOLIO_CSV = os.path.join(BASE_DIR, "portfolio_US.csv")
TEMPLATE_HTML = os.path.join(BASE_DIR, "status_tpl.html")
OUTPUT_CSV = os.path.join(BASE_DIR, f"daily_report_{datetime.now().strftime('%Y%m%d')}_us.csv")
OUTPUT_HTML = os.path.join(BASE_DIR, "status.html")

# Load portfolio (skip the first header line in the CSV)
cols = ["market", "account", "name", "quantity", "buy_price", "Ticker"]
portfolio = pd.read_csv(PORTFOLIO_CSV, header=None, names=cols, skiprows=1, dtype={"Ticker": str})

# Ensure numeric columns are proper types (remove commas in buy_price if any)
portfolio["buy_price"] = portfolio["buy_price"].astype(str).str.replace(",", "").astype(float)
portfolio["quantity"] = portfolio["quantity"].astype(int)

# Helper: fetch yesterday's close price using yfinance (no suffix for US tickers)
def fetch_prev_close(ticker: str):
    try:
        hist = yf.Ticker(ticker).history(period="2d")
        if not hist.empty:
            # The last row should be the most recent trading day (yesterday)
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None

# Retrieve previous close price for each ticker
portfolio["prev_close"] = portfolio["Ticker"].apply(fetch_prev_close)

# Compute valuation, profit, profit_rate (skip rows without price)
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

# Prepare output DataFrame with Korean column names (same as KR version)
# Prepare output DataFrame for CSV (without Ticker column)
out_df = portfolio[["account", "name", "quantity", "buy_price", "prev_close", "valuation", "profit", "profit_rate", "Ticker"]].copy()
# Rename columns for CSV output (exclude Ticker from header)
out_df.columns = [
    "계좌",
    "종목명",
    "보유수량",
    "매입가(USD)",
    "어제종가(USD)",
    "평가금액(USD)",
    "수익(USD)",
    "수익률(%)",
    "Ticker"
]
# When saving CSV, drop the internal Ticker column so the file matches the template format
csv_df = out_df.drop(columns=["Ticker"])


# Sort by profit descending (treat missing profit as lowest)
out_df["profit_sort"] = out_df["수익(USD)"].fillna(float('-inf'))
out_df.sort_values(by="profit_sort", ascending=False, inplace=True)
out_df.drop(columns="profit_sort", inplace=True)

# Save CSV (UTF-8 with BOM for Excel compatibility)
csv_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

# Build HTML rows; profit cells get class based on sign when value exists
# Also format numeric fields with commas for better readability (except the account column)
# and strip any stray control characters that might appear in the HTML output.
rows_html = []

def fmt(v):
    # Strip control characters and format numbers with commas
    if pd.isna(v):
        return ""
    try:
        iv = int(v)
        return f"{iv:,}"
    except Exception:
        s = str(v)
        return s.translate({ord(c): None for c in '\u200b\u200c\u200d\uFEFF'})

for _, row in out_df.iterrows():
    profit = row["수익(USD)"]
    profit_rate = row["수익률(%)"]
    cls = "positive" if pd.notna(profit) and profit >= 0 else "negative"
    rows_html.append(
        f"<tr>"
        f"<td>{row['계좌']}</td>"
        f"<td><a href=\"https://www.google.com/search?q={row['Ticker']}\" target=\"_blank\">{row['종목명']}</a></td>"
        f"<td>{fmt(row['보유수량'])}</td>"
        f"<td>{fmt(row['매입가(USD)'])}</td>"
        f"<td>{fmt(row['어제종가(USD)'])}</td>"
        f"<td>{fmt(row['평가금액(USD)'])}</td>"
        f"<td class=\"{cls}\">{fmt(row['수익(USD)'])}</td>"
        f"<td class=\"{cls}\">{f'{profit_rate:.2f}%' if pd.notna(profit_rate) else ''}</td>"
        f"</tr>"
    )

# Add a summary "합계" row
# Compute totals and profit rate (avoid division by zero)

total_valuation = out_df["평가금액(USD)"].sum()
total_profit = out_df["수익(USD)"].sum()
# denominator = total_valuation - total_profit
# If denominator is zero, set profit_rate to 0 to avoid ZeroDivisionError

denominator = total_valuation - total_profit
total_profit_rate = (total_profit / denominator * 100) if denominator != 0 else 0
total_cls = "positive" if total_profit >= 0 else "negative"
rows_html.append(
    f"<tr>"
    f"<td colspan=\"5\">합계</td>"
    f"<td>{fmt(total_valuation)}</td>"
    f"<td class=\"{total_cls}\">{fmt(total_profit)}</td>"
    f"<td class=\"{total_cls}\">{f'{total_profit_rate:.2f}%'}"
    f"</td>"
    f"</tr>"
)

# Insert rows into the HTML template and update the "Last updated" date
with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
    template = f.read()
    # Remove any stray control characters from the template
    template = template.translate({ord(c): None for c in '\u200b\u200c\u200d\uFEFF'})

today_str = datetime.now().strftime("%Y-%m-%d")
template = template.replace("Last updated: 2026-06-16", f"Last updated: {today_str}")

new_body = "\n".join(rows_html)
output_html = re.sub(r"(<tbody>)(.*?)(</tbody>)", f"\1\n{new_body}\n\3", template, flags=re.DOTALL)

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    cleaned_html = output_html.translate({ord(c): None for c in '\u0000\u0001\u0002\u0003\u200b\u200c\u200d\uFEFF'})
    f.write(cleaned_html)

print("Report generated:", OUTPUT_CSV, "and", OUTPUT_HTML)
