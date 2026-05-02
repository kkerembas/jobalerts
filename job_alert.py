"""
DKB Code Factory – Valencia Job Alert
Scrapes the careers page, detects new listings, and sends an email alert.

Setup:
  pip install requests beautifulsoup4

Configuration:
  Set the environment variables below (or hardcode for testing):
    ALERT_FROM_EMAIL   – Gmail address you're sending from
    ALERT_APP_PASSWORD – Gmail App Password (not your regular password)
    ALERT_TO_EMAIL     – Address to receive alerts
"""

import os
import json
import smtplib
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Configuration ─────────────────────────────────────────────────────────────

JOBS_URL = "https://www.dkbcodefactory.com/jobs/valencia"
STATE_FILE = Path("known_jobs.json")  # stores previously seen jobs

# Only alert for jobs whose department contains one of these strings (case-insensitive)
FILTER_KEYWORDS = ["design", "product & design", "ux", "ui"]

FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "you@gmail.com")
APP_PASSWORD = os.getenv("ALERT_APP_PASSWORD", "your-app-password")
TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "you@gmail.com")

# ── Scraper ───────────────────────────────────────────────────────────────────

def fetch_jobs() -> dict[str, str]:
    """Returns {job_title: job_url} for listings matching FILTER_KEYWORDS."""
    resp = requests.get(JOBS_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    jobs = {}
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "greenhouse.io/dkbcodefactory/jobs/" not in href:
            continue

        title = link.get_text(strip=True)
        if not title:
            continue

        # The department sits in the <li> sibling text nodes after the title
        parent = link.find_parent("li")
        department = parent.get_text(" ", strip=True) if parent else ""

        # Filter: keep only jobs matching any keyword
        match = any(kw in department.lower() or kw in title.lower() for kw in FILTER_KEYWORDS)
        if match:
            jobs[title] = href

    return jobs

# ── State management ──────────────────────────────────────────────────────────

def load_known_jobs() -> dict[str, str]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_known_jobs(jobs: dict[str, str]) -> None:
    STATE_FILE.write_text(json.dumps(jobs, indent=2))

# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(new_jobs: dict[str, str]) -> None:
    subject = f"🆕 {len(new_jobs)} new design job(s) at DKB Code Factory Valencia"

    lines = [
        "<h2>New design job listings detected on DKB Code Factory – Valencia</h2>",
        "<ul>",
    ]
    for title, url in new_jobs.items():
        lines.append(f'  <li><a href="{url}">{title}</a></li>')
    lines += [
        "</ul>",
        f'<p><a href="{JOBS_URL}">View all open roles →</a></p>',
    ]
    body = "\n".join(lines)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_EMAIL, APP_PASSWORD)
        server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())

    print(f"✅ Alert sent for {len(new_jobs)} new job(s).")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Checking {JOBS_URL} …")
    current_jobs = fetch_jobs()
    print(f"Found {len(current_jobs)} matching design job(s) live.")

    known_jobs = load_known_jobs()
    new_jobs = {t: u for t, u in current_jobs.items() if t not in known_jobs}

    if new_jobs:
        print(f"🆕 {len(new_jobs)} new job(s): {list(new_jobs.keys())}")
        send_email(new_jobs)
    else:
        print("No new jobs since last check.")

    save_known_jobs(current_jobs)

if __name__ == "__main__":
    main()
