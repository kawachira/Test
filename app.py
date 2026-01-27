import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import random
import time

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (UPDATE: แก้ไขเรื่องหัวข้อหาย และเพิ่มการล็อคหน้าจอ) ---
st.markdown("""
    <style>
    /* 2. ✅ ล็อคการเลื่อนหน้าจอในตอนเริ่มต้น */
    body {
        overflow: hidden;
    }

    /* เพิ่ม padding ด้านล่าง เพื่อไม่ให้ปุ่ม Manage app บังเนื้อหา */
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }

    /* 1. ✅ ปรับ margin หัวข้อให้เสถียรขึ้น ไม่หายเมื่อรีเฟรช และยังชิดช่องค้นหา */
    h1 { text-align: center; font-size: 2.8rem !important; margin-bottom: 0px !important; margin-top: 5px !important; }
    
    div[data-testid="stForm"] {
        border: none; padding: 30px; border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px; margin: 0 auto;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 12px; font-size: 1.2rem; font-weight: bold; padding: 15px 0;
    }
    
    /* ดีไซน์กล่องหมายเหตุ (สำหรับข้อ 5) */
    .disclaimer-box {
        margin-top: 20px;
        margin-bottom: 20px;
        padding: 20px;
        background-color: #fff8e1;
        border: 2px solid #ffc107;
        border-radius: 12px;
        font-size: 1rem;
        color: #5d4037;
        text-align: center;
        font-weight: 500;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)
# ลบ st.write("") ออกเพื่อให้ชิดกับช่องค้นหาตาม CSS ที่ตั้งใหม่

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB,TSLA)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
        
        st.markdown("---")
        realtime_mode = st.checkbox("🔴 เปิดโหมด Real-time (ราคาขยับเองทุก 10 วิ)", value=False)
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที / รีเฟรชข้อมูล")

# --- 4. Helper Functions ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def custom_metric_html(label, value, status_text, color_status, icon_svg):
    if color_status == "green": color_code = "#16a34a"
    elif color_status == "red": color_code = "#dc2626"
    else: color_code = "#6b7280"
    
    # 3. ✅ UPDATE: ปรับ Layout ให้หัวข้อและค่าอยู่บรรทัดเดียวกัน และขยายขนาด
    html = f"""
    <div style="margin-bottom: 15px;">
        <div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 5px;">
            <div style="font-size: 18px; font-weight: 700; opacity: 0.9; color: var(--text-color); white-space: nowrap;">{label}</div>
            <div style="font-size: 24px; font-weight: 700; color: var(--text-color);">{value}</div>
        </div>
        <div style="display: flex; align-items: start; gap: 6px; font-size: 15px; font-weight: 600; color: {color_code}; line-height: 1.4;">
            <div style="margin-top: 3px; min-width: 24px;">{icon_svg}</div>
            <div>{status_text}</div>
        </div>
    </div>
    """
    return html

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "Extreme Overbought (80+): ระวังแรงขายรุนแรง"
    elif rsi >= 70: return "Overbought (70-80): ราคาตึงตัว อาจพักฐาน"
    elif rsi >= 55: return "Bullish Zone (55-70): โมเมนตัมกระทิงแข็งแกร่ง"
    elif rsi >= 45: return "Sideway/Neutral (45-55): รอเลือกทาง"
    elif rsi >= 30: return "Bearish Zone (30-45): โมเมนตัมหมีครองตลาด"
    elif rsi > 20: return "Oversold (20-30): เริ่มเข้าเขตของถูก"
    else: return "Extreme Oversold (<20): ลงลึกมาก ลุ้นเด้ง"

def get_rsi_short_label(rsi):
    if rsi >= 70: return "Overbought"
    elif rsi >= 55: return "Bullish"
    elif rsi >= 45: return "Neutral"
    elif rsi >= 30: return "Bearish"
    else: return "Oversold"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "N/A"
    if pe < 0: return "ขาดทุน (Loss)"
    if pe < 15: return "หุ้นถูก (Value)"
    if pe < 30: return "ราคาเหมาะสม (Fair)"
    return "หุ้นแพง (Growth)"

def get_adx_interpretation(adx):
    if adx >= 50: return "Super Strong Trend: เทรนด์แรงมาก (ระวังจุดพีค)"
    if adx >= 25: return "Strong Trend: มีเทรนด์ชัดเจน (น่าติดตาม)"
    return "Weak Trend/Sideway: ตลาดไร้ทิศทาง (แกว่งตัว)"

def get_detailed_explanation(adx, rsi, macd_val, macd_signal, price, ema200):
    if adx >= 50: adx_str = "ระดับ 'รุนแรงมาก' (Super Strong)"
    elif adx >= 25: adx_str = "ระดับ 'แข็งแกร่ง' (Strong)"
    elif adx >= 20: adx_str = "ระดับ 'กำลังก่อตัว' (Developing)"
    else: adx_str = "ระดับ 'อ่อนแอ/ไม่มีเทรนด์' (Weak)"
    
    if price > ema200: trend_dir = "ขาขึ้น (Uptrend)"
    else: trend_dir = "ขาลง (Downtrend)"
        
    adx_explain = f"ค่า **{adx:.2f}** อยู่ใน{adx_str} เมื่อรวมกับทิศทางที่เป็น **{trend_dir}** จึงสรุปได้ว่าตลาดกำลังมี **{trend_dir} ที่{adx_str.split("'")[1]}**"

    if rsi >= 70: rsi_explain = f"ค่า **{rsi:.2f}** สูงเกิน 70 แปลว่าราคา **'แพงเกินไป' (Overbought)** คนแห่ซื้อกันจนเสี่ยงที่จะโดนเทขาย"
    elif rsi <= 30: rsi_explain = f"ค่า **{rsi:.2f}** ต่ำกว่า 30 แปลว่าราคา **'ถูกเกินไป' (Oversold)** คนแห่ขายจนน่าจะมีแรงซื้อสวนกลับมา"
    else: rsi_explain = f"ค่า **{rsi:.2f}** อยู่ในช่วงกลางๆ (40-60) แปลว่าราคาสมเหตุสมผล ไม่ถูกและไม่แพงเกินไป"

    if macd_val > macd_signal: macd_explain = f"ค่า **{macd_val:.3f}** ตัดขึ้นเหนือเส้น Signal แปลว่า **'แรงซื้อชนะแรงขาย'** โมเมนตัมเป็นบวก"
    else: macd_explain = f"ค่า **{macd_val:.3f}** ตัดลงต่ำกว่าเส้น Signal แปลว่า **'แรงขายชนะแรงซื้อ'** โมเมนตัมเป็นลบ"

    return adx_explain, rsi_explain, macd_explain

def display_learning_section(rsi, rsi_interp, macd_val, macd_signal, macd_interp, adx_val, adx_interp, price, bb_upper, bb_lower):
    st.markdown("### 📘 มุมความรู้: ค่าต่างๆ คืออะไร? มาจากไหน?")
    with st.expander("คลิกเพื่อเรียนรู้ความหมายของอินดิเคเตอร์แต่ละตัว", expanded=False):
        st.markdown(f"#### 1. MACD (Moving Average Convergence Divergence)\n* **ค่าปัจจุบัน:** `{macd_val:.3f}` -> {macd_interp}\n* **คืออะไร?:** เครื่องมือดู 'โมเมนตัม' หรือแรงส่งของราคา\n* **มาจากไหน?:** เกิดจากการเอาเส้นค่าเฉลี่ย 2 เส้นมาลบกัน คือ **EMA(12) - EMA(26)**")
        st.divider()
        st.markdown(f"#### 2. RSI (Relative Strength Index)\n* **ค่าปัจจุบัน:** `{rsi:.2f}` -> {rsi_interp}\n* **คืออะไร?:** ดัชนีวัดการ 'ซื้อมากเกินไป' หรือ 'ขายมากเกินไป'\n* **มาจากไหน?:** คำนวณจากสัดส่วนของวันที่หุ้นขึ้นเทียบกับวันที่หุ้นลงในรอบ 14 วัน")
        st.divider()
        st.markdown(f"#### 3. ADX (Average Directional Index)\n* **ค่าปัจจุบัน:** `{adx_val:.2f}` -> {adx_interp}\n* **คืออะไร?:** เครื่องมือวัด 'ความรุนแรงของเทรนด์' (ไม่บอกทิศทาง บอกแค่ว่าแรงไหม)")
        st.divider()
        st.markdown(f"#### 4. Bollinger Bands (BB)\n* **Upper:** `{bb_upper:.2f}` | **Lower:** `{bb_lower:.2f}`\n* **คืออะไร?:** กรอบการแกว่งตัวของราคาเปรียบเหมือนขอบถนน")

# --- 5. Get Data ---
@st.cache_data(ttl=10, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "10y"
        df = ticker.history(period=period_val, interval=interval)
        
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'marketState': ticker.info.get('marketState', 'UNKNOWN'), # เอาไว้เช็คตลาดปิด
            'dayHigh': ticker.info.get('dayHigh'),
            'dayLow': ticker.info.get('dayLow'),
            'regularMarketOpen': ticker.info.get('regularMarketOpen'),
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

# --- 6. AI Logic ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower):
    report = { "technical": {}, "context": "", "action": {}, "status_color": "", "banner_title": "" }
    
    trend_strength = ""
    if adx_val > 50: trend_strength = "Trend แข็งแกร่งมาก (Super Strong)"
    elif adx_val > 25: trend_strength = "มี Trend ชัดเจน (Strong)"
    else: trend_strength = "Trend อ่อนแอ / ไซด์เวย์ (Weak/Sideway)"

    macd_status = "Bullish (ตัดขึ้น)" if macd_val > macd_signal else "Bearish (ตัดลง)"

    if price > ema200 and price > ema50 and price > ema20:
        report["status_color"] = "green"
        if adx_val > 25 and macd_val > macd_signal: report["banner_title"] = "🚀 Super Bullish: ขาขึ้นสมบูรณ์แบบ"
        else: report["banner_title"] = "Bullish: ขาขึ้น (แต่เริ่มตึงตัว)"
        report["technical"] = { "structure": f"ราคายืนเหนือทุกเส้น EMA + {trend_strength}", "status": f"MACD: {macd_val:.3f} ({macd_status}) สนับสนุนทิศทางขาขึ้น" }
        if price > bb_upper:
            report["context"] = "⚠️ ราคาทะลุกรอบ Bollinger Band บน (Overextended) ระวังแรงขายทำกำไรระยะสั้น"
            action_1 = "แบ่งขายทำกำไรบางส่วน (Trim Profit) แล้วรอรับกลับเมื่อย่อ"
        else:
            report["context"] = "โมเมนตัมแข็งแกร่ง รายใหญ่ยังคุมเกม ตลาดยังมีพื้นที่ให้วิ่งต่อ"
            action_1 = "ถือต่อ (Let Profit Run) ใช้ EMA 20 เป็นจุด Trailing Stop"
        action_2 = f"จุดรับที่ดีคือโซนเส้นกลาง (EMA 20) ที่บริเวณ **{ema20:.2f}**"
        report["action"] = {"strategy": "**กลยุทธ์: Follow Trend (เกาะเทรนด์)**", "steps": [action_1, action_2]}

    elif price > ema200 and price < ema20:
        report["status_color"] = "orange"
        report["banner_title"] = "Correction: พักตัวในขาขึ้น"
        reversal_sign = "เริ่มมีสัญญาณกลับตัว" if macd_val > macd_signal else "แรงขายยังกดดันอยู่"
        report["technical"] = { "structure": "หลุด EMA 20 ลงมาพักตัว แต่ยังอยู่เหนือ EMA 200", "status": f"ADX = {adx_val:.2f} ({trend_strength}) | MACD: {reversal_sign}" }
        report["context"] = "เป็นจังหวะย่อตัวเพื่อสร้างฐานใหม่ (Healthy Correction) ตราบใดที่ไม่หลุด EMA 200 โครงสร้างยังไม่เสีย"
        action_1 = f"รอสัญญาณกลับตัว (Reversal Candle) แถว EMA 50 ({ema50:.2f}) หรือ EMA 200"
        action_2 = "ถ้า MACD ตัดขึ้น (Cross up) อีกครั้ง คือสัญญาณเข้าซื้อรอบใหม่ (Re-entry)"
        report["action"] = {"strategy": "**กลยุทธ์: Buy on Dip (รอย่อซื้อ)**", "steps": [action_1, action_2]}

    elif price < ema200 and price < ema50:
        if price < ema20:
            if rsi < 25 or price < bb_lower:
                report["status_color"] = "orange"
                report["banner_title"] = "Oversold Bounce: ลุ้นเด้งสั้น (Oversold)"
                report["technical"] = { "structure": "ราคาลงลึกหลุดกรอบล่าง Bollinger / RSI ต่ำมาก", "status": "เข้าเขต Selling Climax (ขายมากเกินไป) มีโอกาสดีดกลับแรงๆ" }
                report["context"] = "ความเสี่ยงสูง แต่ Reward คุ้มค่าสำหรับคนเล่นสั้น (High Risk High Return)"
                action_1 = f"เก็งกำไรสั้นๆ (Scalp) เป้าขายคือโซนเส้นกลาง (EMA 20) แถวๆ **{ema20:.2f}**"
                action_2 = "วาง Stop Loss ไว้ที่ Low ล่าสุดทันที ห้ามลืม"
            else:
                report["status_color"] = "red"
                report["banner_title"] = "Bearish: ขาลงเต็มตัว"
                report["technical"] = { "structure": f"ราคาอยู่ใต้ EMA ทุกเส้น + {trend_strength}", "status": "MACD อยู่ในแดนลบ (Negative Zone) ยืนยันขาลง" }
                report["context"] = "แรงขายยังคงครองตลาด (Dominated by Sellers) การเด้งขึ้นคือจังหวะขาย"
                action_1 = "ห้ามรับมีด (Don't Buy) จนกว่าราคาจะยืนเหนือ EMA 20 ได้"
                action_2 = "ใครติดดอย หาจังหวะเด้งเพื่อลดพอร์ต (Cut Loss / Reduce Position)"
        else:
            report["status_color"] = "orange"
            report["banner_title"] = "Rebound: เด้งเพื่อลงต่อ?"
            report["technical"] = { "structure": "ราคาดีดกลับมาหา EMA 50/200 แต่เทรนด์หลักยังลง", "status": f"MACD ตัดขึ้นระยะสั้น แต่ยังอยู่ใต้ศูนย์ (Weak Bullish)" }
            report["context"] = "ระวังกับดักกระทิง (Bull Trap) แนวต้าน EMA 200 มักจะผ่านยากในครั้งแรก"
            action_1 = f"จับตาแนวต้าน {ema200:.2f} ถ้าไม่ผ่านให้ขาย"
            action_2 = "เล่นสั้นเท่านั้น (Hit & Run)"
        report["action"] = {"strategy": "**กลยุทธ์: Defensive / Short Sell**", "steps": [action_1, action_2]}

    else:
        report["status_color"] = "yellow"
        bb_width = (bb_upper - bb_lower) / price
        sqz_text = "ระเบิดเลือกทางเร็วๆนี้" if bb_width < 0.10 else "แกว่งตัวในกรอบกว้าง"
        report["banner_title"] = "Sideway: รอเลือกทาง"
        report["technical"] = { "structure": "ราคาพันกันนัวเนีย EMA + ADX ต่ำ (ไม่มีเทรนด์)", "status": f"Bollinger Band บีบตัว: {sqz_text}" }
        report["context"] = "ตลาดยังไม่เลือกข้างชัดเจน (Indecision) การเทรดในช่วงนี้จะยากเพราะ False Signal เยอะ"
        action_1 = f"รอให้ราคา Breakout กรอบ Bollinger บน ({bb_upper:.2f}) หรือ ล่าง ({bb_lower:.2f}) ก่อน"
        action_2 = "เน้นซื้อที่แนวรับ ขายที่แนวต้าน (Swing Trade) อย่าหวังคำโต"
        report["action"] = {"strategy": "**กลยุทธ์: Wait & See / Swing Trade**", "steps": [action_1, action_2]}

    return report

# --- 7. Display ---
if submit_btn:
    st.divider()
    
    # 2. ✅ ปลดล๊อคหน้าจอให้เลื่อนได้ เมื่อกดปุ่ม
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)

    result_placeholder = st.empty()
    
    while True:
        with result_placeholder.container():
            with st.spinner(f"AI กำลังประมวลผล {symbol_input} แบบละเอียด (Full Loop)..."):
                df, info = get_data(symbol_input, tf_code)

            if df is not None and not df.empty and len(df) > 200:
                df['EMA20'] = ta.ema(df['Close'], length=20)
                df['EMA50'] = ta.ema(df['Close'], length=50)
                df['EMA200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)
                
                macd = ta.macd(df['Close'])
                df = pd.concat([df, macd], axis=1)
                
                bbands = ta.bbands(df['Close'], length=20, std=2)
                if bbands is not None and len(bbands.columns) >= 3:
                    bbl_col_name, bbu_col_name = bbands.columns[0], bbands.columns[2]
                    df = pd.concat([df, bbands], axis=1)
                else: bbl_col_name, bbu_col_name = None, None

                adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                df = pd.concat([df, adx], axis=1)

                last = df.iloc[-1]
                price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
                rsi = last['RSI']
                ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
                
                try: macd_val, macd_signal = last['MACD_12_26_9'], last['MACDs_12_26_9']
                except KeyError: macd_val, macd_signal = 0, 0
                try: adx_val = last['ADX_14']
                except KeyError: adx_val = 0

                if bbu_col_name and bbl_col_name: bb_upper, bb_lower = last[bbu_col_name], last[bbl_col_name]
                else: bb_upper, bb_lower = price * 1.05, price * 0.95
                
                ai_report = analyze_market_structure(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower)

                # --- ส่วนที่เพิ่มใหม่: ดึงรูปโลโก้หุ้น ---
                logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
                fallback_url = "https://cdn-icons-png.flaticon.com/512/720/720453.png"
                
                icon_html = f"""
                <img src="{logo_url}" 
                     onerror="this.onerror=null; this.src='{fallback_url}';" 
                     style="height: 50px; width: 50px; border-radius: 50%; vertical-align: middle; margin-right: 10px; object-fit: contain; background-color: white; border: 1px solid #e0e0e0; padding: 2px;">
                """
                # -------------------------------------

                st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>{icon_html} {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    reg_price, reg_chg = info.get('regularMarketPrice'), info.get('regularMarketChange')
                    if reg_price and reg_chg:
                        prev_c = reg_price - reg_chg
                        reg_pct = (reg_chg / prev_c) * 100 if prev_c != 0 else 0.0
                    else: reg_pct = 0.0
                    
                    color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"
                    bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
                    
                    st.markdown(f"""
                    <div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                      <div style="font-size:40px; font-weight:600; line-height: 1;">
                        {reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span>
                      </div>
                      <div style="
                        display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text};
                        padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">
                        {arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # --- UPDATE NEW: Layout OHLC + Pre/Post ---
                    # Helper function สร้าง Pill สีเขียว/แดง (สำหรับ Pre/Post)
                    def make_pill(change, percent):
                        color = "#16a34a" if change >= 0 else "#dc2626"
                        bg = "#e8f5ec" if change >= 0 else "#fee2e2"
                        arrow = "▲" if change >= 0 else "▼"
                        # UPDATE: font-size 12px
                        return f'<span style="background:{bg}; color:{color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{arrow} {change:+.2f} ({percent:.2f}%)</span>'

                    # 1. สร้าง HTML ส่วน OHLC (UPDATE: font-size 12px, margin-top -5px เพื่อขยับขึ้น)
                    ohlc_html = ""
                    m_state = info.get('marketState', '').upper()
                    if m_state != "REGULAR": 
                        d_open = info.get('regularMarketOpen')
                        d_high = info.get('dayHigh')
                        d_low = info.get('dayLow')
                        d_close = info.get('regularMarketPrice')
                        
                        if d_open and d_high and d_low and d_close:
                            # คำนวณสีตัวเลข (เขียว/แดง) ตาม Change ของวัน
                            day_chg = info.get('regularMarketChange', 0)
                            val_color = "#16a34a" if day_chg >= 0 else "#dc2626"
                            
                            ohlc_html = f"""
                            <div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; font-family: 'Source Sans Pro', sans-serif; white-space: nowrap; overflow-x: auto;">
                                <span style="margin-right: 5px; opacity: 0.7;">O</span><span style="color: {val_color}; margin-right: 12px;">{d_open:.2f}</span>
                                <span style="margin-right: 5px; opacity: 0.7;">H</span><span style="color: {val_color}; margin-right: 12px;">{d_high:.2f}</span>
                                <span style="margin-right: 5px; opacity: 0.7;">L</span><span style="color: {val_color}; margin-right: 12px;">{d_low:.2f}</span>
                                <span style="margin-right: 5px; opacity: 0.7;">C</span><span style="color: {val_color};">{d_close:.2f}</span>
                            </div>
                            """

                    # 2. สร้าง HTML ส่วน Pre/Post Market
                    pre_post_html = ""
                    
                    # Pre Market
                    if info.get('preMarketPrice') and info.get('preMarketChange'):
                        p = info['preMarketPrice']
                        c = info['preMarketChange']
                        prev_p = p - c
                        pct = (c / prev_p) * 100 if prev_p != 0 else 0
                        # UPDATE: font-size 12px
                        pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">☀️ Pre: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'

                    # Post Market
                    if info.get('postMarketPrice') and info.get('postMarketChange'):
                         p = info['postMarketPrice']
                         c = info['postMarketChange']
                         prev_p = p - c
                         pct = (c / prev_p) * 100 if prev_p != 0 else 0
                         # UPDATE: font-size 12px
                         pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">🌙 Post: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'

                    # แสดงผล (UPDATE: margin-top: -5px เพื่อขยับขึ้น, margin-bottom: 15px เพื่อเว้นห่างกรอบเทรนด์)
                    if ohlc_html or pre_post_html:
                        st.markdown(f'<div style="margin-top: -5px; margin-bottom: 15px;">{ohlc_html}{pre_post_html}</div>', unsafe_allow_html=True)
                    # -----------------------------------------------------------

                if tf_code == "1h": tf_label = "TF Hour"
                elif tf_code == "1wk": tf_label = "TF Week"
                else: tf_label = "TF Day"
                
                st_color = ai_report["status_color"]
                main_status = ai_report["banner_title"]
                if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
                elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
                else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

                # --- Metrics Section (ใช้ Custom HTML และ SVG Icon) ---
                c3, c4, c5 = st.columns(3)
                
                # --- SVG Definitions ---
                # ลูกศรขึ้น/ลง
                icon_up_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>"""
                icon_down_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12l7 7 7-7"/></svg>"""
                icon_flat_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#6b7280"><circle cx="12" cy="12" r="10"/></svg>"""
                
                # 3. ✅ UPDATE: เปลี่ยนไอคอน Sideway เป็นลูกศรสองหัว (Double Arrow) สีเทา
                icon_wave_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l3-3-3-3"/><path d="M6 9l-3 3 3 3"/><path d="M21 12H3"/></svg>"""

                # 1. P/E Ratio (UPDATE: ใช้ Custom HTML เพื่อความสวยงามเหมือน RSI/ADX)
                with c3:
                    pe_val = info['trailingPE']
                    pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
                    pe_interp = get_pe_interpretation(pe_val)
                    
                    if isinstance(pe_val, (int,float)):
                        if pe_val < 0: pe_color = "red"; pe_icon = icon_down_svg
                        elif pe_val < 15: pe_color = "green"; pe_icon = icon_up_svg
                        elif pe_val < 30: pe_color = "green"; pe_icon = icon_flat_svg # Fair = Greenish/Neutral
                        else: pe_color = "red"; pe_icon = icon_down_svg
                    else:
                        pe_color = "gray"; pe_icon = icon_flat_svg
                        
                    st.markdown(custom_metric_html("📊 P/E Ratio", pe_str, pe_interp, pe_color, pe_icon), unsafe_allow_html=True)

                # 2. RSI Metric (UPDATE: รวม Description เข้าไปใน status line)
                with c4:
                    rsi_interp = get_rsi_interpretation(rsi) # Get full text
                    if rsi >= 70: c_stat = "red"; icon_final = icon_up_svg # Overbought
                    elif rsi >= 55: c_stat = "green"; icon_final = icon_up_svg
                    elif rsi >= 45: c_stat = "gray"; icon_final = icon_flat_svg
                    elif rsi >= 30: c_stat = "red"; icon_final = icon_down_svg
                    else: c_stat = "green"; icon_final = icon_down_svg
                    
                    st.markdown(custom_metric_html("⚡ RSI (14)", f"{rsi:.2f}", rsi_interp, c_stat, icon_final), unsafe_allow_html=True)

                # 3. ADX Metric (UPDATE: รวม Description เข้าไปใน status line)
                with c5:
                    adx_interp = get_adx_interpretation(adx_val)
                    if adx_val > 25:
                        c_stat = "green"; icon_final = icon_up_svg
                    else:
                        c_stat = "gray"; icon_final = icon_wave_svg
                    
                    st.markdown(custom_metric_html("💪 ADX Strength", f"{adx_val:.2f}", adx_interp, c_stat, icon_final), unsafe_allow_html=True)

                st.write("") 

                c_ema, c_ai = st.columns([1.5, 2])
                with c_ema:
                    st.subheader("📉 Technical Indicators")
                    st.markdown(f"""
                    <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'>
                        <div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd; font-weight:bold;'><span>Indicator</span> <span>Value</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 20 (สั้น)</span> <span>{ema20:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 50 (กลาง)</span> <span>{ema50:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 200 (ยาว)</span> <span>{ema200:.2f}</span></div>
                        <div style='margin-top:5px; margin-bottom:5px; border-bottom:1px solid #ddd;'></div>
                        <div style='display:flex; justify-content:space-between;'><span>MACD</span> <span style='color:{'green' if macd_val > macd_signal else 'red'}'>{macd_val:.3f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>Upper Band</span> <span>{bb_upper:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>Lower Band</span> <span>{bb_lower:.2f}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.subheader("🚧 Key Levels (Smart Filter)")
                    potential_levels = [
                        (ema20, "EMA 20"), (ema50, "EMA 50"), (ema200, "EMA 200"),
                        (bb_lower, "BB Lower"), (bb_upper, "BB Upper"),
                        (df['High'].tail(60).max(), "High 60 Days"),
                        (df['Low'].tail(60).min(), "Low 60 Days")
                    ]
                    raw_supports = []
                    raw_resistances = []
                    for val, label in potential_levels:
                        if val < price: raw_supports.append((val, label))
                        elif val > price: raw_resistances.append((val, label))
                    raw_supports.sort(key=lambda x: x[0], reverse=True)
                    raw_resistances.sort(key=lambda x: x[0])

                    def filter_levels(levels, threshold_pct=0.015):
                        selected = []
                        for val, label in levels:
                            if not selected:
                                selected.append((val, label))
                            else:
                                last_val = selected[-1][0]
                                diff = abs(val - last_val) / last_val
                                if diff > threshold_pct: selected.append((val, label))
                        return selected

                    final_supports = filter_levels(raw_supports)[:3]
                    final_resistances = filter_levels(raw_resistances)[:2]

                    st.markdown("#### 🟢 แนวรับ (จุดรอซื้อ)")
                    if final_supports:
                        for v, d in final_supports: st.write(f"- **{v:.2f}** : {d}")
                    else: st.write("- ไม่มีแนวรับใกล้เคียง (All Time High?)")
                    st.markdown("#### 🔴 แนวต้าน (จุดรอขาย)")
                    if final_resistances:
                        for v, d in final_resistances: st.write(f"- **{v:.2f}** : {d}")
                    else: st.write("- ไม่มีแนวต้านใกล้เคียง (All Time Low?)")

                with c_ai:
                    exp_adx, exp_rsi, exp_macd = get_detailed_explanation(adx_val, rsi, macd_val, macd_signal, price, ema200)
                    st.subheader("🧐 AI อธิบายความหมาย")
                    with st.container():
                        st.info(f"💪 **ADX:** {exp_adx}")
                        st.info(f"⚡ **RSI:** {exp_rsi}")
                        st.info(f"🌊 **MACD:** {exp_macd}")
                    
                    st.subheader("🤖 AI STRATEGY")
                    with st.chat_message("assistant"):
                        st.markdown(f"### 🎯 {ai_report['action']['strategy']}")
                        for step in ai_report['action']['steps']: st.write(f"- {step}")
                        st.markdown("---")
                        
                        # 4. ✅ UPDATE: ใช้ st.info เพื่อให้มุมมองดู "ขลัง" (ทางการ) และ "เด่น" (มีพื้นหลัง)
                        st.info(f"**👁️ มุมมอง (Perspective):**\n\n{ai_report['context']}")

                st.write("")
                # 5. ✅ UPDATE: เพิ่มกล่องหมายเหตุ (Disclaimer)
                st.markdown("""
                <div class='disclaimer-box'>
                    ⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากการวิเคราะห์ทางเทคนิคด้วยระบบ AI เพื่อประกอบการตัดสินใจเท่านั้น <br>
                    ผู้ใช้งานควรศึกษาก่อนการลงทุน ผู้พัฒนาไม่รับผิดชอบต่อความเสียหายใดๆ ที่เกิดขึ้นจากการนำข้อมูลนี้ไปใช้
                </div>
                """, unsafe_allow_html=True)

                st.divider()
                rsi_interp_str = get_rsi_interpretation(rsi)
                adx_interp_str = get_adx_interpretation(adx_val)
                macd_interp_str = "🟢 แรงซื้อนำ (Bullish)" if macd_val > macd_signal else "🔴 แรงขายนำ (Bearish)"
                display_learning_section(rsi, rsi_interp_str, macd_val, macd_signal, macd_interp_str, adx_val, adx_interp_str, price, bb_upper, bb_lower)

            else:
                st.error("ไม่พบข้อมูลหุ้น หรือ ข้อมูลไม่เพียงพอสำหรับคำนวณ Indicator (ต้องมีมากกว่า 200 แท่งเทียน)")
        
        if not realtime_mode: break
        time.sleep(10)
