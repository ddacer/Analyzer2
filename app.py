import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import json
import re
from pythainlp import word_tokenize
import os
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
import plotly.express as px

# โหลดค่าจากไฟล์ .env
load_dotenv()

# --- 1. นำเข้าฟังก์ชันจากไฟล์ backend.py และ database.py ---
from backend import (
    get_ai_summary, analyze_sentiment, extract_video_id,
    get_comments, extract_timestamps, get_frame_from_youtube,
    get_highlight_summary, get_video_info, get_ai_comparison 
)
from database import init_db, save_to_db, load_history, update_title, delete_record

# --- 2. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="YouTube AI Insight Analyzer", layout="wide", page_icon="📺")

# เรียกใช้ฟังก์ชันสร้าง DB ทันทีที่เปิดเว็บ
init_db()

# --- 3. Custom CSS เพื่อความสวยงาม ---
st.markdown("""
    <style>
    /* ปรับแต่งปุ่มให้ดูพรีเมียม */
    .stButton>button {
        border-radius: 8px;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #ff3333;
        border-color: #ff3333;
        transform: translateY(-2px);
    }
    /* ปรับแต่งกรอบ Expander */
    .streamlit-expanderHeader {
        font-size: 16px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ส่วนเมนูนำทาง (Sidebar)
# ==========================================
st.sidebar.title("📌 เมนูระบบ")
page = st.sidebar.radio("เลือกหน้าจอการทำงาน:", ["🔍 วิเคราะห์คลิปใหม่", "🗄️ คลังข้อมูลประวัติ", "📊 เปรียบเทียบข้อมูล"])
st.sidebar.divider()

st.sidebar.subheader("🤖 เลือกโมเดล AI ในการวิเคราะห์")
model_choice = st.sidebar.selectbox(
    "โมเดล AI:",
    [
        "🤖 Auto (เลือกอัตโนมัติ/เสถียรสุด)",
        "⚡ Groq (Llama-3.3 70B)",
        "🧠 DeepSeek (DeepSeek-Chat)",
        "✨ Google Gemini (Gemini 1.5 Flash)"
    ],
    index=0
)
model_provider_map = {
    "🤖 Auto (เลือกอัตโนมัติ/เสถียรสุด)": "auto",
    "⚡ Groq (Llama-3.3 70B)": "groq",
    "🧠 DeepSeek (DeepSeek-Chat)": "deepseek",
    "✨ Google Gemini (Gemini 1.5 Flash)": "gemini"
}
selected_model_provider = model_provider_map.get(model_choice, "auto")
st.sidebar.divider()

# 🔴 โหลด API Keys จาก Environment Variables เพื่อความปลอดภัย
yt_api_key = os.getenv("YOUTUBE_API_KEY", "")
gemini_api_key = os.getenv("GEMINI_API_KEY", "")

# ==========================================
# 🟢 หน้าที่ 1: หน้าวิเคราะห์ข้อมูล (Analyzer)
# ==========================================
if page == "🔍 วิเคราะห์คลิปใหม่":
    st.title("📺 YouTube AI Insight Analyzer")
    st.markdown("ระบบวิเคราะห์เจตคติ พร้อมบันทึกข้อมูลอัตโนมัติ (รองรับทุกช่อง YouTube)")
    video_url = st.text_input("🔗 วางลิงก์ YouTube ที่นี่")

    if st.button("🚀 เริ่มวิเคราะห์ข้อมูล"):
        if video_url: 
            st.session_state.analyze_url = video_url
            st.session_state.just_analyzed = True

    if st.session_state.get("analyze_url") == video_url and video_url != "":
        with st.spinner('กำลังวิเคราะห์และประมวลผลระดับ Big Data...'):
                v_id = extract_video_id(video_url)
                
                # 🔴 1. ดึงชื่อคลิปและชื่อช่องด้วยฟังก์ชันที่เราเพิ่งสร้าง
                real_video_title, channel_name, actual_comment_count = get_video_info(v_id, yt_api_key)
                
                raw_comments_data = get_comments(v_id, yt_api_key)
                
                if raw_comments_data:
                    st.success(f"📺 กำลังวิเคราะห์คลิป: **{real_video_title}** จากช่อง **{channel_name}**")
                    
                    comments = [c["text"] for c in raw_comments_data]
                    sentiment_counts = analyze_sentiment(comments)
                    
                    # เรียก AI สรุปคอมเมนต์ทั้งหมด โดยส่งชื่อคลิป ชื่อช่อง และโมเดลที่เลือก
                    ai_data = get_ai_summary(comments, gemini_api_key, channel_name, video_title=real_video_title, model_provider=selected_model_provider)
                    
                    # สกัด Timestamp
                    timestamp_df = extract_timestamps(comments)
                    
                    # หา Peak Timestamp
                    peak_label = "-"
                    if not timestamp_df.empty:
                        peak_row = timestamp_df.loc[timestamp_df['Count'].idxmax()]
                        peak_label = peak_row['Timestamp']
                    
                    # 💾 2. บันทึกข้อมูลลง Database อัตโนมัติ (ทำแค่ครั้งเดียวตอนกดปุ่ม)
                    if st.session_state.get("just_analyzed"):
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
                        st.toast('✅ บันทึกข้อมูลลง Database เรียบร้อยแล้ว!', icon='💾')
                        st.session_state.just_analyzed = False
                    
                    # --- ส่วนแสดงผลตัวเลขภาพรวม ---
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("💬 จำนวนคอมเมนต์", f"{actual_comment_count:,}")
                    col_m2.metric("👍 ยอดไลก์สูงสุด", f"{raw_comments_data[0]['likes']:,}")
                    top_sentiment = max(sentiment_counts, key=sentiment_counts.get)
                    col_m3.metric("🎭 อารมณ์ส่วนใหญ่", top_sentiment)
                    
                    st.divider()

                    # --- ส่วนแสดงผล AI Summary ---
                    st.subheader("⚡ AI Executive Summary")
                    if "error" in ai_data:
                        st.error(f"เกิดข้อผิดพลาดในการสรุป: {ai_data['error']}")
                    else:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown("#### 🟢 สิ่งที่คนชอบ")
                            for item in ai_data.get("positive", []):
                                with st.expander(f"✨ {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                    st.write(item.get('details', 'ไม่มีรายละเอียด'))
                        
                        with col_b:
                            st.markdown("#### 🔴 ปัญหา/ดราม่า")
                            for item in ai_data.get("negative", []):
                                with st.expander(f"⚠️ {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                    st.write(item.get('details', 'ไม่มีรายละเอียด'))
                                    
                        st.write("") 
                        col_c, col_d = st.columns(2)
                        with col_c:
                            st.markdown("#### 🎭 แซว/ประชดประชัน (Sarcasm)")
                            sarcasm_data = ai_data.get("sarcasm", [])
                            if sarcasm_data:
                                for item in sarcasm_data:
                                    with st.expander(f"🤡 {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                        st.write(item.get('details', 'ไม่มีรายละเอียด'))
                            else:
                                st.info("ไม่พบการคอมเมนต์ประชดประชัน")

                        with col_d:
                            st.markdown("#### 💡 สิ่งที่คนเรียกร้อง")
                            for item in ai_data.get("recommendation", []):
                                with st.expander(f"📌 {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                    st.write(item.get('details', 'ไม่มีรายละเอียด'))
                    
                    st.divider()
                    
                    # --- ส่วนแสดงผล Heatmap และ Vision AI ---
                    if not timestamp_df.empty:
                        col_heat, col_vision = st.columns(2)
                        
                        with col_heat:
                            st.subheader("⏱️ Timestamp Heatmap")
                            st.markdown("กราฟแสดงช่วงเวลาที่มีการคอมเมนต์ถึงมากที่สุด")
                            chart_data = timestamp_df.set_index('Timestamp')['Count']
                            st.bar_chart(chart_data, color="#ff4b4b", height=300)
                            
                        with col_vision:
                            st.subheader("👁️‍🗨️ Multimodal Vision Analysis")
                            
                            peak_row = timestamp_df.loc[timestamp_df['Count'].idxmax()]
                            peak_sec = int(peak_row['Seconds'])
                            peak_label = peak_row['Timestamp']
                            
                            st.markdown(f"**ช็อตเด็ดที่สุดของคลิป:** นาทีที่ `{peak_label}`")
                            
                            with st.spinner(f"📸 กำลังดึงภาพเฟรมวิดีโอ ณ จุดพีค..."):
                                frame_img = get_frame_from_youtube(video_url, peak_sec)
                                
                                if isinstance(frame_img, str):
                                    st.error(frame_img)
                                else:
                                    # แก้ไขตามคำแนะนำเรื่อง use_column_width
                                    st.image(frame_img, caption=f"ภาพแคปเจอร์ ณ วินาทีที่ {peak_label}", use_container_width=True)
                                    
                                    peak_comments = [c for c in comments if peak_label in c]
                                    if peak_comments:
                                        # 🔴 เรียกใช้ฟังก์ชัน AI สรุปช็อตไฮไลต์ โดยระบุบริบทคลิป เวลาจุดพีค และโมเดลที่เลือก
                                        with st.spinner("🧠 AI กำลังสรุปเหตุการณ์ในช็อตนี้..."):
                                            highlight_summary = get_highlight_summary(peak_comments, gemini_api_key, channel_name, video_title=real_video_title, peak_label=peak_label, model_provider=selected_model_provider)
                                            
                                        st.success(f"🤖 **AI Insight:** {highlight_summary}")
                                        
                                        with st.expander(f"💬 ดูคอมเมนต์ที่พูดถึงนาทีที่ {peak_label} ({len(peak_comments)})"):
                                            for pc in peak_comments:
                                                st.markdown(f"- {pc}")
                            
                            all_ts_comments = [c for c in comments if re.search(r'\b((?:\d{1,2}:)?[0-5]?\d:[0-5]\d)\b', c)]
                            if all_ts_comments:
                                with st.expander(f"⏱️ ดูคอมเมนต์ที่ระบุเวลาทั้งหมด ({len(all_ts_comments)})"):
                                    for tc in all_ts_comments:
                                        st.markdown(f"- {tc}")
                        st.divider()
                    
                    # --- ส่วนแสดงผลสัดส่วนอารมณ์และ Word Cloud ---
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("📊 สัดส่วนอารมณ์")
                        # ใช้ Plotly เพื่อให้กราฟสามารถ Interactive และดูเป็นมืออาชีพขึ้น
                        sentiment_df = pd.DataFrame(list(sentiment_counts.items()), columns=['Sentiment', 'Count'])
                        fig1 = px.pie(sentiment_df, values='Count', names='Sentiment', 
                                      color='Sentiment',
                                      color_discrete_map={'Positive':'#2ecc71', 'Negative':'#e74c3c', 'Neutral':'#95a5a6'},
                                      hole=0.4) # ทำให้เป็น Donut chart สวยๆ
                        fig1.update_traces(textposition='inside', textinfo='percent+label')
                        fig1.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig1, use_container_width=True)

                    with col2:
                        st.subheader("☁️ คำที่พบบ่อย (Word Cloud)")
                        # (ส่วนทำความสะอาด Stopwords เพื่อทำ Word Cloud)
                        # เพิ่มระบบลบชื่อช่องอัตโนมัติ
                        channel_tokens = word_tokenize(channel_name.lower(), engine="newmm")
                        junk_words = ["ๆ", "คลิป", "ดู", "พี่", "ผม", "คน", "แชนเนล", "ช่อง", "นะ", "ที่", "ครับ", "ค่ะ", "ว่า"]
                        junk_words.extend(channel_tokens)
                        
                        tokens = word_tokenize(" ".join(comments).lower(), engine="newmm")
                        filtered_words = [w for w in tokens if len(w) > 2 and w not in junk_words and not w.isnumeric()]
                        processed_text = " ".join(filtered_words)
                        
                        # ใช้ Font ภาษาไทย
                        wordcloud = WordCloud(
                            font_path='THSarabunNew Bold.ttf', width=800, height=500, background_color='white',
                            regexp=r"[\u0E00-\u0E7F]+" 
                        ).generate(processed_text)
                        fig2, ax2 = plt.subplots()
                        ax2.imshow(wordcloud, interpolation='bilinear')
                        ax2.axis("off")
                        st.pyplot(fig2)

                    st.divider()

                    # --- ส่วนแสดงคอมเมนต์ทั้งหมด ---
                    st.subheader("📋 ข้อมูลความคิดเห็นทั้งหมด")
                    df = pd.DataFrame(raw_comments_data)
                    df.columns = ["ความคิดเห็น", "ยอดไลก์"]
                    st.dataframe(df, use_container_width=True, height=300)

    elif not video_url:
        st.warning("กรุณาวางลิงก์ก่อนครับ")

# ==========================================
# 🟠 หน้าที่ 2: หน้าคลังข้อมูลประวัติ (Database History)
# ==========================================
elif page == "🗄️ คลังข้อมูลประวัติ":
    st.title("🗄️ ระบบฐานข้อมูลประวัติการวิเคราะห์")
    st.markdown("จัดการข้อมูล: ดูปกคลิป, แก้ไขชื่อรายการที่วิเคราะห์ และลบทิ้งได้ที่นี่")
    
    history_data = load_history()
    history_df = pd.DataFrame(history_data)
    
    if history_df.empty:
        st.info("ยังไม่มีข้อมูลในระบบ กรุณาไปที่หน้า 'วิเคราะห์คลิปใหม่' เพื่อเพิ่มข้อมูลครับ")
    else:
        st.metric("📊 จำนวนรายงานที่บันทึกไว้", f"{len(history_df)} คลิป")
        st.divider()
        
        # วนลูปสร้างหน้าจอแบบ "การ์ด (Card)" ทีละคลิป
        for index, row in history_df.iterrows():
            
            # ดึง ID ของ YouTube เพื่อเอาปกคลิปมาแสดง
            v_id = extract_video_id(row['video_url'])
            thumbnail_url = f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg"
            
            # ใช้ Container ครอบการ์ดของแต่ละคลิป
            with st.container():
                col_img, col_info, col_action = st.columns([1, 2.5, 1])
                
                with col_img:
                    # โชว์รูปปกคลิป
                    st.image(thumbnail_url, use_container_width=True)
                    
                with col_info:
                    # เช็กว่าเคยตั้งชื่อไว้ไหม ถ้าไม่เคยให้ใช้ค่า Default
                    current_title = row.get('video_title')
                    if pd.isna(current_title) or not current_title:
                        current_title = f"รายการวิเคราะห์ ID: {row['id']}"
                        
                    # เพิ่มการแสดงชื่อช่อง
                    channel_name = row.get('channel_name')
                    if pd.isna(channel_name) or not channel_name:
                        channel_name = "ไม่ทราบช่อง (ข้อมูลเก่า)"
                        
                    # ช่องให้พิมพ์แก้ไขชื่อ
                    new_title = st.text_input("📝 ชื่อข้อมูลวิเคราะห์ (แก้ไขได้):", value=current_title, key=f"title_{row['id']}")
                    st.markdown(f"**📺 ช่อง:** `{channel_name}`")
                    
                    st.caption(f"🔗 {row['video_url']}")
                    st.write(f"💬 คอมเมนต์ทั้งหมด: **{row['total_comments']:,}** | ⏱️ จุดพีค: **{row['peak_timestamp']}**")
                    
                with col_action:
                    st.write("") # เคาะบรรทัดดันปุ่มให้สวยงาม
                    st.write("")
                    
                    # ปุ่มบันทึกชื่อใหม่
                    if st.button("💾 บันทึกชื่อใหม่", key=f"save_{row['id']}", use_container_width=True):
                        update_title(row['id'], new_title)
                        st.rerun() # สั่งให้หน้าเว็บรีเฟรชตัวเองทันที
                        
                    # ปุ่มลบข้อมูล (ใส่ type="primary" ให้ปุ่มเด่นเป็นสีแดง)
                    if st.button("🗑️ ลบข้อมูลนี้", key=f"del_{row['id']}", type="primary", use_container_width=True):
                        delete_record(row['id'])
                        st.rerun()
                        
                st.divider() # เส้นคั่นระหว่างคลิป
        # ==========================================
# 🟣 หน้าที่ 3: หน้าเปรียบเทียบข้อมูล (Comparison Dashboard)
# ==========================================
elif page == "📊 เปรียบเทียบข้อมูล":
    st.title("📊 ระบบเปรียบเทียบเจตคติคลิป (Comparison Dashboard)")
    st.markdown("เปรียบเทียบกระแสตอบรับแบบหมัดต่อหมัด เพื่อหา Insight ว่าคอนเทนต์สไตล์ไหนเข้าถึงผู้ชมได้ดีกว่ากัน")
    
    history_data = load_history()
    history_df = pd.DataFrame(history_data)
    
    if len(history_df) < 2:
        st.warning("⚠️ ต้องมีข้อมูลวิเคราะห์อย่างน้อย 2 คลิปในระบบ เพื่อทำการเปรียบเทียบ กรุณาไปวิเคราะห์คลิปเพิ่มครับ")
    else:
        # สร้างตัวเลือกเป็นข้อความสวยๆ ให้เลือก (ใช้วันที่ + ลิงก์)
        options = history_df['id'].astype(str) + " - " + history_df['video_url']
        
        st.markdown("### 🎯 เลือกคลิปที่ต้องการเปรียบเทียบ")
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            vid_a = st.selectbox("🔴 เลือกคลิปที่ 1 (Video A)", options, index=0)
        with col_opt2:
            vid_b = st.selectbox("🔵 เลือกคลิปที่ 2 (Video B)", options, index=1)
            
        if st.button("⚖️ เริ่มประมวลผลการเปรียบเทียบ"):
            if vid_a == vid_b:
                st.error("กรุณาเลือกคลิปที่ไม่ซ้ำกันครับ")
            else:
                with st.spinner("กำลังสร้าง Dashboard เปรียบเทียบ..."):
                    # ดึง ID ออกมาจากข้อความที่เลือก
                    id_a = int(vid_a.split(" - ")[0])
                    id_b = int(vid_b.split(" - ")[0])
                    
                    data_a = history_df[history_df['id'] == id_a].iloc[0]
                    data_b = history_df[history_df['id'] == id_b].iloc[0]
                    
                    st.divider()
                    
                    # --- 1. เปรียบเทียบตัวเลขพื้นฐาน ---
                    st.subheader("📈 1. เปรียบเทียบสถิติพื้นฐาน")
                    c1, c2 = st.columns(2)
                    
                    # คำนวณความต่าง (Delta)
                    diff_comments_a = int(data_a['total_comments'] - data_b['total_comments'])
                    diff_comments_b = int(data_b['total_comments'] - data_a['total_comments'])
                    
                    # 🔴 จัดการดึงรูปปกและชื่อคลิป A
                    v_id_a = extract_video_id(data_a['video_url'])
                    thumb_a = f"https://img.youtube.com/vi/{v_id_a}/hqdefault.jpg"
                    title_a = data_a.get('video_title', 'ไม่พบชื่อคลิป') if pd.notna(data_a.get('video_title')) else 'ไม่พบชื่อคลิป'
                    channel_a = data_a.get('channel_name', 'ไม่ทราบช่อง') if pd.notna(data_a.get('channel_name')) else 'ไม่ทราบช่อง'
                        
                    with c1:
                        st.markdown(f"### 🔴 คลิป A")
                        # แสดงรูปปกคลิป A
                        st.image(thumb_a, use_container_width=True)
                        # แสดงชื่อคลิป A
                        st.markdown(f"**🎬 {title_a}**")
                        st.caption(f"🔗 {data_a['video_url']}")
                        st.metric("💬 จำนวนคอมเมนต์ทั้งหมด", f"{data_a['total_comments']:,} ข้อความ", delta=diff_comments_a)
                        st.metric("⏱️ จุดพีคของคลิป (คนพิมพ์เยอะสุด)", data_a['peak_timestamp'])
                        
                    # 🔵 จัดการดึงรูปปกและชื่อคลิป B
                    v_id_b = extract_video_id(data_b['video_url'])
                    thumb_b = f"https://img.youtube.com/vi/{v_id_b}/hqdefault.jpg"
                    title_b = data_b.get('video_title', 'ไม่พบชื่อคลิป') if pd.notna(data_b.get('video_title')) else 'ไม่พบชื่อคลิป'
                    channel_b = data_b.get('channel_name', 'ไม่ทราบช่อง') if pd.notna(data_b.get('channel_name')) else 'ไม่ทราบช่อง'

                    with c2:
                        st.markdown(f"### 🔵 คลิป B")
                        # แสดงรูปปกคลิป B
                        st.image(thumb_b, use_container_width=True)
                        # แสดงชื่อคลิป B
                        st.markdown(f"**🎬 {title_b}**")
                        st.caption(f"🔗 {data_b['video_url']}")
                        st.metric("💬 จำนวนคอมเมนต์ทั้งหมด", f"{data_b['total_comments']:,} ข้อความ", delta=diff_comments_b)
                        st.metric("⏱️ จุดพีคของคลิป (คนพิมพ์เยอะสุด)", data_b['peak_timestamp'])
                        
                    st.divider()
                    
                    # --- 2. บทสรุป AI (Executive Conclusion) ---
                    st.subheader("🤖 2. บทสรุปเปรียบเทียบจาก AI (Executive Conclusion)")
                    with st.spinner("🧠 AI กำลังเปรียบเทียบข้อมูลเชิงลึก..."):
                        ai_conclusion = get_ai_comparison(
                            data_a['ai_summary'], data_b['ai_summary'], 
                            title_a, title_b, channel_a, channel_b, gemini_api_key,
                            model_provider=selected_model_provider
                        )
                    st.success(ai_conclusion)
                    
                    st.divider()
                    
                    # --- 3. กราฟเปรียบเทียบ Sentiment ---
                    st.subheader("📊 3. สัดส่วนอารมณ์ความรู้สึก (Sentiment %)")
                    st.markdown("ดูกราฟแท่งเปรียบเทียบสัดส่วน พลังบวก vs พลังลบ")
                    
                    # สร้าง DataFrame เพื่อนำไปทำกราฟ Plotly Grouped Bar Chart
                    compare_df = pd.DataFrame([
                        {'คลิป': 'คลิป A', 'ประเภทอารมณ์': 'บวก (Positive)', 'เปอร์เซ็นต์': data_a['positive_pct']},
                        {'คลิป': 'คลิป A', 'ประเภทอารมณ์': 'ทั่วไป (Neutral)', 'เปอร์เซ็นต์': data_a['neutral_pct']},
                        {'คลิป': 'คลิป A', 'ประเภทอารมณ์': 'ลบ (Negative)', 'เปอร์เซ็นต์': data_a['negative_pct']},
                        {'คลิป': 'คลิป B', 'ประเภทอารมณ์': 'บวก (Positive)', 'เปอร์เซ็นต์': data_b['positive_pct']},
                        {'คลิป': 'คลิป B', 'ประเภทอารมณ์': 'ทั่วไป (Neutral)', 'เปอร์เซ็นต์': data_b['neutral_pct']},
                        {'คลิป': 'คลิป B', 'ประเภทอารมณ์': 'ลบ (Negative)', 'เปอร์เซ็นต์': data_b['negative_pct']}
                    ])
                    
                    fig = px.bar(compare_df, x='ประเภทอารมณ์', y='เปอร์เซ็นต์', color='คลิป', barmode='group',
                                 color_discrete_map={'คลิป A': '#ff4b4b', 'คลิป B': '#3498db'},
                                 text_auto='.1f')
                    fig.update_layout(yaxis_title="เปอร์เซ็นต์ (%)", xaxis_title="")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.divider()
                    
                    # --- 4. เปรียบเทียบ AI Summary ---
                    st.subheader("📝 4. เปรียบเทียบ Insight โดยละเอียด (หมัดต่อหมัด)")
                    
                    # แปลงข้อความ JSON กลับมาเป็น Dict
                    try:
                        ai_a = json.loads(data_a['ai_summary'])
                    except Exception: ai_a = {}
                    
                    try:
                        ai_b = json.loads(data_b['ai_summary'])
                    except Exception: ai_b = {}
                    
                    col_ai1, col_ai2 = st.columns(2)
                    
                    # แสดงผลคลิป A
                    with col_ai1:
                        st.markdown("#### 🔴 AI Summary (คลิป A)")
                        
                        st.markdown("**🟢 สิ่งที่คนชอบ**")
                        for item in ai_a.get("positive", []):
                            with st.expander(f"✨ {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                st.write(item.get('details', 'ไม่มีรายละเอียด'))
                                
                        st.markdown("**🔴 ปัญหา/ดราม่า**")
                        for item in ai_a.get("negative", []):
                            with st.expander(f"⚠️ {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                st.write(item.get('details', 'ไม่มีรายละเอียด'))
                                
                        st.markdown("**🤡 แซว/ประชดประชัน**")
                        sarcasm_a = ai_a.get("sarcasm", [])
                        if sarcasm_a:
                            for item in sarcasm_a:
                                with st.expander(f"🤡 {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                    st.write(item.get('details', 'ไม่มีรายละเอียด'))
                        else:
                            st.info("ไม่พบการคอมเมนต์ประชดประชัน")
                            
                        st.markdown("**💡 สิ่งที่คนเรียกร้อง**")
                        for item in ai_a.get("recommendation", []):
                            with st.expander(f"📌 {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                st.write(item.get('details', 'ไม่มีรายละเอียด'))

                    # แสดงผลคลิป B
                    with col_ai2:
                        st.markdown("#### 🔵 AI Summary (คลิป B)")
                        
                        st.markdown("**🟢 สิ่งที่คนชอบ**")
                        for item in ai_b.get("positive", []):
                            with st.expander(f"✨ {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                st.write(item.get('details', 'ไม่มีรายละเอียด'))
                                
                        st.markdown("**🔴 ปัญหา/ดราม่า**")
                        for item in ai_b.get("negative", []):
                            with st.expander(f"⚠️ {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                st.write(item.get('details', 'ไม่มีรายละเอียด'))
                                
                        st.markdown("**🤡 แซว/ประชดประชัน**")
                        sarcasm_b = ai_b.get("sarcasm", [])
                        if sarcasm_b:
                            for item in sarcasm_b:
                                with st.expander(f"🤡 {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                    st.write(item.get('details', 'ไม่มีรายละเอียด'))
                        else:
                            st.info("ไม่พบการคอมเมนต์ประชดประชัน")
                            
                        st.markdown("**💡 สิ่งที่คนเรียกร้อง**")
                        for item in ai_b.get("recommendation", []):
                            with st.expander(f"📌 {item.get('topic', 'ไม่มีหัวข้อ')}"):
                                st.write(item.get('details', 'ไม่มีรายละเอียด'))