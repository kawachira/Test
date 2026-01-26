import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master (Debug Mode)", page_icon="🔧", layout="wide")

# --- 2. CSS ปรับแต่ง ---
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
    .score-box {
        background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #ddd;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>🔧 Ai Debugger<br><span style='font-size: 1.5rem; opacity: 0.7;'>ตรวจสอบระบบ Multi-Frame</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น MSFT, TSLA)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            # Logic Map
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
            else: tf_code = "1d"; mtf_code = "1wk"
        
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ (พร้อมโชว์ไส้ใน)")

# --- Helper Functions (ลดรูป) ---
def format_volume(vol):
    if vol >= 1_000_000_000: return f"{vol/1_000_000_000:.2f}B"
    if vol >= 1_000_000: return f"{vol/1_000_000:.2f}M"
    return f"{vol:,.0f}"

# --- Data Fetching ---
@st.cache_data(ttl=1, show_spinner=False) # ลด TTL เพื่อ Debug
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        
        # Optimize Period
        if interval == "1wk": period_val = "10y"
        elif interval == "1d": period_val = "5y" 
        else: period_val = "730d"

        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="5y", interval=mtf_interval) # MTF Always 5y
        news = ticker.news
        
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'regularMarketPrice': ticker.info.get('regularMarketPrice'),
            'regularMarketChangePercent': ticker.info.get('regularMarketChangePercent')
        }
        # Fallback price
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             
        return df, stock_info, df_mtf, news
    except:
        return None, None, None, None

# --- Analysis Logic ---
def ai_hybrid_analysis(price, ema20, ema200, macd_val, macd_sig, vol_status, mtf_trend, rsi, atr_val):
    score = 0
    debug_log = [] # เก็บประวัติการให้คะแนน
    
    # 1. Trend (Day)
    if not np.isnan(ema200):
        if price > ema200:
            score += 3
            debug_log.append(f"✅ Trend (Day): ราคา > EMA200 (+3 คะแนน) | {price:.2f} > {ema200:.2f}")
            if not np.isnan(ema20) and price > ema20:
                score += 1
                debug_log.append(f"✅ Short-Term: ราคา > EMA20 (+1 คะแนน) | {price:.2f} > {ema20:.2f}")
        else:
            score -= 3
            debug_log.append(f"❌ Trend (Day): ราคา < EMA200 (-3 คะแนน) | {price:.2f} < {ema200:.2f}")
    else:
        debug_log.append(f"⚠️ Trend (Day): EMA200 หาค่าไม่ได้ (NaN) (0 คะแนน)")

    # 2. Momentum
    if macd_val > macd_sig:
        score += 1
        debug_log.append("✅ MACD: ตัดขึ้น (+1 คะแนน)")
    else:
        score -= 1
        debug_log.append("❌ MACD: ตัดลง (-1 คะแนน)")

    # 3. MTF (Week) - จุดสำคัญ!
    if mtf_trend == "Bullish":
        score += 2
        debug_log.append(f"✅ MTF ({mtf_code.upper()}): เป็นขาขึ้น (+2 คะแนน)")
    elif mtf_trend == "Bearish":
        score -= 2
        debug_log.append(f"❌ MTF ({mtf_code.upper()}): เป็นขาลง (-2 คะแนน)")
    else:
        debug_log.append(f"⚠️ MTF ({mtf_code.upper()}): Sideway/Unknown (0 คะแนน)")

    return score, debug_log

