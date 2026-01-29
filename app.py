import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ (คงเดิม 100%) ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- Initialize Session State for History ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = []

# --- 2. CSS ปรับแต่ง (คงเดิม 100% + X-Ray) ---
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
        margin-top: 20px; margin-bottom: 20px; padding: 20px;
        background-color: #fff8e1; border: 2px solid #ffc107;
        border-radius: 12px; font-size: 1rem; color: #5d4037;
        text-align: center; font-weight: 500;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    /* X-Ray Box Style */
    .xray-box {
        background-color: #f0f9ff;
        border: 1px solid #bae6fd;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .xray-title {
        font-weight: bold;
        color: #0369a1;
        font-size: 1.1rem;
        margin-bottom: 10px;
        border-bottom: 1px solid #e0f2fe;
        padding-bottom: 5px;
    }
    .xray-item {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 0.95rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ (คงเดิม 100%) ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ (Hybrid Sniper)🪐</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา (คงเดิม 100%) ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB,TSLA)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
            else: tf_code = "1d"; mtf_code = "1wk"
        
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Helper Functions ---

def analyze_candlestick(open_price, high, low, close):
    """ฟังก์ชันอ่านแท่งเทียน (Tuned Sensitivity)"""
    body = abs(close - open_price)
    wick_upper = high - max(close, open_price)
    wick_lower = min(close, open_price) - low
    total_range = high - low
    
    color = "🟢 เขียว (Buying)" if close >= open_price else "🔴 แดง (Selling)"
    if total_range == 0: return "Doji (N/A)", color, "N/A", False

    pattern_name = "Normal Candle (ปกติ)"
    detail = "แรงซื้อขายสมดุล"
    is_big = False

    if wick_lower > (body * 2) and wick_upper < body:
        pattern_name = "Hammer/Pinbar (ค้อน)"
        detail = "มีการปฏิเสธราคาต่ำ (แรงซื้อสวนกลับดันราคาขึ้น)"
    elif wick_upper > (body * 2) and wick_lower < body:
        pattern_name = "Shooting Star (ดาวตก)"
        detail = "มีการปฏิเสธราคาสูง (โดนตบหัวทิ่ม/แรงขายกดดัน)"
    # [TUNED]: ปรับเกณฑ์ Big Candle เป็น 0.6 (60%) ให้จับสัญญาณได้ไวขึ้น
    elif body > (total_range * 0.6): 
        is_big = True
        if close > open_price: 
            pattern_name = "Big Bullish Candle (แท่งเขียวตัน)"
            detail = "แรงซื้อคุมตลาดเบ็ดเสร็จ (Strong Momentum)"
        else: 
            pattern_name = "Big Bearish Candle (แท่งแดงตัน)"
            detail = "แรงขายคุมตลาดเบ็ดเสร็จ (Panic Sell)"
    elif body < (total_range * 0.1):
        pattern_name = "Doji (โดจิ)"
        detail = "ตลาดเกิดความลังเล (Indecision) รอเลือกทาง"
        
    return pattern_name, color, detail, is_big

def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def format_volume(vol):
    if vol >= 1_000_000_000: return f"{vol/1_000_000_000:.2f}B"
    if vol >= 1_000_000: return f"{vol/1_000_000:.2f}M"
    if vol >= 1_000: return f"{vol/1_000:.2f}K"
    return f"{vol:,.0f}"

def custom_metric_html(label, value, status_text, color_status, icon_svg):
    if color_status == "green": color_code = "#16a34a"
    elif color_status == "red": color_code = "#dc2626"
    else: color_code = "#a3a3a3"
    
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
    if np.isnan(rsi): return "N/A"
    if rsi >= 70: return "Overbought (ระวังแรงขาย)"
    elif rsi >= 55: return "Bullish (กระทิงแข็งแกร่ง)"
    elif rsi >= 45: return "Sideway/Neutral (รอเลือกทาง)"
    elif rsi >= 30: return "Bearish (หมีครองตลาด)"
    else: return "Oversold (ระวังเด้งสวน)"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "N/A"
    if pe is None: return "N/A"
    if pe < 0: return "ขาดทุน (Loss)"
    if pe < 15: return "หุ้นถูก (Value)"
    if pe < 30: return "ราคาเหมาะสม (Fair)"
    return "หุ้นแพง (Growth)"

