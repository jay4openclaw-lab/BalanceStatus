import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# pykrx import (install if missing)
try:
    from pykrx import stock
except ImportError:
    # Install pykrx via pip if not present
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pykrx'])
    from pykrx import stock

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PORTFOLIO_CSV = os.path.join(BASE_DIR, 'portfolio_KR.csv')
TEMPLATE_HTML = os.path.join(BASE_DIR, 'index_tpl.html')
OUTPUT_CSV = os.path.join(BASE_DIR, f'daily_report_20260619_kr.csv')
OUTPUT_HTML = os.path.join(BASE_DIR, 'index.html')

# Read portfolio data (skip header line)
cols = ['market', 'account', 'name', 'quantity', 'buy_price', 'Ticker']
portfolio = pd.read_csv(PORTFOLIO_CSV, header=None, names=cols, skiprows=1)

# Helper to get yesterday's close price using yfinance; fallback to pykrx if yfinance fails
def get_prev_close(ticker):
    yf_ticker = f"{ticker}.KS"
    try:
        data = yf.Ticker(yf_ticker).history(period='2d')
        if not data.empty:
            # The last row should be the most recent trading day (yesterday if market closed)
            return float(data['Close'][-1])
    except Exception as e:
        print(f"YFinance error for {yf_ticker}: {e}")
    # Fallback to pykrx (KOSPI/KOSDAQ) – use yesterday's date
    try:
        # Determine market type: if ticker starts with '0' or '1' -> KOSPI, else KOSDAQ? Simplify by trying both.
        today = datetime.now().date()
        yesterday = today - pd.Timedelta(days=1)
        price = stock.get_market_price_day(ticker, yesterday.strftime('%Y%m%d'))
        if price is not None and price != 0:
            return float(price)
    except Exception as e:
        print(f"pykrx fallback error for {ticker}: {e}")
    return None

# Fetch previous close prices
portfolio['prev_close'] = portfolio['Ticker'].apply(get_prev_close)

# Compute valuation, profit, profit_rate (handle missing prices)
portfolio['valuation'] = portfolio.apply(lambda r: r['quantity'] * r['prev_close'] if pd.notna(r['prev_close']) else None, axis=1)
portfolio['profit'] = portfolio.apply(lambda r: (r['prev_close'] - r['buy_price']) * r['quantity'] if pd.notna(r['prev_close']) else None, axis=1)
portfolio['profit_rate'] = portfolio.apply(lambda r: ((r['prev_close'] - r['buy_price']) / r['buy_price'] * 100) if pd.notna(r['prev_close']) else None, axis=1)

# Prepare output DataFrame with required column order and Korean header names
out_df = portfolio[['account', 'name', 'quantity', 'buy_price', 'prev_close', 'valuation', 'profit', 'profit_rate']].copy()
out_df.columns = ['계좌', '종목명', '보유수량', '매입가(원)', '어제종가(원)', '평가금액(원)', '수익(원)', '수익률(%)']

# Sort by profit descending (treat None as lowest)
out_df['수익(원)'] = out_df['수익(원)'].fillna(float('-inf'))
out_df.sort_values(by='수익(원)', ascending=False, inplace=True)
out_df['수익(원)'] = out_df['수익(원)'].replace(float('-inf'), pd.NA)

# Save CSV (UTF-8 with BOM for Excel compatibility)
out_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

# Build HTML rows
rows = []
for _, row in out_df.iterrows():
    profit = row['수익(원)']
    profit_rate = row['수익률(%)']
    cls = 'positive' if pd.notna(profit) and profit >= 0 else 'negative'
    rows.append(
        f"<tr>"
        f"<td>{row['계좌']}</td>"
        f"<td>{row['종목명']}</td>"
        f"<td>{int(row['보유수량'])}</td>"
        f"<td>{int(row['매입가(원)'])}</td>"
        f"<td>{int(row['어제종가(원)']) if pd.notna(row['어제종가(원)']) else ''}</td>"
        f"<td>{int(row['평가금액(원)']) if pd.notna(row['평가금액(원)']) else ''}</td>"
        f"<td class='{{cls}}'>{int(row['수익(원)']) if pd.notna(row['수익(원)']) else ''}</td>"
        f"<td class='{{cls}}'>{profit_rate:.2f}%" if pd.notna(profit_rate) else ""
        f"</td></tr>"
    )

# Load template HTML and replace placeholder date and tbody
with open(TEMPLATE_HTML, 'r', encoding='utf-8') as f:
    template = f.read()

# Update Last updated date (use today's date)
today_str = datetime.now().strftime('%Y-%m-%d')
template = template.replace('Last updated: 2026-06-16', f'Last updated: {today_str}')

# Insert rows into <tbody>
import re
new_body = '\n'.join(rows)
output_html = re.sub(r'(<tbody>)(.*?)(</tbody>)', f'\1\n{new_body}\n\3', template, flags=re.DOTALL)

# Write final HTML
with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(output_html)

print('Report generated:', OUTPUT_CSV, 'and', OUTPUT_HTML)