import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import os
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master (Pro Journal)", page_icon="💎", layout="wide")

# --- 2. Initialize Session State ---
if 'analyzed_data' not in st.session_state:
    st.session_state['analyzed_data'] = None

# --- 3. CSV Handling (ระบบบันทึกไฟล์) ---
CSV_FILE = 'trading_journal.csv'

def load_journal():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=["Date", "Time", "Symbol", "Price", "Score", "Strategy", "Note"])

def save_to_journal(data_dict):
    df = load_journal()
    # สร้าง DataFrame จากข้อมูลใหม่
    new_row = pd.DataFrame([data_dict])
    # รวมร่าง (concat)
    df = pd.concat([new_row, df], ignore_index=True)
    # บันทึกลงไฟล์
    df.to_csv(CSV_FILE, index=False)
    return df

# --- 4. CSS Styles ---
st.markdown("""
    <style>
    body { overflow-x: hidden; }
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
    h1 { text-align: center; font-size: 2.5rem !important; margin-bottom: 0px !important; }
    div[data-testid="stForm"] {
        border: none; padding: 20px; border-radius: 15px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 10px; font-weight: bold; padding: 10px 0;
    }
    .save-btn { text-align: center; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. Header ---
st.markdown("<h1>💎 Ai Stock Master <br><span style='font-size: 1.2rem; opacity: 0.7;'>Hybrid Sniper + Trading Journal 📓</span></h1>", unsafe_allow_html=True)

# --- 6. Helper Functions ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:bold'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:bold'>▼</span>"

def format_volume(vol):
    if vol >= 1_000_000_000: return f"{vol/1_000_000_000:.2f}B"
    if vol >= 1_000_000: return f"{vol/1_000_000:.2f}M"
    if vol >= 1_000: return f"{vol/1_000:.2f}K"
    return f"{vol:,.0f}"

def get_rsi_interpretation(rsi):
    if np.isnan(rsi): return "N/A"
    if rsi >= 70: return "Overbought (ระวังแรงขาย)"
    elif rsi >= 55: return "Bullish (กระทิงแข็งแกร่ง)"
    elif rsi >= 45: return "Sideway (รอเลือกทาง)"
    elif rsi >= 30: return "Bearish (หมีครองตลาด)"
    else: return "Oversold (ระวังเด้งสวน)"

def get_adx_interpretation(adx, is_uptrend):
    if np.isnan(adx): return "N/A"
    trend_str = "ขาขึ้น" if is_uptrend else "ขาลง"
    if adx >= 50: return f"Super Strong {trend_str}"
    if adx >= 25: return f"Strong {trend_str}"
    if adx >= 20: return "Developing Trend"
    return "Weak Trend"

# --- 7. Data & Logic ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "5y" if interval == "1d" else "730d"
        if interval == "1wk": period_val = "10y"
        
        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval)
        
        try: raw_info = ticker.info 
        except: raw_info = {} 

        # คำนวณราคาปัจจุบันให้แม่นยำที่สุดจาก history
        current_price = df['Close'].iloc[-1] if not df.empty else 0
        prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
        
        stock_info = {
            'longName': raw_info.get('longName', symbol),
            'marketState': raw_info.get('marketState', 'REGULAR'), 
            'trailingPE': raw_info.get('trailingPE', None),
            'price': current_price,
            'change': current_price - prev_price,
            'change_pct': ((current_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0
        }
        return df, stock_info, df_mtf
    except:
        return None, None, None

def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, vol_status, atr_val):
    score = 0
    bullish_factors = []
    bearish_factors = []
    
    # 1. Trend
    if not np.isnan(ema200):
        if price > ema200:
            score += 3
            bullish_factors.append("ราคา > EMA 200 (เทรนด์หลักขาขึ้น)")
            if price > ema20: score += 1; bullish_factors.append("ราคา > EMA 20 (แข็งแกร่ง)")
            else: bearish_factors.append("ราคาหลุด EMA 20 (พักตัว)")
        else:
            score -= 3
            bearish_factors.append("ราคา < EMA 200 (เทรนด์หลักขาลง)")
            
    # 2. Momentum
    if macd_val > macd_sig: score += 1; bullish_factors.append("MACD ตัดขึ้น")
    else: score -= 1; bearish_factors.append("MACD ตัดลง")
    
    # 3. Volume
    if "High" in vol_status:
        if price > ema20: score += 1; bullish_factors.append("Volume ซื้อสนับสนุน")
        else: score -= 1; bearish_factors.append("Volume ขายกดดัน")
        
    # Status Decision
    if score >= 6: status, color, action = "Super Bullish", "green", "Aggressive Buy"
    elif score >= 4: status, color, action = "Strong Bullish", "green", "Buy / Hold"
    elif score >= 2: status, color, action = "Moderate Bullish", "green", "Buy on Dip"
    elif score >= -1: status, color, action = "Neutral", "yellow", "Wait & See"
    elif score >= -3: status, color, action = "Weak Bearish", "orange", "Wait / Defensive"
    else: status, color, action = "Strong Bearish", "red", "Avoid / Cut Loss"
    
    return {"score": score, "status": status, "color": color, "action": action, "bulls": bullish_factors, "bears": bearish_factors}

# --- 8. UI Layout ---
c_search, c_space = st.columns([2, 1])
with c_search:
    with st.form(key='search_form'):
        c1, c2 = st.columns([3, 1])
        with c1: symbol_input = st.text_input("ชื่อหุ้น (เช่น TSLA, BTC-USD)", value="").upper().strip()
        with c2: timeframe = st.selectbox("TF:", ["1h", "1d", "1wk"], index=1)
        submitted = st.form_submit_button("🚀 วิเคราะห์ (Analyze)")

# --- 9. Logic Execution ---
if submitted and symbol_input:
    with st.spinner("AI กำลังทำงาน..."):
        # Mapping MTF
        mtf_code = "1d" if timeframe == "1h" else ("1mo" if timeframe == "1wk" else "1wk")
        df, info, df_mtf = get_data_hybrid(symbol_input, timeframe, mtf_code)
        
        if df is not None and len(df) > 50:
            # Calc Indicators
            df['EMA20'] = ta.ema(df['Close'], 20)
            df['EMA50'] = ta.ema(df['Close'], 50)
            df['EMA200'] = ta.ema(df['Close'], 200)
            df['RSI'] = ta.rsi(df['Close'], 14)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], 14)
            macd = ta.macd(df['Close'])
            df = pd.concat([df, macd], axis=1)
            adx = ta.adx(df['High'], df['Low'], df['Close'], 14)
            df = pd.concat([df, adx], axis=1)
            df['Vol_SMA'] = ta.sma(df['Volume'], 20)
            
            # Get Last Row
            last = df.iloc[-1]
            price = info['price']
            
            # Volume Logic
            vol_now = last['Volume']
            vol_ma = last['Vol_SMA'] if not np.isnan(last['Vol_SMA']) else vol_now
            if vol_now > vol_ma * 1.5: vol_stat = "High Volume"
            elif vol_now < vol_ma * 0.7: vol_stat = "Low Volume"
            else: vol_stat = "Normal"
            
            # AI Logic
            res = ai_hybrid_analysis(price, last['EMA20'], last['EMA50'], last['EMA200'], 
                                     last['RSI'], last['MACD_12_26_9'], last['MACDs_12_26_9'], 
                                     vol_stat, last['ATR'])
            
            # Save to Session State (เพื่อให้ข้อมูลค้างหน้าจอ)
            st.session_state['analyzed_data'] = {
                "symbol": symbol_input,
                "info": info,
                "last": last,
                "res": res,
                "timeframe": timeframe
            }
        else:
            st.error("ไม่พบข้อมูลหุ้น")

# --- 10. Display Result (จาก Session State) ---
if st.session_state['analyzed_data']:
    data = st.session_state['analyzed_data']
    info = data['info']
    last = data['last']
    res = data['res']
    
    st.divider()
    
    # 1. Price Header
    col_head, col_score = st.columns([1.5, 2])
    with col_head:
        st.markdown(f"## {data['symbol']} ({data['timeframe']})")
        val_color = "#16a34a" if info['change'] >= 0 else "#dc2626"
        st.markdown(f"<h1 style='margin:0;'>{info['price']:,.2f}</h1>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:{val_color}; font-size:1.2rem; font-weight:bold'>{info['change']:+.2f} ({info['change_pct']:.2f}%)</span>", unsafe_allow_html=True)
        
    with col_score:
        # AI Banner
        bg_color = {"green": "#dcfce7", "yellow": "#fef9c3", "orange": "#ffedd5", "red": "#fee2e2"}
        text_color = {"green": "#14532d", "yellow": "#713f12", "orange": "#7c2d12", "red": "#7f1d1d"}
        c_bg = bg_color.get(res['color'], "#f3f4f6")
        c_txt = text_color.get(res['color'], "#1f2937")
        
        st.markdown(f"""
        <div style="background-color:{c_bg}; padding:15px; border-radius:10px; border-left: 5px solid {res['color']};">
            <h3 style="color:{c_txt}; margin:0;">{res['status']}</h3>
            <p style="color:{c_txt}; margin:5px 0 0 0; font-weight:bold;">🎯 Action: {res['action']}</p>
        </div>
        """, unsafe_allow_html=True)

    # 2. Indicators & Save Button
    c_left, c_right = st.columns([1, 1])
    
    with c_left:
        st.subheader("📊 Indicators")
        atr_pct = (last['ATR'] / info['price']) * 100 if info['price'] > 0 else 0
        st.markdown(f"""
        - **RSI:** {last['RSI']:.2f} ({get_rsi_interpretation(last['RSI'])})
        - **MACD:** {last['MACD_12_26_9']:.3f}
        - **ATR:** {last['ATR']:.2f} (**{atr_pct:.1f}%**)
        - **Volume:** {vol_stat}
        """)
        
    with c_right:
        st.subheader("🧠 AI Logic")
        for b in res['bulls']: st.markdown(f"✅ {b}")
        for b in res['bears']: st.markdown(f"❌ {b}")

    # --- 🔥 SAVE BUTTON SECTION ---
    st.write("---")
    c_btn1, c_btn2 = st.columns([1, 3])
    with c_btn1:
        # ปุ่มบันทึก - กดแล้วบันทึกลง CSV ทันที
        if st.button("💾 บันทึกผลลงสมุด (Save Journal)"):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            record = {
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Time": datetime.now().strftime("%H:%M"),
                "Symbol": data['symbol'],
                "Price": round(info['price'], 2),
                "Score": res['status'],  # เก็บเป็นสถานะ (เช่น Strong Bullish)
                "Strategy": res['action'],
                "Note": f"RSI:{last['RSI']:.0f} | ATR:{atr_pct:.1f}%"
            }
            save_to_journal(record)
            st.success("✅ บันทึกเรียบร้อย! (เลื่อนลงเพื่อดูประวัติ)")
            time.sleep(1) # ให้ user เห็นข้อความก่อนรีเฟรช
            st.rerun()

# --- 11. Journal Display (Persistent) ---
st.divider()
st.subheader("📓 สมุดจดการเทรด (Trading Journal)")
st.caption("ข้อมูลนี้ถูกบันทึกในไฟล์ 'trading_journal.csv' ในเครื่องของคุณ")

journal_df = load_journal()
if not journal_df.empty:
    # โชว์ข้อมูลล่าสุดขึ้นบนสุด
    st.dataframe(journal_df.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มีข้อมูลในสมุดจด ลองวิเคราะห์หุ้นแล้วกดปุ่ม 'บันทึก' ดูสิ!")