def get_adx_interpretation(adx, is_uptrend):
    if np.isnan(adx): return "N/A"
    trend_str = "ขาขึ้น" if is_uptrend else "ขาลง"
    if adx >= 50: return f"Super Strong {trend_str} (แรงมาก)"
    if adx >= 25: return f"Strong {trend_str} (แข็งแกร่ง)"
    if adx >= 20: return "Developing Trend (เริ่มก่อตัว)"
    return "Weak/Sideway (ตลาดไร้ทิศทาง)"

def get_detailed_explanation(adx, rsi, macd_val, macd_signal, price, ema200):
    if np.isnan(ema200): is_uptrend = True; trend_context = "ไม่สามารถยืนยันเทรนด์ได้"
    else: is_uptrend = price > ema200
    is_bullish_momentum = macd_val > macd_signal
    if not np.isnan(ema200):
        if is_uptrend and is_bullish_momentum: trend_context = "ขาขึ้นเต็มตัว (Uptrend) + แรงส่งดี"
        elif is_uptrend and not is_bullish_momentum: trend_context = "ขาขึ้น (Uptrend) ระยะสั้นพักตัว"
        elif not is_uptrend and not is_bullish_momentum: trend_context = "ขาลงเต็มตัว (Downtrend) + แรงขายกดดัน"
        else: trend_context = "ขาลง (Downtrend) เริ่มมีการเด้ง (Rebound)"
    if np.isnan(adx): adx_explain = "⚠️ **ADX:** N/A"
    elif adx >= 25: adx_explain = f"💪 **Trend Strength:** ตลาดมีเทรนด์ที่แข็งแกร่ง ({trend_context})"
    else: adx_explain = f"😴 **Trend Strength:** ตลาดไร้ทิศทาง (Sideway) หรือกำลังฟอร์มตัว"
    if is_bullish_momentum: macd_explain = "🟢 **MACD:** โมเมนตัมเป็นบวก (กระทิงคุม)"
    else: macd_explain = "🔴 **MACD:** โมเมนตัมเป็นลบ (หมีคุม)"
    return adx_explain, "RSI Info", macd_explain, trend_context

def display_learning_section(rsi, rsi_interp, macd_val, macd_signal, macd_interp, adx_val, price, ema200, bb_upper, bb_lower):
    is_up = price >= ema200 if not np.isnan(ema200) else True
    adx_interp = get_adx_interpretation(adx_val, is_up)
    st.markdown("### 📘 มุมความรู้: ค่าต่างๆ คืออะไร?")
    with st.expander("คลิกเพื่อเรียนรู้ความหมายของอินดิเคเตอร์แต่ละตัว", expanded=False):
        st.markdown(f"#### 1. MACD\n* **ค่าปัจจุบัน:** `{macd_val:.3f}` -> {macd_interp}")
        st.markdown("* ดูโมเมนตัม: เส้น MACD ตัด Signal Line ขึ้น = ซื้อ, ตัดลง = ขาย")
        st.divider()
        st.markdown(f"#### 2. RSI\n* **ค่าปัจจุบัน:** `{rsi:.2f}` -> {rsi_interp}")
        st.markdown("* ดูความถูกแพง: >70 แพงไป (ระวังขาย), <30 ถูกไป (ระวังเด้ง)")
        st.divider()
        st.markdown(f"#### 3. ADX\n* **ค่าปัจจุบัน:** `{adx_val:.2f}` -> {adx_interp}")
        st.markdown("* ดูความแรงเทรนด์: >25 มีเทรนด์ชัด, <20 ไซด์เวย์")

