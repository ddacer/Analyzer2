import os
os.environ["PYTHAINLP_DATA_DIR"] = "/tmp/pythainlp-data"

from googleapiclient.discovery import build
import re
import json
import requests
from dotenv import load_dotenv

def safe_word_tokenize(text, engine="newmm"):
    try:
        from pythainlp import word_tokenize
        return word_tokenize(text, engine=engine)
    except Exception:
        return text.split()

def _call_groq(prompt, system_msg, json_mode):
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
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
    return None

def _call_deepseek(prompt, system_msg, json_mode, ai_api_key=""):
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
            
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
    return None

def _call_openrouter(prompt, system_msg, json_mode):
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
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
    return None

def _call_gemini(prompt, system_msg, json_mode):
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key and gemini_key.startswith("AIzaSy"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": system_msg + "\n\n" + prompt}]}]
        }
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text.strip()
    return None


def call_ai_api(prompt, ai_api_key="", json_mode=False, model_provider="auto"):
    """ระบบเรียกใช้ AI อัจฉริยะ รองรับ Groq, DeepSeek, Gemini, OpenRouter พร้อมระบุโมเดลเฉพาะเจาะจงและ Fallback อัตโนมัติ"""
    load_dotenv(override=True)

    system_msg = (
        "คุณคือ Senior Social Media Data Analyst และ Expert Behavioral Psychologist "
        "ผู้เชี่ยวชาญระดับสูงในการวิเคราะห์พฤติกรรมผู้ชม เสียงของมนุษย์ (Voice of Audience/Customer) "
        "และกระแสตอบรับบนโซเชียลมีเดียภาษาไทย\n"
        "หน้าที่ของคุณคือวิเคราะห์ความหมายแฝง นัยยะทางอารมณ์ บริบทโซเชียล (Context & Subtext) "
        "ศัพท์แสลง มุกตลก คำประชดประชัน (Sarcasm/Irony) ภาษาเกมเมอร์ ภาษาอินเทอร์เน็ต และมีมภาษาไทย\n"
        "วิเคราะห์อย่างเที่ยงตรง ลึกซึ้ง แม่นยำ ไม่เจือปนอคติ และห้ามสรุปแบบหว่านค่ายกว้างๆ "
        "อ้างอิงหลักฐานจากคอมเมนต์จริงเสมอ"
    )
    if json_mode:
        system_msg += " ในรูปแบบ JSON เท่านั้น"

    provider = str(model_provider).strip().lower()

    # 1. หากผู้ใช้เลือกโมเดลเฉพาะเจาะจง ให้พยายามใช้โมเดลนั้นเป็นอันดับแรก
    if provider == "groq":
        try:
            res = _call_groq(prompt, system_msg, json_mode)
            if res: return res
        except Exception: pass
    elif provider == "deepseek":
        try:
            res = _call_deepseek(prompt, system_msg, json_mode, ai_api_key)
            if res: return res
        except Exception: pass
    elif provider == "gemini":
        try:
            res = _call_gemini(prompt, system_msg, json_mode)
            if res: return res
        except Exception: pass

    # 2. หากผู้ใช้เลือก auto หรือโมเดลที่เลือกใช้งานไม่ได้ ให้ใช้ Auto Fallback ตามลำดับ
    fallback_funcs = [
        _call_groq, 
        lambda p, s, j: _call_deepseek(p, s, j, ai_api_key), 
        _call_openrouter, 
        _call_gemini
    ]
    for fn in fallback_funcs:
        try:
            res = fn(prompt, system_msg, json_mode)
            if res:
                return res
        except Exception:
            continue

    raise Exception(
        "ไม่สามารถเชื่อมต่อกับ AI ได้ กรุณาตรวจสอบ API Key ในไฟล์ .env (GROQ_API_KEY / DEEPSEEK_API_KEY / GEMINI_API_KEY)"
    )


