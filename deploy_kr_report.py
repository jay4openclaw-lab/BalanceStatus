#!/usr/bin/env python3
import subprocess, sys, os, glob, shutil
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.chdir(BASE_DIR)

# 1. KR 일일 보고서 생성
print("Running generate_daily_report_kr_final.py...")
proc = subprocess.run(["python3", "generate_daily_report_kr_final.py"], capture_output=True, text=True)
print(proc.stdout)
if proc.returncode != 0:
    sys.exit(f"Error generating KR report: {proc.stderr}")

# 2. 생성된 index.html을 git에 추가
print("Adding index.html to git...")
subprocess.run(["git", "add", "index.html"], check=True)

# 3. 타임스탬프를 포함한 커밋 메시지
commit_msg = f"Update KR daily report {datetime.now().strftime('%Y-%m-%d')}"
print(f"Committing: {commit_msg}")
commit_res = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
print(commit_res.stdout)
print(commit_res.stderr)
if commit_res.returncode != 0:
    # Non-zero return can happen when there is nothing to commit; continue anyway.
    print("Git commit returned non-zero, proceeding anyway.")

# 4. 원격 저장소(gh‑pages)로 푸시
print("Pushing to GitHub...")
subprocess.run(["git", "push"], check=True)

# 5. CSV 파일을 report 폴더로 이동
print("Moving CSV report files to 'report/' directory...")
report_dir = os.path.join(BASE_DIR, "report")
os.makedirs(report_dir, exist_ok=True)
# Find generated daily report CSV files (pattern may vary by date)
for csv_path in glob.glob(os.path.join(BASE_DIR, "daily_report_*.csv")):
    dst_path = os.path.join(report_dir, os.path.basename(csv_path))
    if os.path.exists(dst_path):
        os.remove(dst_path)  # overwrite existing report
    shutil.move(csv_path, report_dir)
    print(f"Moved {os.path.basename(csv_path)} to report/")

print("KR deployment completed successfully.")