def filter_levels(levels, threshold_pct=0.025):
    selected = []
    for val, label in levels:
        if np.isnan(val): continue
        label = label.replace("BB Lower (Volatility)", "BB Lower (กรอบล่าง)").replace("Low 60 Days (Price Action)", "Low 60 วัน (ฐานราคา)").replace("EMA 200 (Trend Wall)", "EMA 200 (เทรนด์หลัก)").replace("EMA 50 (Short Trend)", "EMA 50 (ระยะกลาง)").replace("EMA 20 (Momentum)", "EMA 20 (โมเมนตัม)").replace("BB Upper (Ceiling)", "BB Upper (ต้านใหญ่)").replace("High 60 Days (Peak)", "High 60 วัน (ยอดดอย)")
        if "MTF" in label or "1wk" in label.lower() or "1mo" in label.lower(): label = "EMA 200 (TF ใหญ่)"
        if not selected: selected.append((val, label))
        else:
            last_val = selected[-1][0]; diff = abs(val - last_val) / last_val
            if diff > threshold_pct: selected.append((val, label))
    return selected

# --- 5. Data Fetching (คงเดิม 100%) ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        if interval == "1wk": period_val = "10y"
        elif interval == "1d": period_val = "5y"
        else: period_val = "730d"
        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval)
        try: raw_info = ticker.info 
        except: raw_info = {} 
        stock_info = {
            'longName': raw_info.get('longName', symbol), 'marketState': raw_info.get('marketState', 'REGULAR'), 'trailingPE': raw_info.get('trailingPE', None), 'sector': raw_info.get('sector', 'Unknown'),
            'regularMarketPrice': df['Close'].iloc[-1] if not df.empty else None, 'regularMarketChange': (df['Close'].iloc[-1] - df['Close'].iloc[-2]) if len(df) > 1 else 0,
            'regularMarketChangePercent': ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) if len(df) > 1 else 0,
            'dayHigh': df['High'].iloc[-1] if not df.empty else None, 'dayLow': df['Low'].iloc[-1] if not df.empty else None, 'regularMarketOpen': df['Open'].iloc[-1] if not df.empty else None,
            'preMarketPrice': raw_info.get('preMarketPrice'), 'preMarketChange': raw_info.get('preMarketChange'), 'preMarketChangePercent': raw_info.get('preMarketChangePercent'),
            'postMarketPrice': raw_info.get('postMarketPrice'), 'postMarketChange': raw_info.get('postMarketChange'), 'postMarketChangePercent': raw_info.get('postMarketChangePercent'),
        }
        return df, stock_info, df_mtf
    except Exception as e: return None, None, None

# --- 6. Analysis Logic (คงเดิม 100%) ---
def analyze_volume(row, vol_ma):
    vol = row['Volume']
    if np.isnan(vol_ma): return "Normal Volume", "gray"
    if vol > vol_ma * 1.5: return "High Volume", "green"
    elif vol < vol_ma * 0.7: return "Low Volume", "red"
    else: return "Normal Volume", "gray"

