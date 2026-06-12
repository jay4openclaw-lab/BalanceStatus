import os, sys
import datetime
import pandas as pd
from pykrx import stock

# Determine previous trading day (yesterday)
today = datetime.date.today()
prev_day = today - datetime.timedelta(days=1)
date_str = prev_day.strftime('%Y%m%d')

# Fetch market data for the previous day
try:
    df = stock.get_market_ohlcv_by_date(date_str, date_str)
except Exception as e:
    print(f"Error fetching market data: {e}")
    sys.exit(0)

if df.empty:
    # Probably a holiday or weekend – skip update
    print(f"No market data for {date_str} (holiday/weekend). Skipping.")
    sys.exit(0)

# Load holdings CSV (assumed to be in repo root)
holdings_path = os.path.join(os.path.dirname(__file__), 'portfolio_holdings.csv')
if not os.path.exists(holdings_path):
    print(f"Holdings file not found at {holdings_path}")
    sys.exit(1)

holdings = pd.read_csv(holdings_path, dtype={'ticker': str})
# Ensure ticker column matches KRX code format (six digits string)
if 'ticker' not in holdings.columns:
    print('Holdings CSV must contain a "ticker" column')
    sys.exit(1)

# Merge with market close price
merged = holdings.merge(df[['종가']], left_on='ticker', right_index=True, how='left')
merged.rename(columns={'종가': 'close_price'}, inplace=True)
merged['date'] = prev_day

# Output daily report CSV
report_path = os.path.join(os.path.dirname(__file__), f'daily_report_{date_str}.csv')
merged.to_csv(report_path, index=False)
print(f"Report written to {report_path}")

# Update index.html to show last update date
index_path = os.path.join(os.path.dirname(__file__), 'index.html')
if os.path.exists(index_path):
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    # Insert/update a timestamp paragraph after </title>
    timestamp_html = f"<p style='text-align:center;color:#555;'>Last updated: {prev_day.strftime('%Y-%m-%d')}</p>"
    # Simple replace if placeholder exists
    if '<!-- UPDATE_TIMESTAMP -->' in html:
        html = html.replace('<!-- UPDATE_TIMESTAMP -->', timestamp_html)
    else:
        # Insert after </title>
        html = html.replace('</title>', f"</title>\n{timestamp_html}")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('index.html updated with timestamp')
else:
    print('index.html not found, skipping HTML update')

# Git operations
repo_dir = os.path.dirname(__file__)
os.chdir(repo_dir)
os.system('git add .')
os.system(f"git commit -m 'Update prices for {prev_day}'")
os.system('git push origin main')
