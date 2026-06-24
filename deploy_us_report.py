#!/usr/bin/env python3
import subprocess, sys, os
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.chdir(BASE_DIR)

# 1. Generate the US daily report
print("Running generate_daily_report_us_final.py...")
proc = subprocess.run(["python3", "generate_daily_report_us_final.py"], capture_output=True, text=True)
print(proc.stdout)
if proc.returncode != 0:
    sys.exit(f"Error generating report: {proc.stderr}")

# 2. Add the generated status.html to git
print("Adding status.html to git...")
subprocess.run(["git", "add", "-A"], check=True)

# 3. Commit with a timestamped message
commit_msg = f"Update US daily report {datetime.now().strftime('%Y-%m-%d')}"
print(f"Committing: {commit_msg}")
subprocess.run(["git", "commit", "-m", commit_msg], check=True)

# 4. Push to the remote (GitHub Pages)
print("Pushing to GitHub...")
subprocess.run(["git", "push"], check=True)

print("Deployment completed successfully.")
