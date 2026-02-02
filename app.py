import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# --- 1. ตั้งค่าหน้าเว็บ (The Master Version) ---
st.set_page_config(page_title="AI Stock Master (SMC)", page_icon="💎", layout="wide")

# --- Initialize Session State for History ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = []

# --- 2. CSS ปรับแต่ง (Clean & Professional) ---
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

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>Ultimate Sniper (SMC + OBV Hybrid)🚀</span></h1>", unsafe_allow_html=True)

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
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
            else: tf_code = "1d"; mtf_code = "1wk"
        
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Helper Functions ---

def analyze_candlestick(open_price, high, low, close):
    """ฟังก์ชันอ่านแท่งเทียน (Tuned Sensitivity 0.6)"""
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

def get_adx_interpretation(adx, is_uptrend):
    if np.isnan(adx): return "N/A"
    trend_str = "ขาขึ้น" if is_uptrend else "ขาลง"
    if adx >= 50: return f"Super Strong {trend_str} (แรงมาก)"
    if adx >= 25: return f"Strong {trend_str} (แข็งแกร่ง)"
    if adx >= 20: return "Developing Trend (เริ่มก่อตัว)"
    return "Weak/Sideway (ตลาดไร้ทิศทาง)"

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

# --- SMC: Find Zones ---

def find_demand_zones(df, atr_multiplier=0.25):
    """ ค้นหา Demand Zones (Swing Low) """
    zones = []
    if len(df) < 20: return zones
    
    lows = df['Low']
    is_swing_low = (lows < lows.shift(1)) & (lows < lows.shift(2)) & (lows < lows.shift(-1)) & (lows < lows.shift(-2))
    swing_indices = is_swing_low[is_swing_low].index
    current_price = df['Close'].iloc[-1]
    
    for date in swing_indices:
        if date == df.index[-1] or date == df.index[-2]: continue
        swing_low_val = df.loc[date, 'Low']
        atr_val = df.loc[date, 'ATR'] if 'ATR' in df.columns else (swing_low_val * 0.02)
        if np.isnan(atr_val): atr_val = swing_low_val * 0.02
        
        zone_bottom = swing_low_val
        zone_top = swing_low_val + (atr_val * atr_multiplier)
        
        if (current_price - zone_top) / current_price > 0.20: continue
        future_data = df.loc[date:][1:]
        if future_data.empty: continue
        if not (future_data['Close'] < zone_bottom).any():
            test_count = ((future_data['Low'] <= zone_top) & (future_data['Low'] >= zone_bottom)).sum()
            zones.append({'bottom': zone_bottom, 'top': zone_top, 'type': 'Fresh' if test_count == 0 else 'Tested'})
    return zones

def find_supply_zones(df, atr_multiplier=0.25):
    """ ค้นหา Supply Zones (Swing High) - สำหรับแนวต้าน """
    zones = []
    if len(df) < 20: return zones
    
    highs = df['High']
    is_swing_high = (highs > highs.shift(1)) & (highs > highs.shift(2)) & (highs > highs.shift(-1)) & (highs > highs.shift(-2))
    swing_indices = is_swing_high[is_swing_high].index
    current_price = df['Close'].iloc[-1]
    
    for date in swing_indices:
        if date == df.index[-1] or date == df.index[-2]: continue
        swing_high_val = df.loc[date, 'High']
        atr_val = df.loc[date, 'ATR'] if 'ATR' in df.columns else (swing_high_val * 0.02)
        if np.isnan(atr_val): atr_val = swing_high_val * 0.02
        
        zone_top = swing_high_val
        zone_bottom = swing_high_val - (atr_val * atr_multiplier)
        
        # Filter: ถ้าโซนอยู่สูงเกิน 20% ของราคาปัจจุบัน ให้ข้าม (ลด Noise)
        if (zone_bottom - current_price) / current_price > 0.20: continue

        future_data = df.loc[date:][1:]
        if future_data.empty: continue
        # Fresh Check: ราคายังไม่เคยปิดทะลุ High ขึ้นไป
        if not (future_data['Close'] > zone_top).any():
            zones.append({'bottom': zone_bottom, 'top': zone_top, 'type': 'Fresh'})
            
    return zones

# --- 5. Data Fetching ---

