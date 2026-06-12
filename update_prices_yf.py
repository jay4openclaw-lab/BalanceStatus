import os, sys
import datetime
import pandas as pd
import yfinance as yf
import re

# Determine previous business day (Korean market calendar approximated by BDay)
prev_day = (pd.Timestamp('today') - pd.tseries.offsets.BDay(1)).date()
date_str = prev_day.strftime('%Y-%m-%d')

# Load holdings CSV (must contain a 'ticker' column with KRX codes, e.g., '005930')
holdings_path = os.path.expanduser('~/portfolio_holdings.csv')
if not os.path.exists(holdings_path):
    print(f'Holdings file not found at {holdings_path}')
    sys.exit(1)

holdings = pd.read_csv(holdings_path, dtype={'ticker': str})
if 'ticker' not in holdings.columns:
    print('Holdings CSV must contain a "ticker" column')
    sys.exit(1)

# Prepare a list of Yahoo Finance tickers (Korean stocks end with .KS)
# If the user already provides correct Yahoo symbols, they can be used directly.
# Here we assume plain KRX numeric codes, so we append '.KS'.
holdings['yf_ticker'] = holdings['ticker'].apply(lambda x: f"{x}.KS")

# Download close price for the previous business day for all tickers at once
try:
    # yfinance treats the end date as exclusive, so we add one day to include the target date
    end_str = (prev_day + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    data = yf.download(holdings['yf_ticker'].tolist(), start=date_str, end=end_str, progress=False)
except Exception as e:
    print(f'Error fetching data from yfinance: {e}')
    sys.exit(1)

# yfinance returns a multi-index DataFrame when multiple tickers are requested.
# We only need the 'Close' column.
if data.empty:
    # Likely a holiday/weekend – skip update.
    print(f'No market data for {date_str} (holiday/weekend). Skipping.')
    sys.exit(0)

# Extract close prices – handle single ticker vs multiple ticker shape.
if isinstance(data.columns, pd.MultiIndex):
    close_prices = data['Close'].iloc[0]  # first (and only) row for that date
else:
    close_prices = data['Close']

# Build a DataFrame of ticker -> close price
price_df = close_prices.reset_index()
price_df.columns = ['yf_ticker', 'close_price']

# Merge with holdings to retain original ticker column and compute valuation
merged = holdings.merge(price_df, on='yf_ticker', how='left')
# Calculate valuation = close_price * quantity
merged['valuation'] = merged['close_price'] * merged['quantity']
# Remove ticker columns (original ticker and Yahoo ticker) as they are not needed in the report
merged = merged.drop(columns=['ticker', 'yf_ticker'])
merged['date'] = prev_day

# Output daily report CSV (now includes valuation column)
report_path = os.path.join(os.path.dirname(__file__), f"daily_report_{prev_day.strftime('%Y%m%d')}.csv")
merged.to_csv(report_path, index=False)
print(f'Report written to {report_path}')

# After report CSV is written, regenerate index.html from the CSV data (no ticker column, include valuation)
# Read the newly written CSV
report_df = pd.read_csv(report_path)
# Build HTML content
html_parts = []
html_parts.append('<!DOCTYPE html>')
html_parts.append('<html lang="ko">')
html_parts.append('<head>')
html_parts.append('<meta charset="UTF-8">')
html_parts.append('<title>포트폴리오 보유 현황 리포트</title>')
# Timestamp (single)
html_parts.append(f"<p style='text-align:center;color:#555;'>Last updated: {prev_day.strftime('%Y-%m-%d')}</p>")
html_parts.append('<style>')
html_parts.append('  body {font-family: Arial, Helvetica, sans-serif; background:#f9f9f9; padding:20px;}')
html_parts.append('  h1 {text-align:center; color:#333;}')
html_parts.append('  table {border-collapse:collapse; width:100%; margin:auto; background:#fff; box-shadow:0 2px 5px rgba(0,0,0,0.1);}')
html_parts.append('  th, td {border:1px solid #ddd; padding:8px; text-align:center;}')
html_parts.append('  th {background:#4a90e2; color:#fff; font-weight:bold;}')
html_parts.append('  tr:nth-child(even) {background:#f2f2f2;}')
html_parts.append('  tr:hover {background:#e1f5fe;}')
html_parts.append('</style>')
html_parts.append('</head>')
html_parts.append('<body>')
html_parts.append('<h1>포트폴리오 보유 현황 리포트</h1>')
html_parts.append('<table>')
# Table header from DataFrame columns
html_parts.append('<thead><tr>')
for col in report_df.columns:
    html_parts.append(f'<th>{col}</th>')
html_parts.append('</tr></thead>')
# Table body
html_parts.append('<tbody>')
for _, row in report_df.iterrows():
    html_parts.append('<tr>')
    for val in row:
        # Format numbers with commas for readability
        if isinstance(val, (int, float)):
            cell = f"{val:,.0f}" if isinstance(val, (int,)) else f"{val:,.2f}"
        else:
            cell = str(val)
        html_parts.append(f'<td>{cell}</td>')
    html_parts.append('</tr>')
html_parts.append('</tbody>')
html_parts.append('</table>')
html_parts.append('</body>')
html_parts.append('</html>')
new_html = "\n".join(html_parts)
# Write the regenerated index.html
index_path = os.path.join(os.path.dirname(__file__), 'index.html')
with open(index_path, 'w', encoding='utf-8') as f:
    f.write(new_html)
print('index.html regenerated from CSV')
# Update index.html with a timestamp (replace any existing timestamp paragraph or insert after </title>)
# This block is now redundant since timestamp is already included, but kept for safety
if os.path.exists(index_path):
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    timestamp_html = f"<p style='text-align:center;color:#555;'>Last updated: {prev_day.strftime('%Y-%m-%d')}</p>"
    html, count = re.subn(r"<p style='text-align:center;color:#555;'>Last updated: .*?</p>", timestamp_html, html)
    if count == 0:
        html = html.replace('</title>', f"</title>\n{timestamp_html}")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('index.html updated with timestamp')
else:
    print('index.html not found, skipping HTML update')

# Git operations – commit and push changes
repo_dir = os.path.dirname(__file__)
os.chdir(repo_dir)
os.system('git add .')
os.system(f"git commit -m 'Update prices for {prev_day}'")
os.system('git push origin main')