def get_ai_summary(comments, api_key_deepseek="", channel_name="YouTube", video_title="", model_provider="auto"):
    try:
        # คัดเลือกลำดับคอมเมนต์สูงสุด 120 คอมเมนต์ และจัดรูปแบบให้อ่านง่าย
        sampled_comments = comments[:120] if comments else []
        formatted_comments = "\n".join([f"- {c.strip()}" for c in sampled_comments if c.strip()])
        
        video_context_str = f"ชื่อคลิป: '{video_title}'\nช่อง: '{channel_name}'" if video_title else f"ช่อง: '{channel_name}'"
        
        prompt = f"""
คุณคือนักวิเคราะห์พฤติกรรมผู้ชมและสรุป Insight จากความคิดเห็นบนโซเชียลมีเดียภาษาไทยที่มีความแม่นยำระดับสูงสุด

บริบทวิดีโอที่กำลังวิเคราะห์:
{video_context_str}

คำแนะนำเฉพาะสำหรับการวิเคราะห์บริบทภาษาไทยและโซเชียลมีเดีย:
1. เข้าใจภาษาไทยยุคปัจจุบัน ศัพท์วงการเกม สแลงอินเทอร์เน็ต มุกตลก มีมยอดฮิต และภาษาพูดอย่างลึกซึ้ง
2. **การตรวจจับคำประชด (Sarcasm / Irony / Satire Detection)**:
   - คำอย่างเช่น 'ตึงจัด', 'สภาพ', 'เอาเรื่อง', 'เจริญ', 'เล่นดีมากมั้ง', 'เก่งเหลือเกิน', 'ตื่นกี่โมง', 'เทพซ่า', 'โบ๊ะบ๊ะ' 
   - หากสังเกตเห็นว่าผู้ชมใช้ในบริบทล้อเลียน แซวความผิดพลาด แซวความตลก หรือประชดประชัน **ห้ามจัดเป็นคำชม (Positive) เด็ดขาด** ให้จัดไว้ในหมวดการแซว/ประชดประชัน (`sarcasm`) เท่านั้น
3. **ความแม่นยำของหัวข้อ (Specific & Actionable Topics)**:
   - ห้ามใช้หัวข้อทั่วไปแบบลอยๆ เช่น 'ชอบคลิป', 'สนุกดี', 'ไม่ชอบ', 'คนด่า'
   - หัวข้อ (`topic`) ต้องระบุชัดเจนว่าชื่นชอบหรือติชมประเด็นใด เช่น 'ชื่นชอบจังหวะการตัดต่อและมุกตลกในนาทีแรก', 'วิพากษ์วิจารณ์เรื่องระดับเสียงไมค์และดนตรีประกอบที่ดังเกินไป'
4. **รายละเอียดและการอ้างอิง (`details`)**:
   - อธิบายเหตุผลเบื้องหลังความคิดเห็นของผู้ชมอย่างกระชับแต่ได้ใจความ
   - ต้องยกตัวอย่างคำพูดจริงจากคอมเมนต์สั้นๆ มาประกอบในรายละเอียดด้วยเสมอ เช่น `(อ้างอิงคอมเมนต์: '...')`
5. **การรวมประเด็น (Clustering)**:
   - รวมคอมเมนต์ที่มีความหมายหรือพูดถึงเรื่องเดียวกันไว้ในหัวข้อเดียว ห้ามสร้างหัวข้อซ้ำ
   - คัดเลือกรวบรวมเฉพาะประเด็นหลักที่คนพูดถึงบ่อยที่สุด หมวดละไม่เกิน 3 - 4 หัวข้อ

กฎเหล็กรูปแบบ JSON:
- ตอบกลับเฉพาะโครงสร้าง JSON ที่ถูกต้องสมบูรณ์เท่านั้น ห้ามใส่คำเกริ่นหรือข้อความ markdown นอกเหนือจาก JSON
- ในข้อความ JSON ห้ามใช้เครื่องหมายคำพูดคู่ซ้อนข้างใน ให้ใช้เครื่องหมายคำพูดเดี่ยว (') สำหรับการอ้างอิงคำพูด

รูปแบบ JSON ที่ต้องการเป๊ะๆ:
{{
  "positive": [
    {{"topic": "สรุปประเด็นที่คนชม/ชอบอย่างเจาะจง (ภาษาไทย)", "details": "อธิบายรายละเอียดว่าทำไมคนถึงชอบ พร้อมยกตัวอย่างคอมเมนต์สั้นๆ (อ้างอิง: '...') "}}
  ],
  "negative": [
    {{"topic": "สรุปปัญหา/ข้อติชม/ดราม่าอย่างเจาะจง (ภาษาไทย)", "details": "อธิบายรายละเอียดปัญหาและข้อติชม พร้อมยกตัวอย่างคอมเมนต์สั้นๆ (อ้างอิง: '...') "}}
  ],
  "sarcasm": [
    {{"topic": "สรุปประเด็นการแซว/ประชดประชัน/Irony อย่างเจาะจง (ภาษาไทย)", "details": "อธิบายบริบทการแซวหรือประชด พร้อมยกตัวอย่างคอมเมนต์สั้นๆ (อ้างอิง: '...') "}}
  ],
  "recommendation": [
    {{"topic": "สรุปข้อเสนอแนะ/สิ่งที่คนดูอยากเห็นเพิ่มอย่างเจาะจง (ภาษาไทย)", "details": "อธิบายรายละเอียดสิ่งที่ผู้ชมเรียกร้อง พร้อมยกตัวอย่างคอมเมนต์สั้นๆ (อ้างอิง: '...') "}}
  ]
}}

รายการคอมเมนต์ของผู้ชมที่ต้องนำมาวิเคราะห์:
{formatted_comments}
"""
        
        json_str = call_ai_api(prompt, api_key_deepseek, json_mode=True, model_provider=model_provider)
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            clean_text = match.group(0)
        else:
            clean_text = json_str.replace('```json', '').replace('```', '').strip()
            
        return json.loads(clean_text)
        
    except Exception as e:
        return {"error": str(e)}