@st.cache_data(ttl=60, show_spinner=False)
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        if interval == "1wk": period_val = "10y"
        elif interval == "1d": period_val = "5y"
        else: period_val = "730d"
        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval)
        if not df_mtf.empty: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
        
        try: raw_info = ticker.info 
        except: raw_info = {} 

        df_daily_header = ticker.history(period="5d", interval="1d")
        if not df_daily_header.empty:
            header_price = df_daily_header['Close'].iloc[-1]
            header_change = header_price - df_daily_header['Close'].iloc[-2] if len(df_daily_header) >=2 else 0
            header_pct = (header_change / df_daily_header['Close'].iloc[-2]) if len(df_daily_header) >=2 else 0
            d_h, d_l, d_o = df_daily_header['High'].iloc[-1], df_daily_header['Low'].iloc[-1], df_daily_header['Open'].iloc[-1]
        else:
            header_price = df['Close'].iloc[-1]
            header_change, header_pct = 0, 0
            d_h, d_l, d_o = df['High'].iloc[-1], df['Low'].iloc[-1], df['Open'].iloc[-1]

        stock_info = {
            'longName': raw_info.get('longName', symbol), 
            'marketState': raw_info.get('marketState', 'REGULAR'), 
            'regularMarketPrice': header_price, 'regularMarketChange': header_change,
            'regularMarketChangePercent': header_pct, 'dayHigh': d_h, 'dayLow': d_l, 'regularMarketOpen': d_o,
            'preMarketPrice': raw_info.get('preMarketPrice'), 'preMarketChange': raw_info.get('preMarketChange'),
            'postMarketPrice': raw_info.get('postMarketPrice'), 'postMarketChange': raw_info.get('postMarketChange'),
        }
        
        return df, stock_info, df_mtf
    except: return None, None, None

# --- 6. Analysis Logic (Thai Volume Grading) ---

def analyze_volume(row, vol_ma):
    vol = row['Volume']
    
    # กัน Error กรณีหุ้นใหม่ หรือไม่มีค่าเฉลี่ย
    if np.isnan(vol_ma) or vol_ma == 0: 
        return "☁️ ปกติ", "gray"
    
    # คำนวณ % เทียบค่าเฉลี่ย
    pct = (vol / vol_ma) * 100
    
    # --- แบ่งเกรด 4 ระดับ (ภาษาไทย) ---
    if pct >= 250: # ระดับ 4: ระเบิดลง
        return f"💣 สูงมาก/ระเบิด ({pct:.0f}%)", "#7f1d1d" # สีแดงเข้ม (Extreme)
    elif pct >= 120: # ระดับ 3: คึกคัก
        return f"🔥 สูง/คึกคัก ({pct:.0f}%)", "#16a34a" # สีเขียว (Strong)
    elif pct <= 70: # ระดับ 1: แห้ง
        return f"🌵 ต่ำ/เบาบาง ({pct:.0f}%)", "#f59e0b" # สีส้ม (Quiet)
    else: # ระดับ 2: ปกติ
        return f"☁️ ปกติ ({pct:.0f}%)", "gray" # สีเทา

# --- 7. AI Decision Engine (Detailed Insight Version) ---