# --- 7. AI Decision Engine (FINE-TUNED SMART LOGIC) ---
def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, 
                       vol_status, mtf_trend, atr_val, mtf_ema200_val,
                       open_price, high, low, close): 
    
    # 1. รวบรวมข้อมูลดิบ
    candle_pattern, candle_color, candle_detail, is_big_candle = analyze_candlestick(open_price, high, low, close)
    
    bb_width = ((bb_up - bb_low) / ema20) * 100 if not np.isnan(ema20) else 0
    # [TUNED]: ปรับ Squeeze Threshold เป็น 8.0% ให้เหมาะกับหุ้นรายตัว
    is_squeeze = bb_width < 8.0 
    
    score = 0
    bullish_factors = [] 
    bearish_factors = []
    
    # --- [TUNED]: Quiet Uptrend Structure Check ---
    is_uptrend_structure = False
    if not np.isnan(ema20) and not np.isnan(ema50):
        # ราคายืนเหนือ EMA 20 และ 50 (ไม่ต้องรอตัด)
        if price > ema20 and price > ema50:
            # [ADDED SAFETY]: ต้องยืนเหนือ EMA 200 ด้วย เพื่อกรองขาลงที่เด้งหลอก
            if not np.isnan(ema200) and price > ema200:
                is_uptrend_structure = True

    # 2. ให้คะแนน Trend (Base Score)
    if not np.isnan(ema200):
        if price > ema200:
            score += 2; bullish_factors.append("ราคา > EMA 200 (เทรนด์หลักขาขึ้น)")
        else:
            score -= 2; bearish_factors.append("ราคา < EMA 200 (เทรนด์หลักขาลง)")
            
    if not np.isnan(ema20):
        if price > ema20: score += 1
        else: score -= 1

    if not np.isnan(macd_val) and not np.isnan(macd_sig):
        if macd_val > macd_sig: 
            score += 1; bullish_factors.append("MACD > Signal (โมเมนตัมบวก)")
        else: 
            score -= 1; bearish_factors.append("MACD < Signal (โมเมนตัมลบ)")
            
    # 3. การประมวลผลชั้นสูง (Advanced Synthesis)
    situation_insight = "ตลาดแกว่งตัวตามปกติ"
    
    # 3.1: REALITY FIX: Quiet Uptrend & Paradox
    if not np.isnan(adx) and adx < 25:
        if is_uptrend_structure:
            situation_insight = "📈 **Quiet Uptrend:** ราคาไต่ระดับขึ้นยืนเหนือ EMA หลักได้มั่นคง (Low Volatility) ถือเป็นขาขึ้นที่น่าสนใจ"
            bullish_factors.append("ราคาฟื้นตัวยืนเหนือเส้น EMA หลักได้ (Recovery)")
            
        elif is_big_candle and "Bullish" in candle_pattern:
            score += 3; situation_insight = "🚀 **Awakening Breakout:** ตลาดระเบิดพลังจากความเงียบด้วยแท่งเทียนใหญ่!"
            bullish_factors.append("Breakout พ้นจากโซน Sideway")
            
        elif is_big_candle and "Bearish" in candle_pattern:
            score -= 3; situation_insight = "💥 **Panic Breakdown:** ตลาดทิ้งตัวแรงจากความเงียบ!"
            bearish_factors.append("ทุบหลุดกรอบ Sideway")
            
        else:
            score = 0; situation_insight = "😴 **Sideway Market:** ADX ต่ำและไม่มีแรงซื้อขายที่มีนัยสำคัญ ตลาดรอเลือกทาง"

    # 3.2: Reversal & Pullback
    elif score < 0 and "Hammer" in candle_pattern and rsi < 35:
        score += 2; situation_insight = "↩️ **Potential Reversal:** เทรนด์หลักลง แต่เกิดแท่งเทียนกลับตัว (Hammer) ในโซน Oversold"
        bullish_factors.append("แพทเทิร์นกลับตัว (Hammer) ในโซน Oversold")

    elif score > 0 and "Shooting Star" in candle_pattern and rsi > 65:
        score -= 2; situation_insight = "⚠️ **Pullback Warning:** เทรนด์ขึ้น แต่เจอแรงขายกดดัน (Shooting Star) ระวังย่อตัว"
        bearish_factors.append("แพทเทิร์นกลับตัวลง (Shooting Star) ในโซน Overbought")

    # 3.3: Squeeze
    if is_squeeze:
        if is_big_candle: situation_insight = "💣 **Squeeze Breakout:** ระเบิดออกจากกรอบบีบตัว!"
        else: situation_insight = "⚡ **Volatility Squeeze:** กราฟบีบตัวแน่น เตรียมเลือกทาง"

    # 4. Volume
    vol_msg = "Normal"
    if "High Volume" in vol_status:
        if price > open_price: 
            score += 1; vol_msg = "Strong Buying (ซื้อจริง)"; bullish_factors.append("Volume เข้าสนับสนุนการขึ้น")
        else: 
            score -= 1; vol_msg = "Panic Selling (ขายจริง)"; bearish_factors.append("Volume ถล่มขาย")
            
    # 5. สรุป Strategy
    status_color = "yellow"; banner_title = ""; strategy_text = ""; holder_advice = ""
    sl_val = price - (2 * atr_val) if not np.isnan(atr_val) else price * 0.95
    tp_val = price + (3 * atr_val) if not np.isnan(atr_val) else price * 1.05

    if is_squeeze and not is_big_candle:
        status_color = "orange"; banner_title = "💣 Squeeze Watch: รอระเบิด"; strategy_text = "Wait for Breakout"
        holder_advice = f"ตั้ง Alert รอ! ถ้าทะลุ {bb_up:.2f} ให้ตาม แต่ถ้าหลุด {bb_low:.2f} ให้หนี"
    
    elif score >= 5:
        status_color = "green"; banner_title = "🚀 Super Nova: กระทิงดุ"; strategy_text = "Aggressive Buy / Let Profit Run"
        holder_advice = "กอดหุ้นแน่นๆ ตลาดเป็นใจทุกอย่าง (Trend + Momentum + Volume)"
        
    elif score >= 3:
        status_color = "green"; banner_title = "🐂 Bullish: ขาขึ้นแข็งแกร่ง"; strategy_text = "Buy on Dip / Hold"
        holder_advice = f"เทรนด์ยังดีมาก ถือต่อได้ ถ้าย่อมาแถว EMA 20 ({ema20:.2f}) เป็นโอกาสสะสม"
        
    elif score >= 1:
        status_color = "green"; banner_title = "📈 Moderate Bullish: ขาขึ้นต่อเนื่อง"; strategy_text = "Accumulate (ทยอยสะสม)"
        holder_advice = "ราคาไต่ขึ้นแบบ Low Volatility ถือได้เรื่อยๆ สบายใจ"
        
    elif score >= -2:
        status_color = "yellow"; banner_title = "⚖️ Neutral: ไซด์เวย์"; strategy_text = "Wait & See"
        holder_advice = "ตลาดไม่ไปไหน ทนถือหรือเปลี่ยนตัวเล่น"
        
    else:
        status_color = "red"; banner_title = "🐻 Bearish: ขาลง"; strategy_text = "Avoid / Cut Loss"
        holder_advice = "ถ้าหลุด EMA 20 ต้องยอมมอบตัว อย่าสวนเทรนด์"

    return {
        "status_color": status_color, "banner_title": banner_title, "strategy": strategy_text, "context": situation_insight,
        "bullish_factors": bullish_factors, "bearish_factors": bearish_factors, "sl": sl_val, "tp": tp_val, "holder_advice": holder_advice,
        "situation_insight": situation_insight, "candle_pattern": candle_pattern, "candle_color": candle_color, "candle_detail": candle_detail,
        "bb_width": bb_width, "is_squeeze": is_squeeze, "vol_quality_msg": vol_msg
    }

