import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import random
import time  # <--- ต้องมี import time เพื่อใช้หน่วงเวลา Loop

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    h1 { text-align: center; font-size: 2.8rem !important; margin-bottom: 10px; }
    div[data-testid="stForm"] {
        border: none; padding: 30px; border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px; margin: 0 auto;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 12px; font-size: 1.2rem; font-weight: bold; padding: 15px 0;
    }
    div[data-testid="metric-container"] label { font-size: 1.1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)
st.write("")

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
        
        # --- Checkbox Real-time ---
        st.markdown("---")
        realtime_mode = st.checkbox("🔴 เปิดโหมด Real-time (ราคาขยับเองทุก 10 วิ)", value=False)
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที / เริ่มระบบ")

# --- 4. Helper Functions ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 **Extreme Overbought (80+):** แรงซื้อบ้าคลั่ง ระวังการเทขายรุนแรง"
    elif rsi >= 70: return "🟠 **Overbought (70-80):** ราคาเริ่มตึงตัว อาจมีการเทขายพักฐานเร็วๆ นี้"
    elif rsi >= 55: return "🟢 **Bullish Zone (55-70):** โมเมนตัมกระทิงครองตลาด ราคาแข็งแกร่ง"
    elif rsi >= 45: return "⚪ **Sideway/Neutral (45-55):** แรงซื้อขายก้ำกึ่ง รอเลือกทางที่ชัดเจน"
    elif rsi >= 30: return "🟠 **Bearish Zone (30-45):** โมเมนตัมหมีครองตลาด ระวังราคาไหลลงต่อ"
    elif rsi > 20: return "🟢 **Oversold (20-30):** ขายมากเกินไป เริ่มเข้าเขต 'ของถูก' ลุ้นเด้งรีบาวด์"
    else: return "🟢 **Extreme Oversold (<20):** ลงลึกมาก Panic Sell จบแล้ว"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ N/A (บริษัทอาจขาดทุน/ไม่มีกำไร)"
    if pe < 0: return "🔴 ขาดทุน (Earnings ติดลบ)"
    if pe < 15: return "🟢 หุ้นถูก (Value)"
    if pe < 30: return "🟡 ราคาเหมาะสม"
    return "🟠 หุ้นแพง (Growth)"

# --- 5. Get Data ---
@st.cache_data(ttl=10, show_spinner=False) # ใช้ TTL 10 วิ เพื่อให้ Realtime ทำงานได้จริง
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "10y"
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

