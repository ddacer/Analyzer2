import os
import shutil
import sqlite3
import json
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DB = os.path.join(BASE_DIR, 'hrk_insight.db')

if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    TMP_DB = "/tmp/hrk_insight.db"
    if not os.path.exists(TMP_DB) and os.path.exists(LOCAL_DB):
        try:
            shutil.copyfile(LOCAL_DB, TMP_DB)
        except Exception:
            pass
    DB_NAME = TMP_DB
else:
    DB_NAME = LOCAL_DB

def is_supabase_enabled():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))).strip()
    return bool(url and key)

def get_supabase_headers():
    key = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))).strip()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def get_supabase_url():
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")

def init_db():
    """สร้างไฟล์ฐานข้อมูลและตารางเก็บข้อมูล (สำหรับ SQLite)"""
    if is_supabase_enabled():
        return

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_url TEXT,
                total_comments INTEGER,
                positive_pct REAL,
                negative_pct REAL,
                neutral_pct REAL,
                peak_timestamp TEXT,
                ai_summary TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            c.execute("ALTER TABLE analysis_history ADD COLUMN video_title TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            c.execute("ALTER TABLE analysis_history ADD COLUMN channel_name TEXT")
        except sqlite3.OperationalError:
            pass
            
        conn.commit()

def save_to_db(url, total, pos, neg, neu, peak_time, ai_data, title, channel_name):
    """บันทึกผลการวิเคราะห์ลงฐานข้อมูล (รองรับทั้ง Supabase และ SQLite)"""
    total_sentiment = pos + neg + neu
    pos_pct = (pos / total_sentiment) * 100 if total_sentiment > 0 else 0
    neg_pct = (neg / total_sentiment) * 100 if total_sentiment > 0 else 0
    neu_pct = (neu / total_sentiment) * 100 if total_sentiment > 0 else 0
    ai_json_str = json.dumps(ai_data, ensure_ascii=False)

    if is_supabase_enabled():
        endpoint = f"{get_supabase_url()}/rest/v1/analysis_history"
        payload = {
            "video_url": url,
            "total_comments": total,
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
            "neutral_pct": neu_pct,
            "peak_timestamp": peak_time,
            "ai_summary": ai_json_str,
            "video_title": title,
            "channel_name": channel_name
        }
        res = requests.post(endpoint, json=payload, headers=get_supabase_headers(), timeout=15)
        if res.status_code not in (200, 201):
            raise Exception(f"Supabase save error ({res.status_code}): {res.text}")
        return

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO analysis_history 
            (video_url, total_comments, positive_pct, negative_pct, neutral_pct, peak_timestamp, ai_summary, video_title, channel_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (url, total, pos_pct, neg_pct, neu_pct, peak_time, ai_json_str, title, channel_name))
        conn.commit()

def load_history():
    """ดึงข้อมูลประวัติทั้งหมดมาแสดงผล"""
    if is_supabase_enabled():
        endpoint = f"{get_supabase_url()}/rest/v1/analysis_history?select=*&order=analyzed_at.desc"
        res = requests.get(endpoint, headers=get_supabase_headers(), timeout=15)
        if res.status_code == 200:
            return res.json()
        raise Exception(f"Supabase load error ({res.status_code}): {res.text}")

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM analysis_history ORDER BY analyzed_at DESC")
        rows = [dict(r) for r in c.fetchall()]
    return rows

def update_title(record_id, new_title):
    """อัปเดตชื่อคลิปใหม่ลงฐานข้อมูล"""
    if is_supabase_enabled():
        endpoint = f"{get_supabase_url()}/rest/v1/analysis_history?id=eq.{record_id}"
        payload = {"video_title": new_title}
        res = requests.patch(endpoint, json=payload, headers=get_supabase_headers(), timeout=15)
        if res.status_code not in (200, 204):
            raise Exception(f"Supabase update error ({res.status_code}): {res.text}")
        return

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("UPDATE analysis_history SET video_title = ? WHERE id = ?", (new_title, record_id))
        conn.commit()

def delete_record(record_id):
    """ลบข้อมูลคลิปออกจากฐานข้อมูล"""
    if is_supabase_enabled():
        endpoint = f"{get_supabase_url()}/rest/v1/analysis_history?id=eq.{record_id}"
        res = requests.delete(endpoint, headers=get_supabase_headers(), timeout=15)
        if res.status_code not in (200, 204):
            raise Exception(f"Supabase delete error ({res.status_code}): {res.text}")
        return

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM analysis_history WHERE id = ?", (record_id,))
        conn.commit()
