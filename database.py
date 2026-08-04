import os
import shutil
import sqlite3
import json

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

def init_db():
    """สร้างไฟล์ฐานข้อมูลและตารางเก็บข้อมูล"""
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
            pass # ถ้ามีคอลัมน์นี้อยู่แล้ว ระบบจะข้ามไปไม่ Error
            
        try:
            c.execute("ALTER TABLE analysis_history ADD COLUMN channel_name TEXT")
        except sqlite3.OperationalError:
            pass # ถ้ามีคอลัมน์นี้อยู่แล้ว ระบบจะข้ามไปไม่ Error
            
        conn.commit()

def save_to_db(url, total, pos, neg, neu, peak_time, ai_data, title, channel_name):
    """บันทึกผลการวิเคราะห์ลงฐานข้อมูล (อัปเดตรองรับชื่อคลิปจริงและชื่อช่อง)"""
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        
        total_sentiment = pos + neg + neu
        pos_pct = (pos / total_sentiment) * 100 if total_sentiment > 0 else 0
        neg_pct = (neg / total_sentiment) * 100 if total_sentiment > 0 else 0
        neu_pct = (neu / total_sentiment) * 100 if total_sentiment > 0 else 0
        
        ai_json_str = json.dumps(ai_data, ensure_ascii=False)
        
        c.execute('''
            INSERT INTO analysis_history 
            (video_url, total_comments, positive_pct, negative_pct, neutral_pct, peak_timestamp, ai_summary, video_title, channel_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (url, total, pos_pct, neg_pct, neu_pct, peak_time, ai_json_str, title, channel_name))
        
        conn.commit()

def load_history():
    """ดึงข้อมูลประวัติทั้งหมดมาแสดงผล"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM analysis_history ORDER BY analyzed_at DESC")
        rows = [dict(r) for r in c.fetchall()]
    return rows

def update_title(record_id, new_title):
    """อัปเดตชื่อคลิปใหม่ลงฐานข้อมูล"""
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("UPDATE analysis_history SET video_title = ? WHERE id = ?", (new_title, record_id))
        conn.commit()

def delete_record(record_id):
    """ลบข้อมูลคลิปออกจากฐานข้อมูล"""
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM analysis_history WHERE id = ?", (record_id,))
        conn.commit()
