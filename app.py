import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import requests
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master Ultimate", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (รวม V1 และ V2) ---
st.markdown("""
    <style>
    body { overflow-x: hidden; }
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
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
    .disclaimer-box {
        margin-top: 20px; padding: 20px; background-color: #fff8e1;
        border: 2px solid #ffc107; border-radius: 12px;
        font-size: 0.9rem; color: #5d4037; text-align: center;
    }
    .metric-card {
        background-color: var(--secondary-background-color);
        padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center; height: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai Ultimate<br><span style='font-size: 1.2rem; opacity: 0.7;'>Integrated Intelligence System</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น (Full Integration)")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น NVDA, TSLA, AAPL)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            # ตั้งค่า Timeframe หลัก และ Timeframe รอง (MTF)
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo" 
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"   
            else: tf_code = "1d"; mtf_code = "1wk"                    
        
        st.markdown("---")
        realtime_mode = st.checkbox("🔴 Real-time Mode (Refresh 10s)", value=False)
        submit_btn = st.form_submit_button("🚀 วิเคราะห์เต็มรูปแบบ (Full Loop)")

# --- 4. Helper Functions (V1 & V2 Combined) ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def custom_metric_html(label, value, status_text, color_status, icon_svg):
    if color_status == "green": color_code = "#16a34a"
    elif color_status == "red": color_code = "#dc2626"
    else: color_code = "#6b7280"
    
    html = f"""
    <div style="margin-bottom: 15px;">
        <div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 5px;">
            <div style="font-size: 16px; font-weight: 700; opacity: 0.9; white-space: nowrap;">{label}</div>
            <div style="font-size: 22px; font-weight: 700;">{value}</div>
        </div>
        <div style="display: flex; align-items: start; gap: 6px; font-size: 14px; font-weight: 600; color: {color_code}; line-height: 1.4;">
            <div style="margin-top: 3px; min-width: 20px;">{icon_svg}</div>
            <div>{status_text}</div>
        </div>
    </div>
    """
    return html

# --- V1 Interpretation Functions (เก็บของเดิมไว้ทั้งหมด) ---
def get_rsi_interpretation(rsi):
    if rsi >= 80: return "Extreme Overbought (80+): ระวังแรงขายรุนแรง"
    elif rsi >= 70: return "Overbought (70-80): ราคาตึงตัว อาจพักฐาน"
    elif rsi >= 55: return "Bullish Zone (55-70): โมเมนตัมกระทิงแข็งแกร่ง"
    elif rsi >= 45: return "Sideway/Neutral (45-55): รอเลือกทาง"
    elif rsi >= 30: return "Bearish Zone (30-45): โมเมนตัมหมีครองตลาด"
    elif rsi > 20: return "Oversold (20-30): เริ่มเข้าเขตของถูก"
    else: return "Extreme Oversold (<20): ลงลึกมาก ลุ้นเด้ง"

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
    st.markdown("### 📘 มุมความรู้: ค่าต่างๆ คืออะไร? มาจากไหน? (Original V1)")
    with st.expander("คลิกเพื่อเรียนรู้ความหมายของอินดิเคเตอร์แต่ละตัว", expanded=False):
        st.markdown(f"#### 1. MACD (Moving Average Convergence Divergence)\n* **ค่าปัจจุบัน:** `{macd_val:.3f}` -> {macd_interp}\n* **คืออะไร?:** เครื่องมือดู 'โมเมนตัม' หรือแรงส่งของราคา\n* **มาจากไหน?:** เกิดจากการเอาเส้นค่าเฉลี่ย 2 เส้นมาลบกัน คือ **EMA(12) - EMA(26)**")
        st.divider()
        st.markdown(f"#### 2. RSI (Relative Strength Index)\n* **ค่าปัจจุบัน:** `{rsi:.2f}` -> {rsi_interp}\n* **คืออะไร?:** ดัชนีวัดการ 'ซื้อมากเกินไป' หรือ 'ขายมากเกินไป'\n* **มาจากไหน?:** คำนวณจากสัดส่วนของวันที่หุ้นขึ้นเทียบกับวันที่หุ้นลงในรอบ 14 วัน")
        st.divider()
        st.markdown(f"#### 3. ADX (Average Directional Index)\n* **ค่าปัจจุบัน:** `{adx_val:.2f}` -> {adx_interp}\n* **คืออะไร?:** เครื่องมือวัด 'ความรุนแรงของเทรนด์' (ไม่บอกทิศทาง บอกแค่ว่าแรงไหม)")
        st.divider()
        st.markdown(f"#### 4. Bollinger Bands (BB)\n* **Upper:** `{bb_upper:.2f}` | **Lower:** `{bb_lower:.2f}`\n* **คืออะไร?:** กรอบการแกว่งตัวของราคาเปรียบเหมือนขอบถนน")

# --- 5. Data Fetching (Pro Version - เพื่อรองรับฟีเจอร์ใหม่) ---
@st.cache_data(ttl=15, show_spinner=False)
def get_data_pro(symbol, main_tf, mtf_tf):
    try:
        ticker = yf.Ticker(symbol)
        
        # 1. Main Data
        period_val = "730d" if main_tf == "1h" else "10y"
        df = ticker.history(period=period_val, interval=main_tf)
        
        # 2. MTF Data (ข้อมูล Timeframe ใหญ่กว่า)
        df_mtf = ticker.history(period="2y", interval=mtf_tf)
        
        # 3. News (Sentiment Data)
        news = ticker.news
        
        # 4. Info
        info = ticker.info
        current_price = info.get('regularMarketPrice')
        if current_price is None and not df.empty:
            current_price = df['Close'].iloc[-1]

        stock_info = {
            'longName': info.get('longName', symbol),
            'currentPrice': current_price,
            'marketCap': info.get('marketCap', 'N/A'),
            'sector': info.get('sector', 'Unknown'),
            'pe': info.get('trailingPE', 0)
        }
        
        return df, df_mtf, news, stock_info
    except Exception as e:
        return None, None, None, None

# --- 6. Analysis Logic Modules (V2 - Pro Features) ---

# A. Volume Analysis
def analyze_volume(row, vol_ma):
    vol = row['Volume']
    if vol > vol_ma * 1.5: return "High Volume (มีนัยยะ)", "green"
    elif vol < vol_ma * 0.7: return "Low Volume (เบาบาง)", "red"
    else: return "Normal Volume (ปกติ)", "gray"

# C. Price Action (Candlestick Patterns)
def identify_candlestick(open, high, low, close, avg_body_size):
    body = abs(close - open)
    upper_wick = high - max(close, open)
    lower_wick = min(close, open) - low
    total_range = high - low
    
    if total_range == 0: return "Doji", "gray"
    
    # Hammer / Pinbar (Bullish)
    if lower_wick > body * 2 and upper_wick < body * 0.5:
        return "Hammer/Pin Bar (แรงซื้อสวน)", "green"
    # Shooting Star (Bearish)
    elif upper_wick > body * 2 and lower_wick < body * 0.5:
        return "Shooting Star (แรงขายกด)", "red"
    # Marubozu (Strong Trend)
    elif body > total_range * 0.8 and body > avg_body_size * 1.5:
        return "Big Candle (แรงมาก)", "green" if close > open else "red"
    # Doji (Indecision)
    elif body < total_range * 0.1:
        return "Doji (ลังเล)", "yellow"
        
    return "Normal Candle", "gray"

# E. Sentiment Analysis (Keyword Based)
def analyze_news_sentiment(news_list):
    if not news_list: return "No News", 0
    
    score = 0
    bullish_keywords = ['soar', 'jump', 'surge', 'beat', 'profit', 'growth', 'buy', 'upgrade', 'record', 'gain', 'strong']
    bearish_keywords = ['drop', 'fall', 'plunge', 'miss', 'loss', 'down', 'sell', 'downgrade', 'lawsuit', 'crash', 'weak']
    
    for item in news_list[:5]: # เช็ค 5 ข่าวล่าสุด
        title = item.get('title', '').lower()
        for word in bullish_keywords:
            if word in title: score += 1
        for word in bearish_keywords:
            if word in title: score -= 1
            
    if score >= 1: return "Positive (ข่าวดี)", score
    elif score <= -1: return "Negative (ข่าวร้าย)", score
    else: return "Neutral (ข่าวทรงๆ)", score

# --- 7. The SUPER AI Decision Engine (บูรณาการ Logic ใหม่และเก่า) ---
def ai_decision_engine(
    price, ema20, ema50, ema200, 
    rsi, macd_val, macd_sig, adx, 
    bb_up, bb_low, 
    vol_status, obv_slope, 
    mtf_trend, 
    candle_pattern, candle_color,
    atr_val
):
    # Initial Score
    score = 0
    reasons = []
    warnings = []
    strategy = "Wait & See"
    action_steps = []
    
    # 1. Trend Analysis (Weight: 40%) - ใช้ Logic เดิมของ V1 เป็นฐาน
    trend_state = "Sideway"
    if price > ema200 and price > ema50:
        if price > ema20: 
            trend_state = "Strong Uptrend"
            score += 3
            reasons.append("ราคายืนเหนือ EMA ทุกเส้น (Bullish Structure - V1 Logic)")
        else:
            trend_state = "Uptrend Pullback"
            score += 1
            reasons.append("เทรนด์หลักขาขึ้น แต่ระยะสั้นย่อตัว")
    elif price < ema200 and price < ema50:
        trend_state = "Downtrend"
        score -= 3
        reasons.append("ราคาอยู่ใต้ EMA ทุกเส้น (Bearish Structure)")
    
    # 2. MTF Confirmation (Weight: 20%) - ส่วนเพิ่มของ V2
    if mtf_trend == "Bullish":
        if score > 0: 
            score += 2
            reasons.append(f"Timeframe ใหญ่สนับสนุนขาขึ้น (MTF Confluence)")
        elif score < 0:
            warnings.append("Timeframe ใหญ่ขัดแย้ง (ระวังเด้งเพื่อลงต่อ)")
    elif mtf_trend == "Bearish":
        if score < 0:
            score -= 2
            reasons.append(f"Timeframe ใหญ่ยืนยันขาลง")
        elif score > 0:
            warnings.append("Timeframe ใหญ่เป็นขาลง (ระวัง Bull Trap)")
            score -= 1 # ลดคะแนนความมั่นใจ

    # 3. Momentum & Volume (Weight: 20%) - รวม V1 RSI/MACD กับ V2 Volume
    if rsi > 50 and macd_val > macd_sig:
        score += 1
        reasons.append("Momentum เป็นบวก (RSI>50, MACD Cross)")
    elif rsi < 50 and macd_val < macd_sig:
        score -= 1
        
    if "High Volume" in vol_status:
        if candle_color == "green": 
            score += 1
            reasons.append("Volume เข้าสนับสนุนการขึ้น (V2 Logic)")
        elif candle_color == "red":
            score -= 1
            reasons.append("Volume ขายออกมาเยอะมาก")
    
    if obv_slope > 0: reasons.append("OBV ชี้ขึ้น (เงินไหลเข้าสะสม)")
    
    # 4. Overbought/Oversold (V1) & Risk (Correction)
    if rsi > 75:
        score -= 1
        warnings.append(f"RSI สูงมาก ({rsi:.1f}) ระวังแรงเทขายทำกำไร")
    elif rsi < 25:
        score += 1
        warnings.append(f"RSI ต่ำมาก ({rsi:.1f}) อาจเกิด Technical Rebound")

    # --- Strategy Generator ---
    
    # Case A: Strong Buy
    if score >= 5:
        strategy = "🚀 STRONG BUY (Follow Trend)"
        action_steps.append("Trend แข็งแกร่ง + Volume ซัพพอร์ต")
        action_steps.append("เข้าซื้อได้เลย (Market Buy) หรือตั้งรับที่ EMA20")
        stop_loss = price - (2 * atr_val)
        take_profit = price + (4 * atr_val) # RR 1:2
        
    # Case B: Buy on Dip
    elif score >= 2 and trend_state == "Uptrend Pullback":
        strategy = "🛒 BUY ON DIP (ย่อซื้อสะสม)"
        action_steps.append("ราคาย่อตัวในขาขึ้น เป็นโอกาสสะสม")
        action_steps.append(f"รอแท่งเทียนกลับตัวเขียวแรก หรือรอ RSI ตัด 30 ขึ้นมา")
        stop_loss = price - (2 * atr_val)
        take_profit = price + (3 * atr_val)

    # Case C: Sell / Short
    elif score <= -4:
        strategy = "🔻 STRONG SELL / SHORT"
        action_steps.append("โครงสร้างราคาพังเสียหาย")
        action_steps.append("ห้ามรับมีดเด็ดขาด หาจังหวะเด้งเพื่อขาย")
        stop_loss = price + (2 * atr_val)
        take_profit = price - (3 * atr_val)
        
    # Case D: Rebound (High Risk)
    elif score <= -1 and rsi < 25:
        strategy = "⚡ OVERSOLD PLAY (เก็งกำไรสั้น)"
        action_steps.append("เล่นเด้งสั้นเท่านั้น (High Risk)")
        action_steps.append("เข้าเร็วออกเร็ว อย่าแช่นาน")
        stop_loss = price - (1.5 * atr_val)
        take_profit = price + (2 * atr_val)
        
    # Case E: Sideway
    else:
        strategy = "👀 WAIT & SEE (ทับมือ)"
        action_steps.append(f"ตลาดยังไม่เลือกทางชัดเจน ({trend_state})")
        action_steps.append(f"รอ Breakout กรอบ {bb_up:.2f} หรือ {bb_low:.2f}")
        stop_loss = price - atr_val
        take_profit = price + atr_val

    return {
        "score": score,
        "strategy": strategy,
        "reasons": reasons,
        "warnings": warnings,
        "action": action_steps,
        "sl": stop_loss,
        "tp": take_profit,
        "trend_state": trend_state
    }

# --- 8. Main Execution Loop ---
if submit_btn:
    st.divider()
    
    while True:
        with st.spinner(f"🤖 AI Ultimate กำลังบูรณาการข้อมูล (V1+V2) สำหรับ {symbol_input}..."):
            # 1. Fetch Data
            df, df_mtf, news, info = get_data_pro(symbol_input, tf_code, mtf_code)
        
        if df is None or df.empty or len(df) < 200:
            st.error("❌ ไม่พบข้อมูลหุ้น หรือข้อมูลไม่เพียงพอสำหรับการวิเคราะห์ขั้นสูง (ต้องมี Data > 200 แท่ง)")
            break
        else:
            # 2. Calculate Indicators (รวมของ V1 และ V2)
            # Main Timeframe
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # --- FIX: Explicitly name the ATR column (ป้องกัน KeyError) ---
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            # -------------------------------------------
            
            macd = ta.macd(df['Close'])
            df = pd.concat([df, macd], axis=1)
            
            bb = ta.bbands(df['Close'], length=20, std=2)
            df = pd.concat([df, bb], axis=1)
            
            adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            df = pd.concat([df, adx], axis=1)
            
            # Volume Indicators (V2)
            df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
            df['OBV'] = ta.obv(df['Close'], df['Volume'])
            
            # MTF Calculation (V2)
            mtf_trend = "Sideway"
            if df_mtf is not None and not df_mtf.empty and len(df_mtf) > 50:
                df_mtf['EMA50'] = ta.ema(df_mtf['Close'], length=50)
                last_mtf = df_mtf.iloc[-1]
                if last_mtf['Close'] > last_mtf['EMA50']: mtf_trend = "Bullish"
                elif last_mtf['Close'] < last_mtf['EMA50']: mtf_trend = "Bearish"

            # 3. Extract Latest Data
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            price = info['currentPrice']
            rsi = last['RSI']
            
            # --- FIX: Access using the correct column name ---
            atr = last['ATR'] 
            # -------------------------------------------------
            
            # Extract MACD/ADX/BB safely
            macd_val = last.get('MACD_12_26_9', 0)
            macd_sig = last.get('MACDs_12_26_9', 0)
            adx_val = last.get('ADX_14', 0)
            bb_up = last.get('BBU_20_2.0', price * 1.05)
            bb_low = last.get('BBL_20_2.0', price * 0.95)
            
            # 4. Specific Analysis Calls
            vol_status, vol_color = analyze_volume(last, last['Vol_SMA20'])
            candle_pattern, candle_color = identify_candlestick(last['Open'], last['High'], last['Low'], last['Close'], atr)
            news_sentiment, news_score = analyze_news_sentiment(news)
            
            try: obv_slope = last['OBV'] - df['OBV'].iloc[-5] 
            except: obv_slope = 0

            # 5. Run AI Engine (V2 Logic with V1 Inputs)
            ai_result = ai_decision_engine(
                price, last['EMA20'], last['EMA50'], last['EMA200'],
                rsi, macd_val, macd_sig, adx_val,
                bb_up, bb_low,
                vol_status, obv_slope,
                mtf_trend,
                candle_pattern, candle_color,
                atr
            )

            # --- DISPLAY SECTION (บูรณาการ UI ของ V1 และ V2) ---
            
            # Header (V2 Style - สะอาดกว่า)
            logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
            st.markdown(f"""
            <div style="display:flex; justify-content:center; align-items:center; gap:15px; margin-bottom: 20px;">
                <img src="{logo_url}" onerror="this.style.display='none'" style="height:60px; border-radius:50%; border:2px solid #eee;">
                <div>
                    <h1 style="margin:0; text-align:left;">{symbol_input}</h1>
                    <span style="font-size:1.2rem; color:gray;">{info['longName']} | Sector: {info['sector']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Metrics (V2 + Custom HTML)
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(custom_metric_html("💰 Price", f"{price:.2f}", f"EMA20: {last['EMA20']:.2f}", "green" if price > last['EMA20'] else "red", ""), unsafe_allow_html=True)
            with m2:
                st.markdown(custom_metric_html("📊 Volume", vol_status.split(" ")[0], vol_status.split("(")[1].replace(")",""), vol_color, ""), unsafe_allow_html=True)
            with m3:
                st.markdown(custom_metric_html("🕯️ Pattern", candle_pattern.split(" ")[0], candle_pattern.split("(")[1].replace(")","") if "(" in candle_pattern else "", candle_color, ""), unsafe_allow_html=True)
            with m4:
                sent_color = "green" if news_score > 0 else "red" if news_score < 0 else "gray"
                st.markdown(custom_metric_html("📰 Sentiment", news_sentiment.split(" ")[0], f"Score: {news_score}", sent_color, ""), unsafe_allow_html=True)

            # Strategy Banner (V2)
            st.markdown("---")
            strat_color = "success" if ai_result['score'] > 2 else "error" if ai_result['score'] < -2 else "warning"
            if strat_color == "success": st.success(f"## {ai_result['strategy']}")
            elif strat_color == "error": st.error(f"## {ai_result['strategy']}")
            else: st.warning(f"## {ai_result['strategy']}")
            
            # --- INTEGRATED ANALYSIS SECTION (The Best Part) ---
            c_left, c_right = st.columns([1.5, 2])
            
            with c_left:
                # 1. Risk Management (V2 Feature)
                st.subheader("📉 Risk Management (ATR Based)")
                st.info(f"""
                **🎯 แผนการเทรด (Trade Setup):**
                * **Entry:** {price:.2f}
                * **🛑 Stop Loss:** **{ai_result['sl']:.2f}** (ระยะ {price - ai_result['sl']:.2f})
                * **✅ Take Profit:** **{ai_result['tp']:.2f}** (Reward Ratio 1:{abs(ai_result['tp']-price)/abs(price-ai_result['sl']):.1f})
                """)
                
                # 2. Key Levels (V1 Feature - ดึงกลับมา)
                st.subheader("🚧 Key Levels (Smart Filter)")
                potential_levels = [
                    (last['EMA20'], "EMA 20"), (last['EMA50'], "EMA 50"), (last['EMA200'], "EMA 200"),
                    (bb_low, "BB Lower"), (bb_up, "BB Upper"),
                    (df['High'].tail(60).max(), "High 60D"), (df['Low'].tail(60).min(), "Low 60D")
                ]
                # Filter Logic
                supports = sorted([x for x in potential_levels if x[0] < price], key=lambda x: x[0], reverse=True)[:3]
                resistances = sorted([x for x in potential_levels if x[0] > price], key=lambda x: x[0])[:2]
                
                st.markdown("#### 🟢 แนวรับ (Supports)")
                for v, d in supports: st.write(f"- **{v:.2f}** : {d}")
                st.markdown("#### 🔴 แนวต้าน (Resistances)")
                for v, d in resistances: st.write(f"- **{v:.2f}** : {d}")

            with c_right:
                # 1. AI Logic & Reasons (V2 Feature)
                st.subheader("🧠 AI Analysis & Reasoning")
                if ai_result['reasons']:
                    st.markdown("**✅ ปัจจัยสนับสนุน (Pros):**")
                    for r in ai_result['reasons']: st.markdown(f"- {r}")
                if ai_result['warnings']:
                    st.markdown("**⚠️ ปัจจัยเสี่ยง (Cons/Risks):**")
                    for w in ai_result['warnings']: st.markdown(f"- {w}")
                
                st.markdown("---")
                
                # 2. Detailed Explanation (V1 Feature - ดึงกลับมาใส่เพื่อให้ข้อมูลแน่นปึ้ก)
                exp_adx, exp_rsi, exp_macd = get_detailed_explanation(adx_val, rsi, macd_val, macd_sig, price, last['EMA200'])
                st.subheader("🧐 คำอธิบายเชิงลึก (Deep Dive)")
                with st.container():
                    st.info(f"💪 **ADX:** {exp_adx}")
                    st.info(f"⚡ **RSI:** {exp_rsi}")
                    st.info(f"🌊 **MACD:** {exp_macd}")

            # News Expander (V2)
            with st.expander("📰 อ่านหัวข้อข่าวที่ AI ใช้ประเมิน (News Source)", expanded=False):
                if news:
                    for n in news[:5]:
                        try:
                            link = n.get('link', '#')
                            title = n.get('title', 'No Title')
                            st.write(f"- [{title}]({link})")
                        except: pass
                else: st.write("- ไม่มีข้อมูลข่าวล่าสุด")

            st.divider()
            
            # --- Learning Section (V1 Feature - ดึงกลับมาไว้ล่างสุด) ---
            # ใช้ฟังก์ชันเดิมจาก V1 เพื่อแสดงความรู้
            rsi_interp_str = get_rsi_interpretation(rsi)
            adx_interp_str = get_adx_interpretation(adx_val)
            macd_interp_str = "🟢 แรงซื้อนำ" if macd_val > macd_sig else "🔴 แรงขายนำ"
            display_learning_section(rsi, rsi_interp_str, macd_val, macd_sig, macd_interp_str, adx_val, adx_interp_str, price, bb_up, bb_low)

            st.markdown("<div class='disclaimer-box'>⚠️ <b>Disclaimer:</b> ระบบ Ultimate นี้บูรณาการข้อมูลเทคนิค (V1) และ AI Decision Tree ขั้นสูง (V2) เพื่อประมวลผลข้อมูล 5 มิติ (Price, Vol, Timeframe, Risk, Sentiment) แต่การลงทุนยังมีความเสี่ยง โปรดใช้ Money Management อย่างเคร่งครัด</div>", unsafe_allow_html=True)

        if not realtime_mode: break
        time.sleep(10)
        st.rerun()