def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, 
                       vol_status, mtf_trend, atr_val, mtf_ema200_val,
                       open_price, high, low, close, obv_val, obv_avg,
                       obv_slope, rolling_min, rolling_max,
                       prev_open, prev_close, vol_now, vol_avg, demand_zones,
                       is_squeeze):

    def safe_float(x):
        try: return float(x) if not np.isnan(float(x)) else np.nan
        except: return np.nan
    
    price = safe_float(price); ema20 = safe_float(ema20); ema50 = safe_float(ema50); ema200 = safe_float(ema200)
    atr_val = safe_float(atr_val); vol_now = safe_float(vol_now); vol_avg = safe_float(vol_avg)
    obv_slope = safe_float(obv_slope)

    # 1. Raw Data & Pattern
    candle_pattern, candle_color, candle_detail, is_big_candle = analyze_candlestick(open_price, high, low, close)
    is_reversal_candle = "Hammer" in candle_pattern or "Doji" in candle_pattern
    
    # Extract Volume Grade
    vol_grade_text, vol_grade_color = analyze_volume({'Volume': vol_now}, vol_avg)

    # 2. SMC Location Check
    in_demand_zone = False
    active_zone = None
    if demand_zones:
        for zone in demand_zones:
            if (low <= zone['top'] * 1.005) and (high >= zone['bottom']):
                in_demand_zone = True; active_zone = zone; break
    
    # 3. Confluence Check
    is_confluence = False; confluence_msg = ""
    if in_demand_zone:
        if abs(active_zone['bottom'] - ema200) / price < 0.02: is_confluence = True; confluence_msg = "Zone + EMA 200"
        elif abs(active_zone['bottom'] - ema50) / price < 0.02: is_confluence = True; confluence_msg = "Zone + EMA 50"

    # --- SCORING SYSTEM ---
    score = 0
    bullish_factors = []
    bearish_factors = []
    
    # --- 4. DETAILED FACTOR COLLECTION (เก็บทุกเม็ด) ---
    
    # A. Trend Structure (EMA)
    if not np.isnan(ema200):
        if price > ema200: 
            score += 2; bullish_factors.append("ยืนเหนือ EMA 200 (เทรนด์หลักขาขึ้น)")
        else: 
            score -= 2; bearish_factors.append("หลุด EMA 200 (เทรนด์หลักขาลง)")
            
    if not np.isnan(ema50):
        if price > ema50: score += 1; bullish_factors.append("ยืนเหนือ EMA 50 (ระยะกลางแกร่ง)")
        else: score -= 1; bearish_factors.append("หลุด EMA 50 (ระยะกลางเสียทรง)")
        
    if not np.isnan(ema20):
        if price < ema20: score -= 1; bearish_factors.append("หลุด EMA 20 (ระยะสั้นลง)")
    
    # B. Momentum (MACD & RSI)
    if not np.isnan(macd_val) and not np.isnan(macd_sig):
        if macd_val > macd_sig: bullish_factors.append(f"MACD ตัดขึ้น (Momentum บวก)")
        else: score -= 1; bearish_factors.append(f"MACD ตัดลง (Momentum ลบ)")
        
    if rsi < 30: 
        score += 1; bullish_factors.append(f"RSI Oversold ({rsi:.0f}) - ขายมากเกินไป")
    elif rsi > 70: 
        score -= 1; bearish_factors.append(f"RSI Overbought ({rsi:.0f}) - ซื้อมากเกินไป")

    # C. Multi-Timeframe
    if mtf_trend == "Bullish": 
        score += 1; bullish_factors.append("TF ใหญ่เป็นขาขึ้น (Major Uptrend)")
    else:
        bearish_factors.append("TF ใหญ่เป็นขาลง (Major Downtrend)")

    # --- 5. SMART LOGIC & OVERRIDES ---
    
    situation_insight = "" # รอเติมตามสถานการณ์
    
    # Smart OBV
    has_bullish_div = False; has_bearish_div = False; obv_insight = "Volume Flow ปกติ (ตามเทรนด์)"
    if not np.isnan(obv_slope):
        if price < ema20 and obv_slope > 0:
            has_bullish_div = True; score += 2
            bullish_factors.append("💎 Smart OBV: เกิด Bullish Divergence (เจ้าเก็บของ)")
            obv_insight = "Bullish Divergence (สะสมพลัง)"
        elif price > ema20 and obv_slope < 0:
            has_bearish_div = True; score -= 2
            bearish_factors.append("⚠️ Smart OBV: เกิด Bearish Divergence (เจ้าออกของ)")
            obv_insight = "Bearish Divergence (ระวังทุบ)"

    # Squeeze
    if is_squeeze:
        situation_insight = "💣 **BB Squeeze:** กราฟบีบอัดรุนแรง รอระเบิดเลือกทาง!"
        if has_bullish_div: score += 1; situation_insight += " (แนวโน้มระเบิดขึ้น 🚀)"
        elif has_bearish_div: score -= 1; situation_insight += " (แนวโน้มระเบิดลง 🩸)"

    # SMC & Volume Logic
    if in_demand_zone:
        is_vol_safe = "ต่ำ" in vol_grade_text or "ปกติ" in vol_grade_text
        if is_vol_safe:
            score += 3
            bullish_factors.append(f"🟢 ราคาอยู่ใน Demand Zone + Volume ปลอดภัย")
            if not is_squeeze: situation_insight = "💎 **Sniper Mode:** เข้าโซนซื้อสวย Volume แห้ง รอเด้ง"
            if is_reversal_candle: score += 1; bullish_factors.append("🕯️ เจอแท่งเทียนกลับตัวในโซน")
        
        if is_confluence: score += 2; bullish_factors.append(f"⭐ จุดนัดพบ: Demand Zone ตรงกับ {confluence_msg}")

    # --- 6. SAFETY NET & FINAL INSIGHT GENERATOR ---
    
    # Safety Net 1: Crash (ระเบิดลง)
    if "ระเบิด" in vol_grade_text and close < open_price:
        score -= 10
        bearish_factors.append("💀 **Panic Sell:** แรงขายระดับระเบิด (หนีตาย!)")
        situation_insight = "🩸 **Market Crash:** แรงขายถล่มทลาย ห้ามรับมีดเด็ดขาด!"
        # Reset Bullish Factors to avoid confusion
        bullish_factors = [f for f in bullish_factors if "EMA" not in f and "Trend" not in f]
        
    # Safety Net 2: Heavy Selling (กฎรอง - ที่ SOFI โดน)
    elif "คึกคัก" in vol_grade_text and is_big_candle and close < open_price:
        score -= 3
        bearish_factors.append("⚠️ **Heavy Selling:** แรงขายเยอะผิดปกติ + แท่งแดงยาว")
        # Insight เฉพาะสำหรับเคสนี้
        if score <= -3:
            situation_insight = "🩸 **Falling Knife:** แรงขายกดดันต่อเนื่อง เสียทรงขาลงชัดเจน"
        else:
            situation_insight = "⚠️ **Selling Pressure:** ระวังแรงขายกดดัน อาจย่อตัวลึก"

    # Default Insight Generator (ถ้าไม่เข้าเงื่อนไขพิเศษด้านบน ให้สร้างคำพูดตาม Score)
    if situation_insight == "":
        if score >= 5: situation_insight = "🚀 **Skyrocket:** โครงสร้างขาขึ้นแข็งแกร่ง + ปัจจัยบวกครบ"
        elif score >= 3: situation_insight = "🐂 **Uptrend/Recovery:** เทรนด์ดี/เริ่มฟื้นตัว ย่อตัวน่าสนใจ"
        elif score >= 1: situation_insight = "⚖️ **Sideway Up:** แกว่งตัวออกข้างอิงทางบวก รอจังหวะ"
        elif score >= -2: situation_insight = "🐻 **Sideway Down:** แกว่งตัวออกข้างอิงทางลบ/ติดแนวต้าน"
        else: situation_insight = "📉 **Downtrend:** โครงสร้างขาลง แรงขายยังคุมตลาด"

    # Final Status Color & Text
    if score >= 5:
        status_color = "green"; banner_title = "🚀 Sniper Entry: จุดซื้อคมกริบ"; strategy_text = "Aggressive Buy"
        holder_advice = f"ทรงกราฟสวยมาก ถือรันเทรนด์หรือหาจังหวะเข้าเพิ่ม SL: {low-(atr_val*0.5):.2f}"
    elif score >= 3:
        status_color = "green"; banner_title = "🐂 Buy on Dip: ย่อซื้อ"; strategy_text = "Accumulate"
        holder_advice = "ย่อตัวในขาขึ้น/จุดรับ ทยอยสะสมได้"
    elif score >= 1:
        status_color = "yellow"; banner_title = "⚖️ Neutral: ไซด์เวย์"; strategy_text = "Wait for Trigger"
        holder_advice = "ตลาดเลือกทาง เฝ้าดูโซนรับ ถ้าราคาเริ่มเด้งค่อยตาม"
    elif score <= -3:
        status_color = "red"; banner_title = "🩸 Falling Knife: มีดหล่น"; strategy_text = "Wait / Cut Loss"
        holder_advice = "อันตราย! แรงขายรุนแรง ห้ามรับจนกว่าจะเห็นฐานใหม่"
    else:
        status_color = "orange"; banner_title = "🐻 Bearish Pressure: แรงกดดันสูง"; strategy_text = "Avoid"
        holder_advice = "เทรนด์อ่อนแอ/ติดต้าน อย่าเพิ่งเข้าเสี่ยง"

    # SL/TP Logic
    if in_demand_zone: sl_val = active_zone['bottom'] - (atr_val * 0.5) 
    else: sl_val = price - (2 * atr_val) if not np.isnan(atr_val) else price * 0.95
    tp_val = price + (3 * atr_val) if not np.isnan(atr_val) else price * 1.05

    return {
        "status_color": status_color, "banner_title": banner_title, "strategy": strategy_text, "context": situation_insight,
        "bullish_factors": bullish_factors, "bearish_factors": bearish_factors, "sl": sl_val, "tp": tp_val, "holder_advice": holder_advice,
        "candle_pattern": candle_pattern, "candle_color": candle_color, "candle_detail": candle_detail,
        "vol_quality_msg": vol_grade_text, "vol_quality_color": vol_grade_color,
        "in_demand_zone": in_demand_zone, "confluence_msg": confluence_msg,
        "is_squeeze": is_squeeze, "obv_insight": obv_insight
    }

