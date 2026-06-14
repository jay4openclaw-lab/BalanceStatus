#!/bin/bash
cd /Users/jaykim/BalanceStatus
# Update prices (choose the script you prefer)
python3 update_prices_yf.py
# Stage and commit changes
git add index.html
# Use a timestamped commit message
git commit -m "자동 업데이트: $(date '+%Y-%m-%d %H:%M')"
# Push to remote (assumes credential helper is set)
git push origin main