def get_highlight_summary(highlight_comments, api_key_deepseek="", channel_name="YouTube", video_title="", peak_label="", model_provider="auto"):
    """ให้ AI สรุปเหตุการณ์จากคอมเมนต์ในช่วงเวลาจุดพีค (รองรับทุกประเภทคลิปวิดีโอ)"""
    if not highlight_comments:
        return "ไม่มีข้อมูลคอมเมนต์เพียงพอในการวิเคราะห์"
    try:
        context = "\n".join([f"- {c.strip()}" for c in highlight_comments[:35] if c.strip()])
        
        video_info_str = f"คลิป '{video_title}' " if video_title else ""
        time_info_str = f"ณ นาทีที่ {peak_label} " if peak_label else ""
        
        prompt = f"""
คุณคือนักวิเคราะห์เหตุการณ์และคอนเทนต์วิดีโอระดับมืออาชีพ
จงอ่านความคิดเห็นของผู้ชม{time_info_str}จาก{video_info_str}ช่อง {channel_name} ต่อไปนี้:

ความคิดเห็นของผู้ชม:
{context}

ภารกิจ:
วิเคราะห์และสรุปอย่างเจาะจงว่าเกิดเหตุการณ์ ไฮไลท์ มุกตลก ความผิดพลาด หรือช็อตเด็ดอะไรขึ้น ณ ช่วงเวลานี้
ทำไมผู้ชมจึงแสดงปฏิกิริยาหรือพิมพ์ข้อความหลั่งไหลเข้ามาจำนวนมาก

ข้อกำหนดการตอบ:
- เขียนบทสรุปเชิงวิเคราะห์ที่กระชับ แม่นยำ ตรงประเด็น ความยาว 1-2 ประโยค เป็นภาษาไทยที่เป็นธรรมชาติ
- ไม่ต้องใส่คำเกริ่น ไม่ต้องตอบเป็น JSON และไม่ต้องใส่ป้ายกำกับใดๆ
"""
        result = call_ai_api(prompt, api_key_deepseek, json_mode=False, model_provider=model_provider)
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        return result.strip()
    except Exception as e:
        return f"Error: {str(e)}"


def get_ai_comparison(summary_a, summary_b, title_a, title_b, channel_a, channel_b, api_key_deepseek="", model_provider="auto"):
    """ให้ AI สรุปเปรียบเทียบผลตอบรับของทั้ง 2 คลิปแบบหมัดต่อหมัด"""
    try:
        prompt = f"""
คุณคือ Senior Content Strategist และ Media Behavioral Analyst

จงวิเคราะห์และเปรียบเทียบผลตอบรับของผู้ชมระหว่างวิดีโอ 2 คลิปอย่างละเอียดและเป็นมืออาชีพ:

[คลิป A]
ชื่อคลิป: {title_a}
ช่อง: {channel_a}
ผลสรุปความคิดเห็นคลิป A:
{json.dumps(summary_a, ensure_ascii=False) if isinstance(summary_a, dict) else summary_a}

[คลิป B]
ชื่อคลิป: {title_b}
ช่อง: {channel_b}
ผลสรุปความคิดเห็นคลิป B:
{json.dumps(summary_b, ensure_ascii=False) if isinstance(summary_b, dict) else summary_b}

ภารกิจของคุณ:
เปรียบเทียบกระแสตอบรับ จุดแข็ง จุดที่ผู้ชมชื่นชอบ และประเด็นดราม่า/ข้อติชมของทั้งสองคลิปแบบหมัดต่อหมัด
แล้วเขียนบทสรุปภาพรวมผู้บริหาร (Executive Conclusion) ที่กระชับ ได้ใจความ (ไม่เกิน 3-4 บรรทัด) โดยครอบคลุม:
1. คลิปไหนมีกระแสตอบรับเชิงบวกและสร้าง Engagement ได้ดีกว่ากัน พร้อมเหตุผลหลัก
2. ความแตกต่างสำคัญของอารมณ์ผู้ชมที่มีต่อทั้งสองคลิป
3. ข้อเสนอแนะเชิงกลยุทธ์ (Key Takeaway) ที่ผู้สร้างคอนเทนต์ควรนำไปปรับใช้

ข้อกำหนด:
- ตอบเป็นภาษาไทยด้วยภาษาที่กระชับ อ่านง่าย ตรงประเด็น และเฉียบคม
"""
        return call_ai_api(prompt, api_key_deepseek, json_mode=False, model_provider=model_provider)
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
            
        tokens = safe_word_tokenize(comment, engine="newmm")
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