# --- 8. Display Execution ---

if submit_btn:
    st.divider()
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)
    with st.spinner(f"AI กำลังสแกนหา Demand/Supply Zone และประมวลผล {symbol_input}..."):
        # 1. Main Data
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)
        
        # 2. Safety Net Data (Week/Day)
        try:
            ticker_stats = yf.Ticker(symbol_input)
            df_stats_day = ticker_stats.history(period="2y", interval="1d")
            df_stats_week = ticker_stats.history(period="5y", interval="1wk")
        except:
            df_stats_day = pd.DataFrame(); df_stats_week = pd.DataFrame()

    if df is not None and not df.empty and len(df) > 20: 
        # Indicators
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
        
        # --- 🌟 ADDED: OBV & Rolling Logic ---
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['OBV_SMA20'] = ta.sma(df['OBV'], length=20)
        df['OBV_Slope'] = ta.slope(df['OBV'], length=5) 
        df['Rolling_Min'] = df['Low'].rolling(window=20).min()
        df['Rolling_Max'] = df['High'].rolling(window=20).max()
        
        # --- 🌟 ADDED: Relative BB Squeeze Logic ---
        # คำนวณ Bandwidth
        if bbu_col_name and bbl_col_name and 'EMA20' in df.columns:
            df['BB_Width'] = (df[bbu_col_name] - df[bbl_col_name]) / df['EMA20'] * 100
            # หาค่า Bandwidth ที่แคบที่สุดในรอบ 20 วัน
            df['BB_Width_Min20'] = df['BB_Width'].rolling(window=20).min()
            # เช็คว่าปัจจุบันแคบใกล้เคียงจุดต่ำสุดไหม (Relative Squeeze)
            is_squeeze = df['BB_Width'].iloc[-1] <= (df['BB_Width_Min20'].iloc[-1] * 1.1) # ยอมให้กว้างกว่าจุดต่ำสุดได้ 10%
        else:
            is_squeeze = False

        # Find Zones
        demand_zones = find_demand_zones(df, atr_multiplier=0.25)
        supply_zones = find_supply_zones(df, atr_multiplier=0.25) # NEW for Resistance
        
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
        
        try: obv_val = last['OBV']; obv_avg = last['OBV_SMA20']
        except: obv_val = np.nan; obv_avg = np.nan
        obv_slope_val = last.get('OBV_Slope', np.nan)
        rolling_min_val = last.get('Rolling_Min', np.nan)
        rolling_max_val = last.get('Rolling_Max', np.nan)

        mtf_trend = "Sideway"; mtf_ema200_val = 0
        if df_mtf is not None and not df_mtf.empty:
            if 'EMA200' not in df_mtf.columns: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
            if len(df_mtf) > 200 and not pd.isna(df_mtf['EMA200'].iloc[-1]):
                mtf_ema200_val = df_mtf['EMA200'].iloc[-1]
                if df_mtf['Close'].iloc[-1] > mtf_ema200_val: mtf_trend = "Bullish"
                else: mtf_trend = "Bearish"
        
        try: prev_open = df['Open'].iloc[-2]; prev_close = df['Close'].iloc[-2]; vol_avg = last['Vol_SMA20']
        except: prev_open = 0; prev_close = 0; vol_avg = 1

        ai_report = ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, 
                                       vol_status, mtf_trend, atr, mtf_ema200_val,
                                       open_p, high_p, low_p, close_p, obv_val, obv_avg,
                                       obv_slope_val, rolling_min_val, rolling_max_val,
                                       prev_open, prev_close, vol_now, vol_avg, demand_zones, is_squeeze)

        # Log
        current_time = datetime.now().strftime("%H:%M:%S")
        log_entry = { "เวลา": current_time, "หุ้น": symbol_input, "ราคา": f"{price:.2f}", "Score": f"{ai_report['status_color'].upper()}", "คำแนะนำ": ai_report['banner_title'].split(':')[0], "Action": ai_report['strategy'] }
        st.session_state['history_log'].insert(0, log_entry)
        if len(st.session_state['history_log']) > 10: st.session_state['history_log'] = st.session_state['history_log'][:10]

        # DISPLAY
        logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
        fallback_url = "https://cdn-icons-png.flaticon.com/512/720/720453.png"
        icon_html = f"""<img src="{logo_url}" onerror="this.onerror=null; this.src='{fallback_url}';" style="height: 50px; width: 50px; border-radius: 50%; vertical-align: middle; margin-right: 10px; object-fit: contain; background-color: white; border: 1px solid #e0e0e0; padding: 2px;">"""
        st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>{icon_html} {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)

        m_state = info.get('marketState', '').upper()
        if m_state == "REGULAR": st_msg = "🟢 **Market Open:** Real-time Analysis"; st_bg = "#dcfce7"; st_color = "#166534"
        elif m_state in ["PRE", "PREPRE"]: st_msg = "🟠 **Pre-Market:** Pending Open"; st_bg = "#ffedd5"; st_color = "#9a3412"
        elif m_state in ["POST", "POSTPOST"]: st_msg = "🌙 **Post-Market:** Closed"; st_bg = "#e0e7ff"; st_color = "#3730a3"
        else: st_msg = "🔴 **Market Closed**"; st_bg = "#fee2e2"; st_color = "#991b1b"
        st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><div style="background-color: {st_bg}; color: {st_color}; padding: 8px 20px; border-radius: 30px; font-size: 0.95rem; font-weight: 600; display: inline-block;">{st_msg}</div></div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            reg_price, reg_chg = info.get('regularMarketPrice'), info.get('regularMarketChange')
            if reg_price and reg_chg: prev_c = reg_price - reg_chg; reg_pct = (reg_chg / prev_c) * 100 if prev_c != 0 else 0.0
            else: reg_pct = 0.0
            color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"; bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
            st.markdown(f"""<div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;"><div style="font-size:40px; font-weight:600; line-height: 1;">{reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span></div><div style="display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text}; padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">{arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)</div></div>""", unsafe_allow_html=True)
            def make_pill(change, percent): color = "#16a34a" if change >= 0 else "#dc2626"; bg = "#e8f5ec" if change >= 0 else "#fee2e2"; arrow = "▲" if change >= 0 else "▼"; return f'<span style="background:{bg}; color:{color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{arrow} {change:+.2f} ({percent:.2f}%)</span>'
            ohlc_html = ""; 
            if m_state != "REGULAR": 
                d_open = info.get('regularMarketOpen'); d_high = info.get('dayHigh'); d_low = info.get('dayLow'); d_close = info.get('regularMarketPrice')
                if d_open: day_chg = info.get('regularMarketChange', 0); val_color = "#16a34a" if day_chg >= 0 else "#dc2626"; ohlc_html = f"""<div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; font-family: 'Source Sans Pro', sans-serif; white-space: nowrap; overflow-x: auto;"><span style="margin-right: 5px; opacity: 0.7;">O</span><span style="color: {val_color}; margin-right: 12px;">{d_open:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">H</span><span style="color: {val_color}; margin-right: 12px;">{d_high:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">L</span><span style="color: {val_color}; margin-right: 12px;">{d_low:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">C</span><span style="color: {val_color};">{d_close:.2f}</span></div>"""
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

        c3, c4 = st.columns(2)
        icon_flat_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#a3a3a3"><circle cx="12" cy="12" r="10"/></svg>"""
        
        with c3:
            rsi_str = f"{rsi:.2f}" if not np.isnan(rsi) else "N/A"; rsi_text = get_rsi_interpretation(rsi)
            st.markdown(custom_metric_html("⚡ RSI (14)", rsi_str, rsi_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        with c4:
            adx_disp = float(adx_val) if not np.isnan(adx_val) else np.nan
            is_uptrend = price >= ema200 if not np.isnan(ema200) else True
            adx_text = get_adx_interpretation(adx_disp, is_uptrend)
            adx_str = f"{adx_disp:.2f}" if not np.isnan(adx_disp) else "N/A"
            st.markdown(custom_metric_html("💪 ADX Strength", adx_str, adx_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        
        st.write("") 
        c_ema, c_ai = st.columns([1.5, 2])
        with c_ema:
            st.subheader("📉 Technical Indicators")
            vol_str = format_volume(vol_now)
            e20_s = f"{ema20:.2f}" if not np.isnan(ema20) else "N/A"
            e50_s = f"{ema50:.2f}" if not np.isnan(ema50) else "N/A"
            e200_s = f"{ema200:.2f}" if not np.isnan(ema200) else "N/A"
            atr_pct = (atr / price) * 100 if not np.isnan(atr) and price > 0 else 0; atr_s = f"{atr:.2f} ({atr_pct:.1f}%)" if not np.isnan(atr) else "N/A"
            
            # --- 🔥 ADDED: BB Display Here ---
            bb_s = f"{bb_upper:.2f} / {bb_lower:.2f}" if not np.isnan(bb_upper) else "N/A"
            # -------------------------------

            st.markdown(f"""<div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'><div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd; font-weight:bold;'><span>Indicator</span> <span>Value</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{e20_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 50</span> <span>{e50_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{e200_s}</span></div><div style='display:flex; justify-content:space-between;'><span>Volume ({vol_str})</span> <span style='color:{ai_report['vol_quality_color']}'>{ai_report['vol_quality_msg']}</span></div><div style='display:flex; justify-content:space-between;'><span>ATR</span> <span>{atr_s}</span></div><div style='display:flex; justify-content:space-between;'><span>BB (Up/Low)</span> <span>{bb_s}</span></div></div>""", unsafe_allow_html=True)
            
            # --- DISTANCE FILTER SETTINGS (TUNED) ---
            if tf_code == "1h": min_dist = atr * 1.0 
            elif tf_code == "1wk": min_dist = atr * 2.0 
            else: min_dist = atr * 1.5 

            st.subheader("🚧 Key Levels")
            
            # === PART 1: SUPPORTS ===
            candidates_supp = []
            if not np.isnan(ema20) and ema20 < price: candidates_supp.append({'val': ema20, 'label': f"EMA 20 ({tf_label} - ระยะสั้น)"})
            if not np.isnan(ema50) and ema50 < price: candidates_supp.append({'val': ema50, 'label': f"EMA 50 ({tf_label})"})
            if not np.isnan(ema200) and ema200 < price: candidates_supp.append({'val': ema200, 'label': f"EMA 200 ({tf_label} - Trend Support)"})
            if not np.isnan(bb_lower) and bb_lower < price: candidates_supp.append({'val': bb_lower, 'label': f"BB Lower ({tf_label} - แนวรับผันผวน)"})

            if not df_stats_day.empty:
                d_ema50 = ta.ema(df_stats_day['Close'], length=50).iloc[-1]
                d_ema200 = ta.ema(df_stats_day['Close'], length=200).iloc[-1]
                if d_ema50 < price: candidates_supp.append({'val': d_ema50, 'label': "EMA 50 (TF Day - รับระยะกลาง)"})
                if d_ema200 < price: candidates_supp.append({'val': d_ema200, 'label': "🛡️ EMA 200 (TF Day - รับใหญ่รายวัน)"})
                low_60d = df_stats_day['Low'].tail(60).min()
                if low_60d < price: candidates_supp.append({'val': low_60d, 'label': "📉 Low 60d (ฐานสั้น)"})

            if not df_stats_week.empty:
                w_ema50 = ta.ema(df_stats_week['Close'], length=50).iloc[-1]
                w_ema200 = ta.ema(df_stats_week['Close'], length=200).iloc[-1]
                if w_ema50 < price: candidates_supp.append({'val': w_ema50, 'label': "EMA 50 (TF Week - รับระยะยาว)"})
                if w_ema200 < price: candidates_supp.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - รับระดับกองทุน)"})

            if demand_zones:
                for z in demand_zones: candidates_supp.append({'val': z['bottom'], 'label': f"Demand Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})

            candidates_supp.sort(key=lambda x: x['val'], reverse=True) # High -> Low for Support

            merged_supp = []
            skip_next = False
            for i in range(len(candidates_supp)):
                if skip_next: skip_next = False; continue
                current = candidates_supp[i]
                if i < len(candidates_supp) - 1:
                    next_item = candidates_supp[i+1]
                    if (current['val'] - next_item['val']) / current['val'] < 0.01: 
                        new_label = f"⭐ Confluence Zone ({current['label']} + {next_item['label']})"
                        merged_supp.append({'val': current['val'], 'label': new_label})
                        skip_next = True
                        continue
                merged_supp.append(current)

            final_show_supp = []
            for item in merged_supp:
                if (price - item['val']) / price > 0.30 and "EMA 200 (TF Week" not in item['label']: continue
                is_vip = "EMA 200" in item['label'] or "EMA 50 (TF Week" in item['label'] or "52-Week" in item['label']
                if not final_show_supp: final_show_supp.append(item)
                else:
                    last_item = final_show_supp[-1]
                    dist = abs(last_item['val'] - item['val'])
                    if is_vip or dist >= min_dist:
                        final_show_supp.append(item)

            st.markdown("#### 🟢 แนวรับ"); 
            if final_show_supp: 
                for item in final_show_supp[:4]: st.write(f"- **{item['val']:.2f} :** {item['label']}")
            else: st.error("🚨 ราคาหลุดทุกแนวรับสำคัญ! (All Time Low?)")

            # === PART 2: RESISTANCES ===
            candidates_res = []
            if not np.isnan(ema20) and ema20 > price: candidates_res.append({'val': ema20, 'label': f"EMA 20 ({tf_label} - ต้านสั้น)"})
            if not np.isnan(ema50) and ema50 > price: candidates_res.append({'val': ema50, 'label': f"EMA 50 ({tf_label})"})
            if not np.isnan(ema200) and ema200 > price: candidates_res.append({'val': ema200, 'label': f"EMA 200 ({tf_label} - ต้านใหญ่)"})
            if not np.isnan(bb_upper) and bb_upper > price: candidates_res.append({'val': bb_upper, 'label': f"BB Upper ({tf_label} - เพดาน)"})
            
            if not df_stats_day.empty:
                d_ema50 = ta.ema(df_stats_day['Close'], length=50).iloc[-1]
                if d_ema50 > price: candidates_res.append({'val': d_ema50, 'label': "EMA 50 (TF Day)"})
                high_60d = df_stats_day['High'].tail(60).max()
                if high_60d > price: candidates_res.append({'val': high_60d, 'label': "🏔️ High 60d (ดอย 3 เดือน)"})

            if not df_stats_week.empty:
                w_ema50 = ta.ema(df_stats_week['Close'], length=50).iloc[-1]
                w_ema200 = ta.ema(df_stats_week['Close'], length=200).iloc[-1]
                if w_ema50 > price: candidates_res.append({'val': w_ema50, 'label': "EMA 50 (TF Week - ต้านระยะยาว)"})
                if w_ema200 > price: candidates_res.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - ต้านระดับกองทุน)"})
                
            if supply_zones:
                for z in supply_zones: candidates_res.append({'val': z['top'], 'label': f"Supply Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})

            candidates_res.sort(key=lambda x: x['val'])

            merged_res = []
            skip_next = False
            for i in range(len(candidates_res)):
                if skip_next: skip_next = False; continue
                current = candidates_res[i]
                if i < len(candidates_res) - 1:
                    next_item = candidates_res[i+1]
                    if (next_item['val'] - current['val']) / current['val'] < 0.01:
                        new_label = f"⭐ Confluence Zone ({current['label']} + {next_item['label']})"
                        merged_res.append({'val': current['val'], 'label': new_label})
                        skip_next = True
                        continue
                merged_res.append(current)

            final_show_res = []
            for item in merged_res:
                if (item['val'] - price) / price > 0.30 and "EMA 200 (TF Week" not in item['label']: continue
                is_vip = "EMA 200" in item['label'] or "EMA 50 (TF Week" in item['label']
                if not final_show_res: final_show_res.append(item)
                else:
                    last_item = final_show_res[-1]
                    dist = abs(item['val'] - last_item['val'])
                    if is_vip or dist >= min_dist:
                        final_show_res.append(item)

            st.markdown("#### 🔴 แนวต้าน"); 
            if final_show_res: 
                for item in final_show_res[:4]: st.write(f"- **{item['val']:.2f} :** {item['label']}")
            else: st.write("- N/A (Blue Sky)")

        with c_ai:
            st.subheader("🔬 Price Action X-Ray")
            
            sq_col = "#f97316" if ai_report['is_squeeze'] else "#0369a1"
            sq_txt = "⚠️ Squeeze (อัดอั้นรอระเบิด)" if ai_report['is_squeeze'] else "Normal (ปกติ)"
            vol_q_col = ai_report['vol_quality_color']
            vol_txt = ai_report['vol_quality_msg']
            obv_col = "#22c55e" if "Bullish" in ai_report['obv_insight'] else ("#ef4444" if "Bearish" in ai_report['obv_insight'] else "#6b7280")
            dz_status = "✅ อยู่ในโซน (In Zone)" if ai_report['in_demand_zone'] else "❌ นอกโซน (รอราคา)"
            
            st.markdown(f"""
            <div class='xray-box'>
                <div class='xray-title'>🕯️ Deep Insight</div>
                <div class='xray-item'><span>ทรงกราฟ:</span> <span style='font-weight:bold;'>{ai_report['candle_pattern']}</span></div>
                <div class='xray-item'><span>สถานะ:</span> <span>{ai_report['candle_color']}</span></div>
                <div class='xray-item'><span>รายละเอียด:</span> <span style='font-style:italic;'>{ai_report['candle_detail']}</span></div>
                <hr style='margin: 8px 0; opacity: 0.3;'>
                <div class='xray-item'><span>🔥 ความผันผวน (BB):</span> <span style='color:{sq_col}; font-weight:bold;'>{sq_txt}</span></div>
                <div class='xray-item'><span>📊 คุณภาพ Volume:</span> <span style='color:{vol_q_col}; font-weight:bold;'>{vol_txt}</span></div>
                <div class='xray-item'><span>🌊 รายใหญ่ (OBV):</span> <span style='color:{obv_col}; font-weight:bold;'>{ai_report['obv_insight']}</span></div>
                <div class='xray-item'><span>🎯 Demand Zone:</span> <span style='font-weight:bold;'>{dz_status}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader("🤖 AI STRATEGY (Hybrid)")
            color_map = {"green": {"bg": "#dcfce7", "border": "#22c55e", "text": "#14532d"}, "red": {"bg": "#fee2e2", "border": "#ef4444", "text": "#7f1d1d"}, "orange": {"bg": "#ffedd5", "border": "#f97316", "text": "#7c2d12"}, "yellow": {"bg": "#fef9c3", "border": "#eab308", "text": "#713f12"}}
            c_theme = color_map.get(ai_report['status_color'], color_map["yellow"])
            st.markdown(f"""<div style="background-color: {c_theme['bg']}; border-left: 6px solid {c_theme['border']}; padding: 20px; border-radius: 10px; margin-bottom: 20px;"><h2 style="color: {c_theme['text']}; margin:0 0 10px 0; font-size: 28px;">{ai_report['banner_title']}</h2><h3 style="color: {c_theme['text']}; margin:0 0 15px 0; font-size: 20px; opacity: 0.9;">{ai_report['strategy']}</h3><p style="color: {c_theme['text']}; font-size: 16px; margin:0; line-height: 1.6;"><b>💡 Insight:</b> {ai_report['context']}</p></div>""", unsafe_allow_html=True)
            with st.chat_message("assistant"):
                if ai_report['bullish_factors']: 
                    st.markdown("**🟢 ปัจจัยบวก:**")
                    for r in ai_report['bullish_factors']: st.write(f"- {r}")
                if ai_report['bearish_factors']: 
                    st.markdown("**🔴 ปัจจัยลบ/ความเสี่ยง:**")
                    for w in ai_report['bearish_factors']: st.write(f"- {w}")
                
                st.markdown("---")
                if "green" in ai_report['status_color']: box_type = st.success
                elif "red" in ai_report['status_color']: box_type = st.error
                else: box_type = st.warning
                
                box_type(f"""
                ### 📝 บทสรุปและคำแนะนำ (Action Plan)
                
                **1. สถานการณ์ (Context):** {ai_report['context']}
                
                **2. คำแนะนำ (Action):** 👉 **{ai_report['strategy']}** : {ai_report['holder_advice']}
                
                **3. แผนการเทรด (Setup):** 🛑 **Stop Loss (หนี):** {ai_report['sl']:.2f}  |  ✅ **Take Profit (เป้า):** {ai_report['tp']:.2f}
                """)

        st.write(""); st.markdown("""<div class='disclaimer-box'>⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากการวิเคราะห์ทางเทคนิคด้วยระบบ AI เพื่อประกอบการตัดสินใจเท่านั้น</div>""", unsafe_allow_html=True); st.divider()
        st.subheader("📜 History Log")
        if st.session_state['history_log']: st.dataframe(pd.DataFrame(st.session_state['history_log']), use_container_width=True, hide_index=True)

    else: st.error("ไม่พบข้อมูลหุ้น หรือข้อมูลไม่เพียงพอสำหรับคำนวณ Swing Low")



