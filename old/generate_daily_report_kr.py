import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PORTFOLIO_CSV = os.path.join(BASE_DIR, 'portfolio_KR.csv')
TEMPLATE_HTML = os.path.join(BASE_DIR, 'index_tpl.html')
OUTPUT_CSV = os.path.join(BASE_DIR, f'daily_report_20260619_kr.csv')
OUTPUT_HTML = os.path.join(BASE_DIR, 'index.html')

# Read portfolio data
cols = ['market', 'account', 'name', 'quantity', 'buy_price', 'Ticker']
portfolio = pd.read_csv(PORTFOLIO_CSV, header=None, names=cols, skiprows=1)

# Function to get previous close price using yfinance
def get_previous_close(ticker):
    yf_ticker = f"{ticker}.KS"
    try:
        data = yf.Ticker(yf_ticker).history(period='2d')
        if data.empty:
            return None
        # Use the most recent close (assumes latest row is yesterday's close)
        return data['Close'][-1]
    except Exception as e:
        print(f"Error fetching {yf_ticker}: {e}")
        return None

# Fetch prices
portfolio['prev_close'] = portfolio['Ticker'].apply(get_previous_close)

# Compute values
portfolio['valuation'] = portfolio['quantity'] * portfolio['prev_close']
portfolio['profit'] = (portfolio['prev_close'] - portfolio['buy_price']) * portfolio['quantity']
portfolio['profit_rate'] = ((portfolio['prev_close'] - portfolio['buy_price']) / portfolio['buy_price']) * 100

# Prepare output DataFrame
out_df = portfolio[['account', 'name', 'quantity', 'buy_price', 'prev_close', 'valuation', 'profit', 'profit_rate']].copy()
out_df.rename(columns={
    'account': '계좌',
    'name': '종목명',
    'quantity': '보유수량',
    'buy_price': '매입가(원)',
    'prev_close': '어제종가(원)',
    'valuation': '평가금액(원)',
    'profit': '수익(원)',
    'profit_rate': '수익률(%)'
}, inplace=True)

# Sort by profit descending
out_df.sort_values(by='수익(원)', ascending=False, inplace=True)

# Save CSV
out_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

# Generate HTML rows
rows_html = []
for _, row in out_df.iterrows():
    profit = row['수익(원)']
    profit_rate = row['수익률(%)']
    profit_class = 'positive' if profit >= 0 else 'negative'
    rows_html.append(
        f"<tr>"
        f"<td>{row['계좌']}</td>"
        f"<td>{row['종목명']}</td>"
        f"<td>{int(row['보유수량'])}</td>"
        f"<td>{int(row['매입가(원)'])}</td>"
        f"<td>{int(row['어제종가(원)']) if not pd.isna(row['어제종가(원)']) else ''}</td>"
        f"<td>{int(row['평가금액(원)']) if not pd.isna(row['평가금액(원)']) else ''}</td>"
        f"<td class=\"{profit_class}\">{int(row['수익(원)']) if not pd.isna(row['수익(원)']) else ''}</td>"
        f"<td class=\"{profit_class}\">{profit_rate:.2f}%" if not pd.isna(profit_rate) else ""
        f"</td></tr>"
    )

# Load template and insert rows
with open(TEMPLATE_HTML, 'r', encoding='utf-8') as f:
    template = f.read()

# Replace Last updated placeholder with today date
today_str = datetime.now().strftime('%Y-%m-%d')
template = template.replace('Last updated: 2026-06-16', f'Last updated: {today_str}')

# Insert rows into <tbody>
import re
new_body = '\n'.join(rows_html)
output_html = re.sub(r'(<tbody>)(.*?)(</tbody>)', f'\1\n{new_body}\n\3', template, flags=re.DOTALL)

# Write final HTML
with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(output_html)

print('Report generated:', OUTPUT_CSV, 'and', OUTPUT_HTML)
