#!/usr/bin/env python3
import sys, os, logging

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(name)s [%(levelname)s] %(message)s'
)

# Clear seen cache
seen_file = 'data/tg_seen_messages.json'
if os.path.exists(seen_file):
    os.remove(seen_file)
    print("[DEBUG] Removed seen file")

from tg_scraper import scrape_channel, load_seen_messages
from database import save_news

seen = load_seen_messages()
print(f"[DEBUG] Seen count: {len(seen)}")
print(f"[DEBUG] Starting scrape...")

try:
    count = scrape_channel('https://t.me/s/Financial_Express', seen, save_news)
    print(f"[RESULT] New messages: {count}")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[ERROR] {e}")

# Check database
import sqlite3
conn = sqlite3.connect('data/finance_data.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM finance_news')
total = c.fetchone()[0]
print(f"[DB] Total news: {total}")
if total > 0:
    c.execute('SELECT id, title, source FROM finance_news LIMIT 3')
    for row in c.fetchall():
        print(f"  - {row}")
conn.close()