# --- 6. AI Logic (ใช้เวอร์ชัน "UPDATED" ที่ฉลาดกว่าและพูดได้เยอะกว่า) ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    report = {
        "technical": {},
        "context": "",
        "action": {},
        "status_color": "",
        "banner_title": ""
    }

    def pick_one(sentences):
        return random.choice(sentences)

    # --- Scenario 1: ขาขึ้นแข็งแกร่ง ---
    if price > ema200 and price > ema50 and price > ema20:
        report["status_color"] = "green"
        report["banner_title"] = pick_one([
            "Bullish Mode: กระทิงดุเต็มพิกัด",
            "Strong Uptrend: หุ้นแกร่งกว่าตลาด",
            "Momentum High: แรงส่งขาขึ้นรุนแรง"
        ])
        
        report["technical"] = {
            "structure": "ราคาเรียงตัวสวยงามยืนเหนือทุกเส้น (Price > EMA20 > 50 > 200)",
            "status": pick_one([
                "Volume เข้า แรงซื้อสนับสนุนชัดเจน",
                "กราฟทรงนี้คือผู้ชนะ (Winner Stock)",
                "Trend ขาขึ้นชัดเจน ยากที่จะลงแรงๆ ในทันที"
            ])
        }
        
        ctx_options = [
            "ใครมีของกอดแน่นๆ ตลาดยังให้ค่า Premium กับหุ้นตัวนี้ อย่ารีบขายหมู",
            "ทรงกราฟแบบนี้ รายใหญ่น่าจะยังคุมเกมอยู่ ราคาอาจจะย่อบ้างแต่ไม่น่าเสียทรง",
            "เป็นช่วงเวลาโกยกำไร (Harvest Time) ปล่อยให้ Trend ทำงานแทนเรา"
        ]
        report["context"] = pick_one(ctx_options)
        
        strategy = "**กลยุทธ์: Let Profit Run & Trailing Stop**"
        
        if rsi > 75: 
            action_1 = "⚠️ **เตือนภัย:** RSI สูงจัด (Overbought) ห้ามไล่ราคาเด็ดขาด!"
            action_2 = "สายซิ่ง: แบ่งขายล็อกกำไรเข้ากระเป๋าบ้าง (Lock Profit) แล้วรอย่อรับใหม่"
        else:
            action_1 = "🟢 **คนมีของ:** ถือต่อ (Hold) ใช้เส้น EMA 20 เป็นจุดหนี"
            action_2 = f"🟡 **คนไม่มีของ:** รอจังหวะย่อแตะ EMA 20 ({ema20:.2f}) แล้วค่อยเข้า (Buy on Dip)"

        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 2: ขาขึ้นพักตัว ---
    elif price > ema200 and price < ema20:
        report["status_color"] = "orange"
        report["banner_title"] = pick_one([
            "Correction: พักตัวเพื่อไปต่อ?",
            "Healthy Pullback: ย่อตัวสร้างฐาน",
            "Short-term Weakness: แรงขายระยะสั้น"
        ])

        report["technical"] = {
            "structure": "ราคาหลุด EMA 20 ลงมาหาแนวรับ EMA 50 (พักตัวระยะกลาง)",
            "status": "แรงขายทำกำไรกดดัน แต่เทรนด์ใหญ่ (EMA 200) ยังเป็นขาขึ้น"
        }
        
        ctx_options = [
            "ตลาดกำลังวัดใจว่าจะรับอยู่ไหม แถวๆ EMA 50 คือจุดวัดใจสำคัญ",
            "เป็นการย่อเคลียร์คนเล่นสั้น (Shake out) ถ้าพื้นฐานดี นี่คือโอกาส",
            "ระวัง! ถ้ารับไม่อยู่ อาจจะไหลลงยาวไปหา EMA 200"
        ]
        report["context"] = pick_one(ctx_options)
        
        strategy = "**กลยุทธ์: Wait & See (รอสัญญาณกลับตัว)**"
        action_1 = f"🎯 **จุด Sniper:** รอรับที่ EMA 50 ({ema50:.2f}) ถ้ามีแท่งเทียนกลับตัวให้เข้าสะสม"
        
        if price < ema50: 
             action_2 = f"ระวัง! ราคาหลุด EMA 50 ลงมา แนวรับถัดไปคือ EMA 200 ({ema200:.2f}) ชะลอการซื้อ"
        else:
             action_2 = f"🛡️ **จุดหนี:** ถ้าหลุด {ema50:.2f} ให้ถอยออกมาดูสถานการณ์ก่อน ห้ามฝืน"

        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 3: ขาลง ---
    elif price < ema200 and price < ema50:
        if price < ema20:
            if rsi < 25:
                report["status_color"] = "orange" 
                report["banner_title"] = "Oversold Bounce: ลุ้นเด้งสั้น (ความเสี่ยงสูง)"
                report["technical"] = {
                    "structure": "ราคาลงลึกมากจน RSI เข้าเขตขายมากเกินไป (<25)",
                    "status": "Panic Sell รุนแรง อาจเกิด Technical Rebound เร็วๆ นี้"
                }
                report["context"] = "ลงแรงเกินพื้นฐาน หรือเกิดความกลัวสุดขีด มักจะมีแรงซื้อเก็งกำไรสวนเข้ามาสั้นๆ"
                strategy = "**กลยุทธ์: Contrarian (ชาวสวน)**"
                action_1 = "🧨 **สายซิ่งเท่านั้น:** เข้าเร็ว-ออกเร็ว (Hit & Run) ห้ามแช่นาน"
