import os
import sys
from dotenv import load_dotenv
load_dotenv()

import json
import base64
import io
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from wordcloud import WordCloud
from pythainlp import word_tokenize

# Add root to sys.path so we can import from backend.py and database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (
    get_ai_summary, analyze_sentiment, extract_video_id,
    get_comments, extract_timestamps, get_frame_from_youtube,
    get_highlight_summary, get_video_info, get_ai_comparison
)
from database import init_db, save_to_db, load_history, update_title, delete_record

app = FastAPI(title="YouTube AI Insight Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
init_db()

class AnalyzeRequest(BaseModel):
    video_url: str

class TitleUpdateRequest(BaseModel):
    new_title: str

class CompareRequest(BaseModel):
    id_a: int
    id_b: int

@app.post("/api/analyze")
def api_analyze(req: AnalyzeRequest):
    video_url = req.video_url
    if not video_url:
        raise HTTPException(status_code=400, detail="Missing video URL")

    yt_api_key = os.getenv("YOUTUBE_API_KEY", "")
    ai_api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("GEMINI_API_KEY", ""))

    v_id = extract_video_id(video_url)
    real_video_title, channel_name, actual_comment_count = get_video_info(v_id, yt_api_key)
    raw_comments_data = get_comments(v_id, yt_api_key)

    if not raw_comments_data:
        raise HTTPException(status_code=404, detail="No comments found or API error")

    comments = [c["text"] for c in raw_comments_data]
    sentiment_counts = analyze_sentiment(comments)
    ai_data = get_ai_summary(comments, ai_api_key, channel_name)
    timestamp_data = extract_timestamps(comments)
    
    peak_label = "-"
    peak_sec = 0
    heatmap_list = []
    peak_comments = []
    if timestamp_data:
        peak_row = max(timestamp_data, key=lambda x: x['Count'])
        peak_label = peak_row['Timestamp']
        peak_sec = int(peak_row['Seconds'])
        for r in timestamp_data:
            heatmap_list.append({"label": str(r['Timestamp']), "count": int(r['Count'])})
        if peak_label != "-":
            peak_comments = [c for c in comments if peak_label in c]

    all_ts_comments = [c for c in comments if re.search(r'\b((?:\d{1,2}:)?[0-5]?\d:[0-5]\d)\b', c)]

    top_likes = raw_comments_data[0]['likes'] if raw_comments_data else 0
    top_sentiment = max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else "Neutral"

    save_to_db(
        video_url, 
        actual_comment_count, 
        sentiment_counts["Positive"], 
        sentiment_counts["Negative"], 
        sentiment_counts["Neutral"],
        peak_label,
        ai_data,
        real_video_title,
        channel_name
    )

    # Word Cloud
    channel_tokens = word_tokenize(channel_name.lower(), engine="newmm")
    junk_words = ["ๆ", "คลิป", "ดู", "พี่", "ผม", "คน", "แชนเนล", "ช่อง", "นะ", "ที่", "ครับ", "ค่ะ", "ว่า"]
    junk_words.extend(channel_tokens)
    
    tokens = word_tokenize(" ".join(comments).lower(), engine="newmm")
    filtered_words = [w for w in tokens if len(w) > 2 and w not in junk_words and not w.isnumeric()]
    processed_text = " ".join(filtered_words)
    
    wordcloud_b64 = ""
    try:
        font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'THSarabunNew Bold.ttf')
        wc_kwargs = {
            "width": 800,
            "height": 500,
            "background_color": "white",
            "regexp": r"[\u0E00-\u0E7F]+"
        }
        if os.path.exists(font_path):
            wc_kwargs["font_path"] = font_path

        wordcloud = WordCloud(**wc_kwargs).generate(processed_text)
        img = wordcloud.to_image()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        wordcloud_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        print("WordCloud error:", e)
        
    highlight_summary = ""
    if peak_sec > 0:
        if peak_comments:
            highlight_summary = get_highlight_summary(peak_comments, ai_api_key, channel_name)
            if isinstance(highlight_summary, dict) and "error" in highlight_summary:
                highlight_summary = highlight_summary["error"]
                
    # Vision Frame (Base64)
    frame_b64 = ""
    try:
        frame_rgb = get_frame_from_youtube(video_url, peak_sec)
        if frame_rgb and not isinstance(frame_rgb, str):
            import cv2
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', frame_bgr)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        print("Frame capture error:", e)

    return {
        "video_info": {
            "title": real_video_title,
            "channel": channel_name,
            "comment_count": actual_comment_count,
            "thumbnail": f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
            "top_likes": top_likes,
            "top_sentiment": top_sentiment
        },
        "sentiment": sentiment_counts,
        "ai_summary": ai_data,
        "peak_label": peak_label,
        "wordcloud_base64": wordcloud_b64,
        "frame_base64": frame_b64,
        "highlight_summary": highlight_summary,
        "timestamp_heatmap": heatmap_list,
        "peak_comments": peak_comments,
        "all_ts_comments": all_ts_comments,
        "comments_table": raw_comments_data
    }

@app.get("/api/history")
def api_history():
    records = load_history()
    return records

@app.put("/api/history/{record_id}")
def api_update_title(record_id: int, req: TitleUpdateRequest):
    update_title(record_id, req.new_title)
    return {"success": True}

@app.delete("/api/history/{record_id}")
def api_delete_record(record_id: int):
    delete_record(record_id)
    return {"success": True}

@app.post("/api/compare")
def api_compare(req: CompareRequest):
    records = load_history()
    list_a = [r for r in records if r.get('id') == req.id_a]
    list_b = [r for r in records if r.get('id') == req.id_b]
    
    if not list_a or not list_b:
        raise HTTPException(status_code=400, detail="Record not found")
        
    data_a = list_a[0]
    data_b = list_b[0]
    
    ai_api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    
    ai_conclusion = get_ai_comparison(
        data_a.get('ai_summary', ''), data_b.get('ai_summary', ''), 
        data_a.get('video_title', ''), data_b.get('video_title', ''), 
        data_a.get('channel_name', ''), data_b.get('channel_name', ''), 
        ai_api_key
    )
    
    return {
        "data_a": data_a,
        "data_b": data_b,
        "ai_conclusion": ai_conclusion
    }

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
public_dir = os.path.join(root_dir, "public")
if os.path.isdir(public_dir):
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