# --- Display Execution ---
if submit_btn:
    st.divider()
    
    with st.spinner(f"กำลังเจาะระบบ {symbol_input}..."):
        df, info, df_mtf, news = get_data_hybrid(symbol_input, tf_code, mtf_code)

    if df is not None and not df.empty and len(df) > 10:
        # --- Calculations ---
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)

        # Last Values
        last = df.iloc[-1]
        price = info['regularMarketPrice']
        ema20 = last['EMA20']
        ema200 = last['EMA200']
        try: macd_val, macd_sig = last['MACD_12_26_9'], last['MACDs_12_26_9']
        except: macd_val, macd_sig = 0, 0
        rsi = last['RSI']
        
        # Volume
        vol_status = "Normal"
        if last['Volume'] > last['Vol_SMA20'] * 1.5: vol_status = "High Volume"
        elif last['Volume'] < last['Vol_SMA20'] * 0.7: vol_status = "Low Volume"

        # --- MTF Calculation (Week) ---
        mtf_trend = "Sideway"
        mtf_debug_val = 0
        mtf_last_price = 0
        
        if df_mtf is not None and not df_mtf.empty:
            df_mtf['EMA50'] = ta.ema(df_mtf['Close'], length=50) # ใช้ EMA 50 Week เป็นเกณฑ์
            if len(df_mtf) > 50 and not pd.isna(df_mtf['EMA50'].iloc[-1]):
                mtf_val = df_mtf['EMA50'].iloc[-1]
                mtf_price = df_mtf['Close'].iloc[-1]
                mtf_debug_val = mtf_val
                mtf_last_price = mtf_price
                
                if mtf_price > mtf_val: mtf_trend = "Bullish"
                else: mtf_trend = "Bearish"
            else:
                mtf_trend = "Unknown (Data Error)"

        # --- AI Processing ---
        final_score, score_log = ai_hybrid_analysis(price, ema20, ema200, macd_val, macd_sig, vol_status, mtf_trend, rsi, last['ATR'])

        # ==========================================
        # 🕵️‍♂️ ส่วนแสดงผล DEBUG (สำคัญมาก!)
        # ==========================================
        st.subheader(f"📊 {info['longName']} ({symbol_input})")
        st.write(f"**ราคาปัจจุบัน:** {price:.2f}")
        
        c_debug1, c_debug2 = st.columns(2)
        
        with c_debug1:
            st.markdown("### 🧮 ตารางคะแนน (Scoreboard)")
            st.markdown(f"<div class='score-box'><b>Final Score: {final_score}</b></div>", unsafe_allow_html=True)
            for log in score_log:
                st.write(log)
                
        with c_debug2:
            st.markdown("### 🔍 ตรวจสอบค่าเทคนิค (Raw Values)")
            st.markdown(f"**1. Timeframe หลัก ({tf_code}):**")
            st.code(f"""
            Price:   {price:.2f}
            EMA 200: {ema200:.2f}  <-- เช็คตรงนี้ว่าเป็น NaN ไหม
            EMA 20:  {ema20:.2f}
            MACD:    {macd_val:.4f}
            """)
            
            st.markdown(f"**2. Multi-Timeframe ({mtf_code}):**")
            st.code(f"""
            MTF Trend: {mtf_trend}
            MTF Price: {mtf_last_price:.2f}
            MTF EMA50: {mtf_debug_val:.2f}
            """)

        st.divider()
        
        # --- Strategy Display (เหมือนเดิม) ---
        if final_score >= 6: status = "🚀 Super Nova"; color="green"
        elif final_score >= 4: status = "🐂 Strong Bullish"; color="green"
        elif final_score >= 2: status = "📈 Moderate Bullish"; color="green"
        elif final_score >= -1: status = "⚖️ Neutral"; color="orange"
        elif final_score >= -3: status = "☁️ Weak Warning"; color="orange"
        elif final_score >= -5: status = "🐻 Strong Bearish"; color="red"
        else: status = "🩸 Extreme Crash"; color="red"

        st.markdown(f"### 🤖 บทสรุป AI: **:{color}[{status}]**")
        
    else:
        st.error(f"❌ ไม่สามารถดึงข้อมูล {symbol_input} ได้ (Data Fetch Error)")
        st.write("สาเหตุที่เป็นไปได้: ชื่อหุ้นผิด, ตลาดปิด, หรือ Yahoo Finance บล็อกชั่วคราว")
