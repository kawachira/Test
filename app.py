import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import random  # <--- เพิ่ม import random เพื่อใช้ในการสุ่มประโยค AI

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่งความสวยงาม ---
st.markdown("""
    <style>
    /* ลดระยะห่างด้านบน */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }

    /* ล็อคการเลื่อนหน้าจอ (Scroll) เป็นค่าเริ่มต้น */
    div[data-testid="stAppViewContainer"] {
        overflow: hidden !important;
    }

    /* จัด Title ให้อยู่ตรงกลาง */
    h1 {
        text-align: center;
        font-size: 2.8rem !important;
        margin-bottom: 10px;
    }
    
    /* กรอบค้นหาแบบใหม่ */
    div[data-testid="stForm"] {
        border: none;
        padding: 30px;
        border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* ปรับปุ่มกดให้เต็มและตัวใหญ่ */
    div[data-testid="stFormSubmitButton"] button {
        width: 100%;
        border-radius: 12px;
        font-size: 1.2rem;
        font-weight: bold;
        padding: 15px 0;
    }
    
    /* ปรับขนาดตัวหนังสือใน Metric ให้ใหญ่ขึ้น */
    div[data-testid="metric-container"] label { font-size: 1.1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อและค้นหา ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)

st.write("") # เว้นระยะ

# สร้าง Form ค้นหา (จัดกึ่งกลาง)
col_space1, col_form, col_space2 = st.columns([1, 2, 1])

with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,GOOGL,RKLB, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            
            # Logic แปลงค่าเป็น code ที่ yfinance เข้าใจ
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
        
        realtime_mode = st.checkbox("🔴 เปิดโหมด Real-time (ราคาขยับเองทุก 10 วิ)", value=False)
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. ฟังก์ชันช่วยแปลความหมาย & Helper Functions ---

def arrow_html(change):
    if change is None: return ""
    if change > 0:
        return "<span style='color:#16a34a;font-weight:600'>▲</span>"  # เขียว
    elif change < 0:
        return "<span style='color:#dc2626;font-weight:600'>▼</span>"  # แดง
    else:
        return "<span style='color:gray'>—</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 **Extreme Overbought (80+):** แรงซื้อบ้าคลั่ง ระวังการเทขายรุนแรง (ห้ามไล่ราคา)"
    elif rsi >= 70: return "🟠 **Overbought (70-80):** ราคาเริ่มตึงตัว อาจมีการเทขายพักฐานเร็วๆ นี้"
    elif rsi >= 55: return "🟢 **Bullish Zone (55-70):** โมเมนตัมกระทิงครองตลาด ราคาแข็งแกร่ง"
    elif rsi >= 45: return "⚪ **Sideway/Neutral (45-55):** แรงซื้อขายก้ำกึ่ง รอเลือกทางที่ชัดเจน"
    elif rsi >= 30: return "🟠 **Bearish Zone (30-45):** โมเมนตัมหมีครองตลาด ระวังราคาไหลลงต่อ"
    elif rsi > 20: return "🟢 **Oversold (20-30):** ขายมากเกินไป เริ่มเข้าเขต 'ของถูก' ลุ้นเด้งรีบาวด์"
    else: return "🟢 **Extreme Oversold (<20):** ลงลึกมาก Panic Sell จบแล้ว เป็นจุดวัดใจซื้อสวนสั้นๆ"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ **N/A:** ไม่มีข้อมูล หรือบริษัทขาดทุน (คำนวณไม่ได้)"
    if pe < 0: return "🔴 **ขาดทุน (Negative P/E):** บริษัทยังไม่มีกำไร"
    if pe < 15: return "🟢 **หุ้นถูก (Low P/E):** ราคาต่ำเมื่อเทียบกับกำไร (Value Stock) หรือตลาดคาดหวังต่ำ"
    if pe < 30: return "🟡 **ราคาเหมาะสม (Average P/E):** ราคาอยู่ในเกณฑ์ค่าเฉลี่ยปกติ"
    return "🟠 **หุ้นแพง (High P/E):** ราคาสูง หรือตลาดคาดหวังการเติบโตสูงมาก (Growth Stock)"

# --- 5. ฟังก์ชันดึงข้อมูล (Cache) ---
@st.cache_data(ttl=5, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        
        if interval == "1h": period_val = "730d"
        else: period_val = "10y"
            
        df = ticker.history(period=period_val, interval=interval)
        
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'trailingPE': ticker.info.get('trailingPE', 'N/A'),
            
            'regularMarketPrice': ticker.info.get('regularMarketPrice'),
            'regularMarketChange': ticker.info.get('regularMarketChange'),
            'regularMarketChangePercent': ticker.info.get('regularMarketChangePercent'),

            'preMarketPrice': ticker.info.get('preMarketPrice'),
            'preMarketChange': ticker.info.get('preMarketChange'),
            'preMarketChangePercent': ticker.info.get('preMarketChangePercent'),

            'postMarketPrice': ticker.info.get('postMarketPrice'),
            'postMarketChange': ticker.info.get('postMarketChange'),
            'postMarketChangePercent': ticker.info.get('postMarketChangePercent'),
        }
        
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]
             stock_info['regularMarketChangePercent'] = (stock_info['regularMarketChange'] / df['Close'].iloc[-2])

        return df, stock_info
    except:
        return None, None

# --- 6. ฟังก์ชันสมอง AI (แบบใหม่: มีความหลากหลาย) ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    report = {
        "technical": {},
        "context": "",
