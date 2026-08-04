from googleapiclient.discovery import build
from pythainlp import word_tokenize
import re
import json
import os
import requests
from dotenv import load_dotenv

def call_ai_api(prompt, ai_api_key="", json_mode=False):
    """ระบบเรียกใช้ AI อัจฉริยะ รองรับ Groq (ฟรี ลื่นสุด), DeepSeek, OpenRouter, และ Gemini พร้อม Fallback อัตโนมัติ"""
    load_dotenv(override=True)

    system_msg = "คุณคือ AI ผู้เชี่ยวชาญด้านวิเคราะห์พฤติกรรมผู้ชมโซเชียลมีเดีย สรุปข้อมูลอย่างแม่นยำ กระชับ ตรงประเด็น เป็นภาษาไทย"
    if json_mode:
        system_msg += " ในรูปแบบ JSON เท่านั้น"

    # 1. ลองใช้ Groq API (ฟรี 100% - เสถียรและเร็วที่สุด)
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and groq_key.startswith("gsk_"):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 2. ลองใช้ DeepSeek API
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", ai_api_key)
    if deepseek_key and deepseek_key.startswith("sk-") and not deepseek_key.startswith("sk-or-"):
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {deepseek_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 3. ลองใช้ OpenRouter API (โมเดลฟรี)
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek/deepseek-r1:free",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        if json_mode: payload["response_format"] = {"type": "json_object"}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 4. ลองใช้ Google Gemini API
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key and gemini_key.startswith("AIzaSy"):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if json_mode:
                payload["generationConfig"] = {"responseMimeType": "application/json"}
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
        except Exception:
            pass

    raise Exception(
        "ไม่สามารถเชื่อมต่อกับ AI ได้ กรุณาตรวจสอบ GROQ_API_KEY ในไฟล์ .env"
    )


def get_ai_summary(comments, api_key_deepseek="", channel_name="YouTube"):
    try:
        context = "\n".join(comments[:100]) 
        
        prompt = f"""
        คุณคือผู้เชี่ยวชาญด้านวิเคราะห์พฤติกรรมผู้ชมคลิปวิดีโอช่อง {channel_name} บน YouTube
        เข้าใจภาษาไทย ศัพท์แสลง มุกตลก คำประชด และบริบทโซเชียลเป็นอย่างดี
        จงวิเคราะห์คอมเมนต์ต่อไปนี้ โดยจัดกลุ่มประเด็นที่คล้ายกันเข้าด้วยกัน แล้วสรุปผลภาพรวมในรูปแบบ JSON เท่านั้น ห้ามพิมพ์ข้อความอื่นนอกเหนือจาก JSON
        
        กฎเหล็กที่ 1: ห้ามใช้เครื่องหมายคำพูดคู่ (") ซ้อนไว้ข้างในข้อความ ให้ใช้เครื่องหมายคำพูดเดี่ยว (') แทน
        กฎเหล็กที่ 2: ระวังคำประชดประชัน (Sarcasm) เช่นคำว่า 'ตึงจัด', 'เจริญ', 'สภาพ', 'เอาเรื่อง', 'เล่นดีมากมั้ง' หากอยู่ในบริบทประชด ห้ามจัดเป็นคำชมเด็ดขาด ให้แยกออกมาใส่ในหมวด sarcasm
        กฎเหล็กที่ 3: ห้ามมีหัวข้อ (topic) ซ้ำกัน ให้รวมคอมเมนต์เรื่องเดียวกันสรุปไว้เป็นหัวข้อเดียว
        กฎเหล็กที่ 4: คัดเฉพาะประเด็นหลักที่คนพูดถึงเยอะที่สุด หมวดละไม่เกิน 3 ถึง 4 หัวข้อ
        กฎเหล็กที่ 5: ข้อมูลผลลัพธ์ทั้งหมดใน JSON (ทั้ง topic และ details) ต้องเขียนเป็นภาษาไทยที่เป็นธรรมชาติ อ่านเข้าใจง่าย
        
        รูปแบบ JSON ที่ต้องการเป๊ะๆ:
        {{
          "positive": [
            {{"topic": "สรุปเรื่องที่คนชม/ชอบ (ภาษาไทย)", "details": "อธิบายรายละเอียดว่าทำไมคนถึงชอบ พร้อมยกตัวอย่างคอมเมนต์สั้นๆ (คอมเมนต์: '...') "}}
          ],
          "negative": [
            {{"topic": "สรุปปัญหา/ดราม่า/ข้อติ (ภาษาไทย)", "details": "อธิบายรายละเอียดปัญหา พร้อมยกตัวอย่างคอมเมนต์สั้นๆ (คอมเมนต์: '...') "}}
          ],
          "sarcasm": [
            {{"topic": "สรุปการแซว/ประชดประชัน (ภาษาไทย)", "details": "อธิบายรายละเอียดการแซว พร้อมยกตัวอย่างคอมเมนต์สั้นๆ (คอมเมนต์: '...') "}}
          ],
          "recommendation": [
            {{"topic": "สรุปสิ่งที่คนดูอยากให้ทำเพิ่ม (ภาษาไทย)", "details": "อธิบายรายละเอียดสิ่งที่เรียกร้อง พร้อมยกตัวอย่างคอมเมนต์สั้นๆ (คอมเมนต์: '...') "}}
          ]
        }}
        
        คอมเมนต์ที่ต้องวิเคราะห์:
        {context}
        """
        
        json_str = call_ai_api(prompt, api_key_deepseek, json_mode=True)
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            clean_text = match.group(0)
        else:
            clean_text = json_str.replace('```json', '').replace('```', '').strip()
            
        return json.loads(clean_text)
        
    except Exception as e:
        return {"error": str(e)}


def get_highlight_summary(highlight_comments, api_key_deepseek="", channel_name="YouTube"):
    """ให้ AI สรุปเหตุการณ์จากคอมเมนต์ในช่วงเวลาจุดพีค (รองรับทุกประเภทคลิปวิดีโอ)"""
    if not highlight_comments:
        return "ไม่มีข้อมูลคอมเมนต์เพียงพอ"
    try:
        context = "\n".join(highlight_comments[:30])
        
        prompt = f"""
        คุณคือนักวิเคราะห์คอนเทนต์วิดีโอจากช่อง {channel_name}
        จงอ่านความคิดเห็นของผู้ชมต่อไปนี้ แล้วสรุปว่า ณ ช่วงเวลานี้เกิดเหตุการณ์ ไฮไลท์ หรือประเด็นอะไรขึ้น 
        ทำไมคนดูถึงพูดถึง พิมพ์ประชด หรือแสดงอารมณ์กันเยอะ
        
        ข้อกำหนดการตอบ:
        - เขียนสรุปสั้นๆ 1-2 ประโยค เป็นภาษาไทยอ่านง่าย เป็นธรรมชาติ ไม่ต้องตอบเป็น JSON และไม่ต้องใส่ป้ายกำกับใดๆ
        
        ความคิดเห็นของคนดู:
        {context}
        """
        result = call_ai_api(prompt, api_key_deepseek, json_mode=False)
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        return result.strip()
    except Exception as e:
        return f"Error: {str(e)}"


def get_ai_comparison(summary_a, summary_b, title_a, title_b, channel_a, channel_b, api_key_deepseek=""):
    """ให้ AI สรุปเปรียบเทียบผลตอบรับของทั้ง 2 คลิปแบบหมัดต่อหมัด"""
    try:
        prompt = f"""
        คุณคือนักวิเคราะห์การตลาดและพฤติกรรมผู้ชมบนโซเชียลมีเดีย
        
        นี่คือข้อมูลสรุปคอมเมนต์จากคลิป A:
        ชื่อคลิป: {title_a} (ช่อง: {channel_a})
        เนื้อหาสรุปคลิป A: {summary_a}
        
        นี่คือข้อมูลสรุปคอมเมนต์จากคลิป B:
        ชื่อคลิป: {title_b} (ช่อง: {channel_b})
        เนื้อหาสรุปคลิป B: {summary_b}
        
        จงเปรียบเทียบผลตอบรับของทั้ง 2 คลิปนี้ 
        เขียนบทสรุปภาพรวม (Executive Conclusion) แบบสั้นและกระชับที่สุด (ไม่เกิน 2-3 บรรทัด) โดยสรุปว่า:
        คลิปไหนดึงดูดใจได้ดีกว่ากัน เพราะอะไร และคนทำช่องควรเรียนรู้อะไรจาก 2 คลิปนี้
        
        ตอบเป็นภาษาไทยเท่านั้น ด้วยภาษาที่อ่านง่ายและตรงประเด็น
        """
        return call_ai_api(prompt, api_key_deepseek, json_mode=False)
    except Exception as e:
        return f"Error: {str(e)}"


def analyze_sentiment(comments):
    """วิเคราะห์เจตคติแบบ Rule-based เบื้องต้น (อัปเดตคลังคำศัพท์เกมเมอร์)"""
    pos_words = set(["ดี", "ชอบ", "เยี่ยม", "สุดยอด", "รัก", "ขอบคุณ", "ฮา", "ตลก", "สนุก", "น่ารัก",
                     "มันส์", "เจ๋ง", "ปัง", "โบ๊ะบ๊ะ", "น่าเอ็นดู", "สะใจ", "ฟิน", "ขำ", "คุณภาพ", "ดีย์", 
                     "สุดจัด", "รอด", "เก่ง", "ตึง", "เอาเรื่อง", "โคตรดี"])
    
    neg_words = set(["ไม่ชอบ", "แย่", "ห่วย", "งง", "เบื่อ", "ช้า", "ผิด", "น่ากลัว", "เวียนหัว",
                     "ตาลาย", "ปวดหัว", "รำคาญ", "หัวร้อน", "บัค", "ตาย", "ตกใจ", "ขนลุก", "หนวกหู", 
                     "น่าเกลียด", "ท้อ", "กาก", "สภาพ", "หลอน", "สะดุ้ง"])
                 
    results = {"Positive": 0, "Negative": 0, "Neutral": 0}
    
    for comment in comments:
        pos_score = 0
        neg_score = 0
        
        if "555" in comment or "ฮ่า" in comment or "อิอิ" in comment:
            pos_score += 1
            
        tokens = word_tokenize(comment, engine="newmm")
        pos_score += sum(1 for word in tokens if word in pos_words)
        neg_score += sum(1 for word in tokens if word in neg_words)
        
        if pos_score > neg_score:
            results["Positive"] += 1
        elif neg_score > pos_score:
            results["Negative"] += 1
        else:
            results["Neutral"] += 1
            
    return results

def extract_video_id(url):
    """สกัด Video ID จากลิงก์ YouTube ที่ครอบคลุมรูปแบบต่างๆ (Shorts, youtu.be, etc.)"""
    regex = r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else url


def get_video_info(v_id, key):
    """ดึงข้อมูลวีดีโอ (ชื่อคลิป, ชื่อช่อง, จำนวนคอมเมนต์จริง) จาก YouTube API"""
    try:
        youtube = build('youtube', 'v3', developerKey=key)
        request = youtube.videos().list(part="snippet,statistics", id=v_id)
        response = request.execute()
        
        if response.get('items'):
            item = response['items'][0]
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            comment_count = int(statistics.get('commentCount', 0))
            return snippet.get('title', 'ไม่พบชื่อคลิป'), snippet.get('channelTitle', 'ไม่พบชื่อช่อง'), comment_count
        return "ไม่พบชื่อคลิป", "ไม่พบชื่อช่อง", 0
    except Exception as e:
        return f"ดึงข้อมูลวีดีโอไม่ได้ ({str(e)})", "ไม่พบชื่อช่อง", 0


def get_comments(v_id, key, max_comments=1000):
    """ดึงคอมเมนต์จาก YouTube API"""
    youtube = build('youtube', 'v3', developerKey=key)
    all_comments, next_page_token = [], None
    
    while len(all_comments) < max_comments:
        try:
            request = youtube.commentThreads().list(
                part="snippet", videoId=v_id, maxResults=100, 
                order="relevance", textFormat="plainText", pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response.get('items', []):
                all_comments.append({
                    "text": item['snippet']['topLevelComment']['snippet']['textDisplay'],
                    "likes": int(item['snippet']['topLevelComment']['snippet']['likeCount'])
                })
            next_page_token = response.get('nextPageToken')
            if not next_page_token: break
        except Exception: break
    return sorted(all_comments, key=lambda x: x['likes'], reverse=True)

def extract_timestamps(comments):
    """สกัด Timestamp จากคอมเมนต์"""
    timestamps = []
    for c in comments:
        timestamps.extend(re.findall(r'\b((?:\d{1,2}:)?[0-5]?\d:[0-5]\d)\b', c))
        
    if not timestamps:
        return []
        
    def to_seconds(t_str):
        parts = list(map(int, t_str.split(':')))
        if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
        return parts[0]*60 + parts[1]

    counts = {}
    for ts in timestamps:
        sec = to_seconds(ts)
        key = (ts, sec)
        counts[key] = counts.get(key, 0) + 1

    result = []
    for (ts, sec), count in sorted(counts.items(), key=lambda x: x[0][1]):
        result.append({'Timestamp': ts, 'Seconds': sec, 'Count': count})
    return result


def get_frame_from_youtube(video_url, target_time_sec):
    """ดึงภาพ 1 เฟรมจาก YouTube ด้วย yt-dlp และ OpenCV (ถ้ามี)"""
    try:
        import yt_dlp
        import cv2
        ydl_opts = {'format': 'best[ext=mp4]', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info['url']
            
        cap = cv2.VideoCapture(stream_url)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(target_time_sec * fps))
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return "แคปเจอร์ภาพไม่สำเร็จ"
            
    except Exception as e:
        return f"Error: {str(e)}"