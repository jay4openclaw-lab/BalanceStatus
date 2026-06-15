import os, sys, datetime
import pandas as pd
import yfinance as yf
import re

# Determine previous business day (Korean market calendar approximated by BDay)
prev_day = (pd.Timestamp('today') - pd.tseries.offsets.BDay(1)).date()
date_str = prev_day.strftime('%Y-%m-%d')

# Load holdings CSV (must contain columns: account, ticker, name, quantity, buy_price)
holdings_path = os.path.expanduser('~/portfolio_holdings.csv')
if not os.path.exists(holdings_path):
    print(f'Holdings file not found at {holdings_path}')
    sys.exit(1)

holdings = pd.read_csv(holdings_path, dtype=str)
required_cols = {'account', 'ticker', 'name', 'quantity', 'buy_price'}
missing = required_cols - set(holdings.columns)
if missing:
    print(f'Holdings CSV missing columns: {missing}')
    sys.exit(1)

# Convert numeric columns
holdings['quantity'] = holdings['quantity'].astype(int)
holdings['buy_price'] = holdings['buy_price'].astype(float)

# Prepare Yahoo Finance tickers (Korean stocks end with .KS)
holdings['yf_ticker'] = holdings['ticker'].apply(lambda x: f"{x}.KS")

# Download close price for the previous business day for all tickers
try:
    end_str = (prev_day + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    data = yf.download(holdings['yf_ticker'].tolist(), start=date_str, end=end_str, progress=False)
except Exception as e:
    print(f'Error fetching data from yfinance: {e}')
    sys.exit(1)

if data.empty:
    print(f'No market data for {date_str} (holiday/weekend). Skipping.')
    sys.exit(0)

# Extract close prices (handle single or multiple ticker response)
if isinstance(data.columns, pd.MultiIndex):
    close_prices = data['Close'].iloc[0]
else:
    close_prices = data['Close']

price_df = close_prices.reset_index()
price_df.columns = ['yf_ticker', 'close_price']

# Merge holdings with price data
merged = holdings.merge(price_df, on='yf_ticker', how='left')
# Compute valuation, profit, profit_rate
merged['valuation'] = merged['close_price'] * merged['quantity']
merged['profit'] = (merged['close_price'] - merged['buy_price']) * merged['quantity']
merged['profit_rate'] = ((merged['close_price'] - merged['buy_price']) / merged['buy_price']) * 100
merged['date'] = prev_day

# Column order for CSV / HTML (ticker at the end)
merged['ticker'] = holdings['ticker']
cols_order = ['account', 'name', 'quantity', 'buy_price', 'close_price', 'valuation', 'profit', 'profit_rate', 'ticker']
merged = merged[cols_order]

# Write CSV report
report_path = os.path.join(os.path.dirname(__file__), f"daily_report_{prev_day.strftime('%Y%m%d')}.csv")
merged.to_csv(report_path, index=False)
print(f'Report written to {report_path}')

# Build HTML report (no ticker column, includes valuation, profit, profit_rate)
html_parts = []
html_parts.append('<!DOCTYPE html>')
html_parts.append('<html lang="ko">')
html_parts.append('<head>')
html_parts.append('<meta charset="UTF-8">')
html_parts.append('<title>포트폴리오 보유 현황 리포트</title>')
html_parts.append(f"<p style='text-align:center;color:#555;'>Last updated: {prev_day.strftime('%Y-%m-%d')}</p>")
html_parts.append('<style>')
html_parts.append('  body {font-family: Arial, Helvetica, sans-serif; background:#f9f9f9; padding:20px;}')
html_parts.append('  h1 {text-align:center; color:#333;}')
html_parts.append('  table {border-collapse:collapse; width:100%; margin:auto; background:#fff; box-shadow:0 2px 5px rgba(0,0,0,0.1);}')
html_parts.append('  th, td {border:1px solid #ddd; padding:8px; text-align:center;}')
html_parts.append('  th {background:#4a90e2; color:#fff; font-weight:bold;}')
html_parts.append('  tr:nth-child(even) {background:#f2f2f2;}')
html_parts.append('  tr:hover {background:#e1f5fe;}')
html_parts.append('  .positive {color:#c0392b; font-weight:bold;}')
html_parts.append('  .negative {color:#27ae60; font-weight:bold;}')
html_parts.append('</style>')
html_parts.append('</head>')
html_parts.append('<body>')
html_parts.append('<h1>포트폴리오 보유 현황 리포트</h1>')
html_parts.append('<table>')
# Header row
html_parts.append('<thead><tr>')
for col in merged.columns:
    header = col
    if col == 'account':
        header = '계좌'
    elif col == 'name':
        header = '종목명'
    elif col == 'quantity':
        header = '보유수량'
    elif col == 'buy_price':
        header = '매입가(원)'
    elif col == 'close_price':
        header = '어제종가(원)'
    elif col == 'valuation':
        header = '평가금액(원)'
    elif col == 'profit':
        header = '수익(원)'
    elif col == 'profit_rate':
        header = '수익률(%)'
    elif col == 'date':
        header = '날짜'
    elif col == 'ticker':
        header = '티커'
    html_parts.append(f'<th>{header}</th>')
html_parts.append('</tr></thead>')
# Body rows
html_parts.append('<tbody>')
for _, row in merged.iterrows():
    html_parts.append('<tr>')
    for col, val in zip(merged.columns, row):
        if isinstance(val, (int, float)):
            if col == 'profit_rate':
                cell = f"{val:,.2f}%"
            else:
                cell = f"{val:,.0f}"
        else:
            cell = str(val)
        if col in ['profit', 'profit_rate']:
            cls = 'positive' if float(val) >= 0 else 'negative'
            cell = f"<span class='{cls}'>{cell}</span>"
        html_parts.append(f'<td>{cell}</td>')
    html_parts.append('</tr>')
html_parts.append('</tbody>')
html_parts.append('</table>')
html_parts.append('</body>')
html_parts.append('</html>')
new_html = "\n".join(html_parts)
index_path = os.path.join(os.path.dirname(__file__), 'index.html')
with open(index_path, 'w', encoding='utf-8') as f:
    f.write(new_html)
print('index.html regenerated')

# Git commit & push
repo_dir = os.path.dirname(__file__)
os.chdir(repo_dir)
os.system('git add .')
os.system(f"git commit -m 'Update prices for {prev_day}'")
os.system('git push origin main')