# --- 8. Display Execution (คงเดิม 100% + X-Ray) ---
if submit_btn:
    st.divider()
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)
    with st.spinner(f"AI กำลังประมวลผล {symbol_input} แบบ Hybrid Intelligent..."):
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)

    if df is not None and not df.empty and len(df) > 10: 
        # Calculations
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50)
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
        bbands = ta.bbands(df['Close'], length=20, std=2)
        if bbands is not None and len(bbands.columns) >= 3:
            bbl_col_name, bbu_col_name = bbands.columns[0], bbands.columns[2]
            df = pd.concat([df, bbands], axis=1)
        else: bbl_col_name, bbu_col_name = None, None
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14); df = pd.concat([df, adx], axis=1)
        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)

        # Last Values
        last = df.iloc[-1]
        price = info.get('regularMarketPrice') if info.get('regularMarketPrice') else last['Close']
        rsi = last['RSI'] if 'RSI' in last else np.nan
        atr = last['ATR'] if 'ATR' in last else np.nan
        ema20 = last['EMA20'] if 'EMA20' in last else np.nan
        ema50 = last['EMA50'] if 'EMA50' in last else np.nan
        ema200 = last['EMA200'] if 'EMA200' in last else np.nan
        vol_now = last['Volume']
        open_p = last['Open']; high_p = last['High']; low_p = last['Low']; close_p = last['Close']
        try: macd_val, macd_signal = last['MACD_12_26_9'], last['MACDs_12_26_9']
        except: macd_val, macd_signal = np.nan, np.nan
        try: adx_val = last['ADX_14']
        except: adx_val = np.nan
        if bbu_col_name and bbl_col_name: bb_upper, bb_lower = last[bbu_col_name], last[bbl_col_name]
        else: bb_upper, bb_lower = price * 1.05, price * 0.95
        vol_status, vol_color = analyze_volume(last, last['Vol_SMA20'])
        mtf_trend = "Sideway"; mtf_ema200_val = 0
        if df_mtf is not None and not df_mtf.empty:
            df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200) 
            if len(df_mtf) > 200 and not pd.isna(df_mtf['EMA200'].iloc[-1]):
                mtf_ema200_val = df_mtf['EMA200'].iloc[-1]
                if df_mtf['Close'].iloc[-1] > mtf_ema200_val: mtf_trend = "Bullish"
                else: mtf_trend = "Bearish"
        
        # AI Analysis
        ai_report = ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, 
                                       vol_status, mtf_trend, atr, mtf_ema200_val,
                                       open_p, high_p, low_p, close_p)

        # Log
        current_time = datetime.now().strftime("%H:%M:%S")
        log_entry = { "เวลา": current_time, "หุ้น": symbol_input, "ราคา": f"{price:.2f}", "Score": f"{ai_report['status_color'].upper()}", "คำแนะนำ": ai_report['banner_title'].split(':')[0], "Action": ai_report['strategy'] }
        st.session_state['history_log'].insert(0, log_entry)
        if len(st.session_state['history_log']) > 10: st.session_state['history_log'] = st.session_state['history_log'][:10]

        # DISPLAY (Original 100%)
        logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
        fallback_url = "https://cdn-icons-png.flaticon.com/512/720/720453.png"
        icon_html = f"""<img src="{logo_url}" onerror="this.onerror=null; this.src='{fallback_url}';" style="height: 50px; width: 50px; border-radius: 50%; vertical-align: middle; margin-right: 10px; object-fit: contain; background-color: white; border: 1px solid #e0e0e0; padding: 2px;">"""
        st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>{icon_html} {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            reg_price, reg_chg = info.get('regularMarketPrice'), info.get('regularMarketChange')
            if reg_price and reg_chg: prev_c = reg_price - reg_chg; reg_pct = (reg_chg / prev_c) * 100 if prev_c != 0 else 0.0
            else: reg_pct = 0.0
            color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"; bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
            st.markdown(f"""<div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;"><div style="font-size:40px; font-weight:600; line-height: 1;">{reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span></div><div style="display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text}; padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">{arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)</div></div>""", unsafe_allow_html=True)
            def make_pill(change, percent): color = "#16a34a" if change >= 0 else "#dc2626"; bg = "#e8f5ec" if change >= 0 else "#fee2e2"; arrow = "▲" if change >= 0 else "▼"; return f'<span style="background:{bg}; color:{color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{arrow} {change:+.2f} ({percent:.2f}%)</span>'
            ohlc_html = ""; m_state = info.get('marketState', '').upper()
            if m_state != "REGULAR": 
                d_open = info.get('regularMarketOpen'); d_high = info.get('dayHigh'); d_low = info.get('dayLow'); d_close = info.get('regularMarketPrice')
                if d_open and d_high and d_low and d_close: day_chg = info.get('regularMarketChange', 0); val_color = "#16a34a" if day_chg >= 0 else "#dc2626"; ohlc_html = f"""<div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; font-family: 'Source Sans Pro', sans-serif; white-space: nowrap; overflow-x: auto;"><span style="margin-right: 5px; opacity: 0.7;">O</span><span style="color: {val_color}; margin-right: 12px;">{d_open:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">H</span><span style="color: {val_color}; margin-right: 12px;">{d_high:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">L</span><span style="color: {val_color}; margin-right: 12px;">{d_low:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">C</span><span style="color: {val_color};">{d_close:.2f}</span></div>"""
            pre_post_html = ""
            if info.get('preMarketPrice') and info.get('preMarketChange'): p = info.get('preMarketPrice'); c = info.get('preMarketChange'); prev_p = p - c; pct = (c / prev_p) * 100 if prev_p != 0 else 0; pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">☀️ Pre: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'
            if info.get('postMarketPrice') and info.get('postMarketChange'): p = info.get('postMarketPrice'); c = info.get('postMarketChange'); prev_p = p - c; pct = (c / prev_p) * 100 if prev_p != 0 else 0; pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">🌙 Post: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'
            if ohlc_html or pre_post_html: st.markdown(f'<div style="margin-top: -5px; margin-bottom: 15px;">{ohlc_html}{pre_post_html}</div>', unsafe_allow_html=True)

        if tf_code == "1h": tf_label = "TF Hour"
        elif tf_code == "1wk": tf_label = "TF Week"
        else: tf_label = "TF Day"
        st_color = ai_report["status_color"]
        main_status = ai_report["banner_title"]
        if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
        elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
        else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

        c3, c4, c5 = st.columns(3)
        icon_up_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>"""
        icon_down_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12l7 7 7-7"/></svg>"""
        icon_flat_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#a3a3a3"><circle cx="12" cy="12" r="10"/></svg>"""
        with c3:
            pe_val = info.get('trailingPE'); pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"; pe_interp = get_pe_interpretation(pe_val)
            st.markdown(custom_metric_html("📊 P/E Ratio", pe_str, pe_interp, "gray", icon_flat_svg), unsafe_allow_html=True)
        with c4:
            rsi_str = f"{rsi:.2f}" if not np.isnan(rsi) else "N/A"; rsi_text = get_rsi_interpretation(rsi)
            st.markdown(custom_metric_html("⚡ RSI (14)", rsi_str, rsi_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        with c5:
            is_uptrend = price >= ema200 if not np.isnan(ema200) else True; adx_text = get_adx_interpretation(adx_val, is_uptrend); adx_str = f"{adx_val:.2f}" if not np.isnan(adx_val) else "N/A"
            st.markdown(custom_metric_html("💪 ADX Strength", adx_str, adx_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        
        st.write("") 
        c_ema, c_ai = st.columns([1.5, 2])
        with c_ema:
            st.subheader("📉 Technical Indicators")
            vol_str = format_volume(vol_now); e20_s = f"{ema20:.2f}" if not np.isnan(ema20) else "N/A"; e200_s = f"{ema200:.2f}" if not np.isnan(ema200) else "N/A"
            atr_pct = (atr / price) * 100 if not np.isnan(atr) and price > 0 else 0; atr_s = f"{atr:.2f} ({atr_pct:.1f}%)" if not np.isnan(atr) else "N/A"; macd_s = f"{macd_val:.3f}" if not np.isnan(macd_val) else "N/A"
            st.markdown(f"""<div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'><div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd; font-weight:bold;'><span>Indicator</span> <span>Value</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{e20_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{e200_s}</span></div><div style='display:flex; justify-content:space-between;'><span>MACD</span> <span>{macd_s}</span></div><div style='display:flex; justify-content:space-between;'><span>Volume ({vol_str})</span> <span style='color:{vol_color}'>{vol_status.split(' ')[0]}</span></div><div style='display:flex; justify-content:space-between;'><span>ATR</span> <span>{atr_s}</span></div></div>""", unsafe_allow_html=True)
            st.subheader("🚧 Key Levels")
            potential_supports = [(bb_lower, "BB Lower"), (df['Low'].tail(60).min(), "Low 60d"), (ema200, "EMA 200"), (ema20, "EMA 20")]
            raw_supports = sorted([x for x in potential_supports if not np.isnan(x[0]) and x[0] < price and x[0] > 0], key=lambda x: x[0], reverse=True)
            valid_supports = filter_levels(raw_supports)
            st.markdown("#### 🟢 แนวรับ"); 
            if valid_supports: 
                for v, d in valid_supports[:3]: st.write(f"- **{v:.2f}** : {d}")
            else: st.write("- N/A")
            potential_resistances = [(ema20, "EMA 20"), (ema200, "EMA 200"), (bb_upper, "BB Upper"), (df['High'].tail(60).max(), "High 60d")]
            raw_resistances = sorted([x for x in potential_resistances if not np.isnan(x[0]) and x[0] > price and x[0] > 0], key=lambda x: x[0])
            valid_resistances = filter_levels(raw_resistances)
            st.markdown("#### 🔴 แนวต้าน"); 
            if valid_resistances: 
                for v, d in valid_resistances[:2]: st.write(f"- **{v:.2f}** : {d}")
            else: st.write("- N/A")
            if ai_report['situation_insight']:
                st.write("")
                with st.expander("💡 อ่านสถานการณ์กราฟ (Click to Read)", expanded=True):
                    st.warning(ai_report['situation_insight'])

        with c_ai:
            st.subheader("🔬 Price Action X-Ray")
            sq_txt = "⚠️ Squeeze (อัดอั้น)" if ai_report['is_squeeze'] else "Normal (ปกติ)"
            sq_col = "#f97316" if ai_report['is_squeeze'] else "#0369a1"
            vol_q_col = "#22c55e" if "Buying" in ai_report['vol_quality_msg'] else ("#ef4444" if "Selling" in ai_report['vol_quality_msg'] else "#6b7280")
            st.markdown(f"""<div class='xray-box'><div class='xray-title'>🕯️ Deep Insight</div><div class='xray-item'><span>ทรงกราฟ:</span> <span style='font-weight:bold;'>{ai_report['candle_pattern']}</span></div><div class='xray-item'><span>สถานะ:</span> <span>{ai_report['candle_color']}</span></div><div class='xray-item'><span>รายละเอียด:</span> <span style='font-style:italic;'>{ai_report['candle_detail']}</span></div><hr style='margin: 8px 0; opacity: 0.3;'><div class='xray-item'><span>ความผันผวน:</span> <span style='color:{sq_col}; font-weight:bold;'>{sq_txt}</span></div><div class='xray-item'><span>คุณภาพ Volume:</span> <span style='color:{vol_q_col}; font-weight:bold;'>{ai_report['vol_quality_msg']}</span></div></div>""", unsafe_allow_html=True)
            st.subheader("🤖 AI STRATEGY")
            color_map = {"green": {"bg": "#dcfce7", "border": "#22c55e", "text": "#14532d"}, "red": {"bg": "#fee2e2", "border": "#ef4444", "text": "#7f1d1d"}, "orange": {"bg": "#ffedd5", "border": "#f97316", "text": "#7c2d12"}, "yellow": {"bg": "#fef9c3", "border": "#eab308", "text": "#713f12"}}
            c_theme = color_map.get(ai_report['status_color'], color_map["yellow"])
            st.markdown(f"""<div style="background-color: {c_theme['bg']}; border-left: 6px solid {c_theme['border']}; padding: 20px; border-radius: 10px; margin-bottom: 20px;"><h2 style="color: {c_theme['text']}; margin:0 0 10px 0; font-size: 28px;">{ai_report['banner_title'].split(':')[0]}</h2><h3 style="color: {c_theme['text']}; margin:0 0 15px 0; font-size: 20px; opacity: 0.9;">{ai_report['strategy']}</h3><p style="color: {c_theme['text']}; font-size: 16px; margin:0; line-height: 1.6;"><b>💡 ภาพรวม:</b> {ai_report['context']}</p></div>""", unsafe_allow_html=True)
            with st.chat_message("assistant"):
                if ai_report['bullish_factors']: 
                    st.markdown("**🟢 ปัจจัยบวก:**")
                    for r in ai_report['bullish_factors']: st.write(f"- {r}")
                if ai_report['bearish_factors']: 
                    st.markdown("**🔴 ความเสี่ยง:**")
                    for w in ai_report['bearish_factors']: st.write(f"- {w}")
                st.markdown("---"); st.info(f"🎒 **คำแนะนำ:** {ai_report['holder_advice']}"); st.write(f"🛑 **SL:** {ai_report['sl']:.2f} | ✅ **TP:** {ai_report['tp']:.2f}")

        st.write(""); st.markdown("""<div class='disclaimer-box'>⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากการวิเคราะห์ทางเทคนิคด้วยระบบ AI เพื่อประกอบการตัดสินใจเท่านั้น</div>""", unsafe_allow_html=True); st.divider()
        st.subheader("📜 History Log")
        if st.session_state['history_log']: st.dataframe(pd.DataFrame(st.session_state['history_log']), use_container_width=True, hide_index=True)
        st.divider()
        rsi_interp_str = get_rsi_interpretation(rsi); macd_interp_str = "🟢 Bullish" if macd_val > macd_signal else "🔴 Bearish"
        display_learning_section(rsi, rsi_interp_str, macd_val, macd_signal, macd_interp_str, adx_val, price, ema200, bb_upper, bb_lower)

    else: st.error("ไม่พบข้อมูลหุ้น")
