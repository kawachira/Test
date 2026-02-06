import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# --- Import สำหรับ Google Sheets ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. ตั้งค่าหน้าเว็บ (The Master Version) ---
st.set_page_config(page_title="AI Stock Master (God Mode)", page_icon="💎", layout="wide")

# --- Initialize Session State (กันจอหาย + ประวัติ) ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = []

if 'search_triggered' not in st.session_state:
    st.session_state['search_triggered'] = False

if 'last_symbol' not in st.session_state:
    st.session_state['last_symbol'] = ""

# --- 2. CSS ปรับแต่ง (Clean & Professional - คงเดิมตามสั่ง) ---
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
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>Ultimate Sniper (God Mode Contextual)🚀</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input_raw = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB,TSLA)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
            else: tf_code = "1d"; mtf_code = "1wk"
        
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Helper Functions (Visuals & Data) ---

def analyze_candlestick(df_window):
    """
    ฟังก์ชันอ่านแท่งเทียน Pro Max (4-Bar Logic)
    รับค่า: DataFrame ย้อนหลัง 4 แท่ง (Index 0=ไกลสุด, 3=ล่าสุด)
    """
    # 1. กัน Error: ถ้าข้อมูลส่งมาไม่ครบ 4 แท่ง ให้ตอบค่ากลางๆ
    if len(df_window) < 4: 
        return "Normal Candle", "gray", "ข้อมูลไม่เพียงพอ", False

    # 2. แยกชิ้นส่วน 4 วัน (เพื่อให้เขียน Logic ง่าย)
    c1 = df_window.iloc[0] # 3 วันก่อน
    c2 = df_window.iloc[1] # 2 วันก่อน
    c3 = df_window.iloc[2] # เมื่อวาน (Prev)
    c4 = df_window.iloc[3] # วันนี้ (Current)

    # ดึงค่าตัวเลขวันนี้
    open_p = c4['Open']; close_p = c4['Close']
    high_p = c4['High']; low_p = c4['Low']
    body = abs(close_p - open_p)
    range_len = high_p - low_p
    is_bull = close_p >= open_p
    color = "🟢 เขียว (Buying)" if is_bull else "🔴 แดง (Selling)"

    # ดึงค่าตัวเลขเมื่อวาน
    prev_open = c3['Open']; prev_close = c3['Close']
    is_prev_bull = prev_close >= prev_open

    pattern_name = "Normal Candle (ปกติ)"
    detail = "แรงซื้อขายสมดุล"
    is_big = False

    # --- 🧠 LEVEL 1: รูปแบบกลุ่ม 3-4 แท่ง (แม่นยำสูง) ---

    # 1. Three Black Crows (อีกา 3 ตัว - ขาลงรุนแรง)
    if (c2['Close'] < c2['Open']) and (c3['Close'] < c3['Open']) and (c4['Close'] < c4['Open']):
        if (c4['Close'] < c3['Close']) and (c3['Close'] < c2['Close']):
            return "🦅 Three Black Crows (อีกา 3 ตัว)", "🔴 แดง (Selling)", "แรงขายทุบต่อเนื่อง 3 วัน (ระวังลงลึก)", True

    # 2. Three White Soldiers (3 ทหารเสือ - ขาขึ้นรุนแรง)
    if (c2['Close'] > c2['Open']) and (c3['Close'] > c3['Open']) and (c4['Close'] > c4['Open']):
        if (c4['Close'] > c3['Close']) and (c3['Close'] > c2['Close']):
            return "💂 Three White Soldiers (3 ทหารเสือ)", "🟢 เขียว (Buying)", "แรงซื้อดันต่อเนื่อง 3 วัน (แข็งแกร่ง)", True

    # 3. Morning Star (กลับตัวขึ้น)
    c2_body = abs(c2['Close'] - c2['Open']); c2_range = c2['High'] - c2['Low']
    if (c2['Close'] < c2['Open']) and (c2_body > c2_range * 0.5): # แท่ง 1 แดงยาว
        if abs(c3['Close'] - c3['Open']) < c2_body * 0.4: # แท่ง 2 ตัวเล็ก (Star)
            midpoint = (c2['Open'] + c2['Close']) / 2
            if (c4['Close'] > c4['Open']) and (c4['Close'] > midpoint): # แท่ง 3 เขียวสวนเกินครึ่ง
                return "🌅 Morning Star (รุ่งอรุณ)", "🟢 เขียว (Buying)", "กลับตัวขึ้นสวยงาม (Confirm Reversal)", True

    # 4. Evening Star (กลับตัวลง)
    if (c2['Close'] > c2['Open']) and (c2_body > c2_range * 0.5): # แท่ง 1 เขียวยาว
        if abs(c3['Close'] - c3['Open']) < c2_body * 0.4: # แท่ง 2 ตัวเล็ก
            midpoint = (c2['Open'] + c2['Close']) / 2
            if (c4['Close'] < c4['Open']) and (c4['Close'] < midpoint): # แท่ง 3 แดงสวนลงมา
                return "🌆 Evening Star (พลบค่ำ)", "🔴 แดง (Selling)", "กลับตัวลงชัดเจน (Confirm Reversal)", True

    # --- 🧠 LEVEL 2: รูปแบบ 2 แท่ง (Engulfing) ---
    
    # Bearish Engulfing
    if is_prev_bull and not is_bull: # เมื่อวานเขียว วันนี้แดง
        if (open_p >= prev_close) and (close_p <= prev_open):
            return "🐻 Bearish Engulfing (กลืนกินขาลง)", "🔴 แดง (Selling)", "แท่งแดงกลบแท่งเขียวเมื่อวาน", True

    # Bullish Engulfing
    if not is_prev_bull and is_bull: # เมื่อวานแดง วันนี้เขียว
        if (open_p <= prev_close) and (close_p >= prev_open):
            return "🐂 Bullish Engulfing (กลืนกินขาขึ้น)", "🟢 เขียว (Buying)", "แท่งเขียวกลบแท่งแดงเมื่อวาน", True

    # --- 🧠 LEVEL 3: รูปแบบแท่งเดียว (Basic) ---
    
    wick_up = high_p - max(close_p, open_p)
    wick_low = min(close_p, open_p) - low_p
    
    if wick_low > (body * 2) and wick_up < body:
        pattern_name = "🔨 Hammer/Pinbar (ค้อน)"
        detail = "ปฏิเสธราคาต่ำ (แรงซื้อสวน)"
    elif wick_up > (body * 2) and wick_low < body:
        pattern_name = "☄️ Shooting Star (ดาวตก)"
        detail = "ปฏิเสธราคาสูง (แรงขายตบ)"
    elif body > (range_len * 0.6): 
        is_big = True
        pattern_name = "Big Bullish (แท่งเขียวตัน)" if is_bull else "Big Bearish (แท่งแดงตัน)"
        detail = "แรงซื้อ/ขาย คุมตลาดเบ็ดเสร็จ"
    elif body < (range_len * 0.1):
        pattern_name = "Doji (โดจิ)"
        detail = "ตลาดลังเล (Indecision)"
        
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
    color_code = "#16a34a" if color_status == "green" else "#dc2626" if color_status == "red" else "#a3a3a3"
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

def get_rsi_interpretation(rsi, is_trending_mode):
    if np.isnan(rsi): return "N/A"
    if is_trending_mode:
        if rsi >= 75: return "Super Bullish (แรงสุดๆ)"
        elif rsi <= 45: return "Dip Opportunity (ย่อซื้อ)"
        else: return "Trending"
    else: # Sideways
        if rsi >= 65: return "Overbought (ระวังแรงขาย)"
        elif rsi <= 35: return "Oversold (ระวังเด้งสวน)"
        else: return "Neutral"

def get_adx_interpretation(adx, is_uptrend):
    if np.isnan(adx): return "N/A"
    trend_str = "ขาขึ้น" if is_uptrend else "ขาลง"
    if adx >= 50: return f"Super Strong {trend_str} (แรงมาก)"
    if adx >= 25: return f"Strong {trend_str} (แข็งแกร่ง)"
    return "Weak/Sideway (ตลาดไร้ทิศทาง)"

# --- Google Sheets Function ---
# --- แก้ไขฟังก์ชัน save_to_gsheet ให้รับค่าครบทุกช่อง ---
def save_to_gsheet(data_dict):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open("Stock_Analysis_Log").sheet1
            
            # จัดเรียงข้อมูลลงคอลัมน์ (ต้องตรงกับ Log Entry)
            row = [
                datetime.now().strftime("%Y-%m-%d"), # A: วันที่
                data_dict.get("เวลา", ""),           # B: เวลา
                data_dict.get("หุ้น", ""),           # C: ชื่อหุ้น
                data_dict.get("TF", ""),             # D: Timeframe (เพิ่มใหม่)
                data_dict.get("ราคา", ""),           # E: ราคา
                data_dict.get("Change%", ""),        # F: % เปลี่ยนแปลง (เพิ่มใหม่)
                data_dict.get("สถานะ", ""),          # G: สถานะ (เพิ่มใหม่)
                data_dict.get("Action", ""),         # H: คำแนะนำ
                data_dict.get("SL", ""),             # I: Stop Loss (เพิ่มใหม่)
                data_dict.get("TP", "")              # J: Take Profit (เพิ่มใหม่)
            ]
            sheet.append_row(row)
            return True
        return False
    except Exception as e:
        return False
# --- SMC: Find Zones ---
def find_demand_zones(df, atr_multiplier=0.25):
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
            zones.append({'bottom': zone_bottom, 'top': zone_top})
    return zones

def find_supply_zones(df, atr_multiplier=0.25):
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
        if (zone_bottom - current_price) / current_price > 0.20: continue
        future_data = df.loc[date:][1:]
        if future_data.empty: continue
        if not (future_data['Close'] > zone_top).any():
            zones.append({'bottom': zone_bottom, 'top': zone_top})
    return zones

# --- 5. Data Fetching ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "10y" if interval == "1wk" else "5y" if interval == "1d" else "730d"
        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval)
        if not df_mtf.empty: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
        
        try: raw_info = ticker.info 
        except: raw_info = {} 

        df_daily = ticker.history(period="5d", interval="1d")
        if not df_daily.empty:
            price = df_daily['Close'].iloc[-1]
            chg = price - df_daily['Close'].iloc[-2] if len(df_daily) >=2 else 0
            pct = (chg / df_daily['Close'].iloc[-2]) if len(df_daily) >=2 else 0
            d_h, d_l, d_o = df_daily['High'].iloc[-1], df_daily['Low'].iloc[-1], df_daily['Open'].iloc[-1]
        else:
            price = df['Close'].iloc[-1]; chg = 0; pct = 0; d_h=0; d_l=0; d_o=0

        info_dict = {
            'longName': raw_info.get('longName', symbol), 
            'marketState': raw_info.get('marketState', 'REGULAR'), 
            'regularMarketPrice': price, 'regularMarketChange': chg,
            'regularMarketChangePercent': pct, 'dayHigh': d_h, 'dayLow': d_l, 'regularMarketOpen': d_o,
            'preMarketPrice': raw_info.get('preMarketPrice'), 'preMarketChange': raw_info.get('preMarketChange'),
            'postMarketPrice': raw_info.get('postMarketPrice'), 'postMarketChange': raw_info.get('postMarketChange'),
        }
        return df, info_dict, df_mtf
    except: return None, None, None

def analyze_volume(row, vol_ma):
    vol = row['Volume']
    if np.isnan(vol_ma) or vol_ma == 0: return "☁️ ปกติ", "gray"
    pct = (vol / vol_ma) * 100
    if pct >= 250: return f"💣 สูงมาก/ระเบิด ({pct:.0f}%)", "#7f1d1d"
    elif pct >= 120: return f"🔥 สูง/คึกคัก ({pct:.0f}%)", "#16a34a"
    elif pct <= 70: return f"🌵 ต่ำ/เบาบาง ({pct:.0f}%)", "#f59e0b"
    else: return f"☁️ ปกติ ({pct:.0f}%)", "gray"

# --- 7. AI Decision Engine (THE UPGRADED BRAIN - GOD MODE) ---
# ระบบสมองใหม่: Contextual Scoring + 4-Bar Pattern + Volume Filter + Trend Integration

def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, 
                       vol_status, mtf_trend, atr_val, mtf_ema200_val,
                       open_price, high, low, close, obv_val, obv_avg,
                       obv_slope, prev_open, prev_close, vol_now, vol_avg, demand_zones,
                       is_squeeze, df_candles): # <--- รับ 4 แท่งตรงนี้

    def safe(x): return float(x) if not np.isnan(float(x)) else np.nan
    price = safe(price); ema20 = safe(ema20); ema50 = safe(ema50); ema200 = safe(ema200)
    atr_val = safe(atr_val); obv_slope = safe(obv_slope); vol_now = safe(vol_now); vol_avg = safe(vol_avg)

    # 1. 🔬 Deep Vision: อ่านแท่งเทียน 4 แท่งแบบละเอียด
    candle_pattern, candle_color, candle_detail, is_big_candle = analyze_candlestick(df_candles)
    
    is_reversal_up = any(x in candle_pattern for x in ["Hammer", "Bullish Engulfing", "Morning Star", "Three White Soldiers"])
    is_reversal_down = any(x in candle_pattern for x in ["Shooting Star", "Bearish Engulfing", "Evening Star", "Three Black Crows"])
    
    is_shooting_star = "Shooting Star" in candle_pattern

    # Volume Logic (Smart Check)
    is_vol_dry = vol_now < (vol_avg * 0.8) # วอลุ่มแห้ง (พักตัวดี)
    is_vol_climax = vol_now > (vol_avg * 2.0) # วอลุ่มระเบิด (ระวังจบแรลลี่)
    vol_txt, vol_col = analyze_volume({'Volume': vol_now}, vol_avg)

    # 2. 🏗️ Zone Checking (Buffer 1.5%)
    in_demand_zone = False; active_zone = None; confluence_msg = ""
    if demand_zones:
        for zone in demand_zones:
            if (low <= zone['top'] * 1.015) and (high >= zone['bottom']):
                in_demand_zone = True; active_zone = zone; break
    
    is_confluence = False
    if in_demand_zone:
        if not np.isnan(ema200) and abs(active_zone['bottom'] - ema200) / price < 0.02: is_confluence = True; confluence_msg = "Zone + EMA 200"
        elif not np.isnan(ema50) and abs(active_zone['bottom'] - ema50) / price < 0.02: is_confluence = True; confluence_msg = "Zone + EMA 50"

    # 3. 🌊 Regime Filter (ADX & Trend)
    is_strong_trend = adx > 25 if not np.isnan(adx) else False
    is_major_uptrend = price > ema200 if not np.isnan(ema200) else True

    # --- 🧠 CONTEXTUAL SCORING SYSTEM (God Mode) ---
    score = 0
    bullish = []
    bearish = []
    ctx = ""

    # A. 🏛️ Structural Score (โครงสร้างพื้นฐาน)
    if not np.isnan(ema200):
        if price > ema200: score += 3; bullish.append("Structure: ยืนเหนือ EMA 200 (ขาขึ้นระยะยาว)")
        else: score -= 3; bearish.append("Structure: หลุด EMA 200 (ขาลงระยะยาว)")

    if not np.isnan(ema50):
        if price > ema50: score += 2; bullish.append("Structure: ยืนเหนือ EMA 50 (แกร่งระยะกลาง)")
        else: score -= 1; bearish.append("Structure: หลุด EMA 50 (เสียทรงระยะกลาง)")

    # B. 🕯️ Price Action Score (ตัดสินใจด้วย 4 แท่ง + บริบท)
    # --- กลุ่มสัญญาณลบ (Bearish) ---
    if "Three Black Crows" in candle_pattern:
        score -= 3 # โดนหนัก
        bearish.append("🦅 Three Black Crows: แรงขายทุบ 3 วันติด (อันตราย)")
        ctx = "🩸 Panic Dump: หนีตาย (เจ้ามือทิ้งของ)" # Veto

    elif "Evening Star" in candle_pattern:
        score -= 2
        bearish.append("🌆 Evening Star: กลับตัวลงสมบูรณ์แบบ")
        if score < 2: ctx = "📉 Reversal: สัญญาณกลับตัวลงชัดเจน"

    elif "Bearish Engulfing" in candle_pattern:
        # Contextual Check: วอลุ่มและการย่อตัว
        if is_vol_climax: 
            score -= 3 # วอลุ่มพีค = เจ้าทิ้ง
            bearish.append("🐻 Bearish Engulfing + Vol Peak (เจ้ามือทิ้งของ)")
            ctx = "🩸 Panic Sell: แรงขายมหาศาล"
        elif is_major_uptrend and is_vol_dry:
            score += 1 # พลิกวิกฤตเป็นโอกาส
            bullish.append("🐂 Bullish Pullback: แท่งแดงวอลุ่มแห้ง (ย่อเพื่อไปต่อ)")
        else:
            score -= 2 # ปกติ
            bearish.append("⚠️ Bearish Engulfing: แรงขายชนะแรงซื้อ")

    elif is_shooting_star:
        if price > bb_up: # ชน Bollinger Band บน
            score -= 2
            bearish.append("☄️ Shooting Star: โดนตบที่แนวต้าน BB (Overbought)")
        else:
            score -= 1
            bearish.append("☄️ Shooting Star: มีแรงขายกดดันข้างบน")

    # --- กลุ่มสัญญาณบวก (Bullish) ---
    if "Three White Soldiers" in candle_pattern:
        score += 3
        bullish.append("💂 Three White Soldiers: แรงซื้อ 3 วันติด (แข็งแกร่งมาก)")

    elif "Morning Star" in candle_pattern:
        if in_demand_zone:
            score += 3 # คูณพิเศษ
            bullish.append("🌅 Morning Star (in Zone): จุดกลับตัวต้นน้ำสวยงาม")
        else:
            score += 2
            bullish.append("🌅 Morning Star: กลับตัวขึ้นสมบูรณ์")

    elif "Bullish Engulfing" in candle_pattern:
        # Contextual Check: วอลุ่มและตำแหน่ง
        if rsi > 70: # ซื้อยอดดอย
            score -= 1
            bearish.append("⚠️ Bullish Trap: เขียวที่ยอดดอย (RSI Overbought)")
        elif is_vol_climax:
            score += 3
            bullish.append("🚀 Power Buy: แท่งเขียวกลืนกิน + วอลุ่มระเบิด")
        else:
            score += 2
            bullish.append("🐂 Bullish Engulfing: แรงซื้อชนะแรงขาย")

    # C. 📊 Volume & Flow Analysis (Smart OBV)
    obv_strength_pct = 0
    if vol_avg > 0 and not np.isnan(obv_slope):
        obv_strength_pct = (obv_slope / vol_avg) * 100
    
    obv_insight = f"Flow ปกติ ({obv_strength_pct:.1f}%)"

    if obv_strength_pct > 5: # เงินเข้า
        if obv_strength_pct > 60: obv_insight = f"🚀 กวาดซื้อ ({obv_strength_pct:.1f}%)"
        else: obv_insight = f"💎 เก็บของ ({obv_strength_pct:.1f}%)"
        
        # Bullish Divergence Check
        if price < ema20: # ราคาลงแต่เงินเข้า
            score += 2
            bullish.append(f"Bullish Divergence: ราคาลงแต่เงินเข้า ({obv_strength_pct:.1f}%)")
            obv_insight = "Bullish Div (เก็บของ)"
        else:
            score += 1
            bullish.append(f"Fund Flow: เงินไหลเข้าต่อเนื่อง")

    elif obv_strength_pct < -5: # เงินออก
        if obv_strength_pct < -60: obv_insight = f"🩸 ทิ้งของ ({obv_strength_pct:.1f}%)"
        else: obv_insight = f"💧 รินขาย ({obv_strength_pct:.1f}%)"

        # Bearish Divergence Check
        if price > ema20: # ราคาขึ้นแต่เงินออก
            score -= 2
            bearish.append(f"Bearish Divergence: ราคาขึ้นแต่เงินออก ({obv_strength_pct:.1f}%)")
            obv_insight = "Bearish Div (รินขาย)"
        else:
            score -= 1
            bearish.append(f"Fund Flow: เงินไหลออกต่อเนื่อง")

    # D. ⚡ Momentum & Indicators (RSI/MACD)
    if not np.isnan(macd_val) and macd_val > macd_sig: score += 1; bullish.append("MACD ตัดขึ้น")
    elif not np.isnan(macd_val): score -= 1

    # RSI Context
    if not np.isnan(rsi):
        if is_strong_trend and is_major_uptrend:
            if rsi > 75 and not is_vol_climax: score += 1; bullish.append(f"RSI {rsi:.0f}: Super Bullish Trend") # Run trend
            elif rsi < 45: score += 2; bullish.append(f"RSI {rsi:.0f}: Dip Opportunity (ย่อซื้อ)")
        else: # Sideway
            if rsi > 65: score -= 2; bearish.append(f"RSI {rsi:.0f}: Overbought (ระวังต้าน)")
            elif rsi < 30: score += 2; bullish.append(f"RSI {rsi:.0f}: Oversold (รอเด้ง)")

    # E. 🛡️ Special Context (Veto Rules)
    if in_demand_zone:
        score += 3; bullish.append("🟢 In Demand Zone (ต้นทุนดี)")
        if is_confluence: score += 1; bullish.append(f"⭐ {confluence_msg}")
        if not ctx: ctx = "💎 Sniper Mode (เข้าโซนสวย)"

    # Final Context Generation
    if ctx == "":
        if score >= 5: ctx = "🚀 Bullish Breakout: โมเมนตัมกระทิงดุ"
        elif score >= 2: ctx = "📈 Uptrend Structure: ย่อตัวเพื่อขึ้นต่อ"
        elif score <= -4: ctx = "🩸 Bearish Crash: แรงขายรุนแรง (ห้ามรับ)"
        elif score <= -1: ctx = "📉 Downtrend Pressure: เด้งเพื่อลง"
        else: ctx = "⚖️ Sideway/Neutral: รอเลือกทาง"

    # --- FINAL STATUS ASSIGNMENT ---
    if score >= 6:
        color = "green"; title = "🚀 Sniper Entry: จุดซื้อคมกริบ"; strat = "Aggressive Buy"
        adv = f"โมเมนตัมแรงจัด Pattern สวย ถือรันเทรนด์ SL: {low-(atr_val*1.0):.2f}"
    elif score >= 4:
        if "Pullback" in ctx or "Dip" in str(bullish):
            color = "green"; title = "🐂 Bullish Pullback: ย่อเพื่อไปต่อ"; strat = "Buy on Dip"
            adv = "ราคาย่อตัวในขาขึ้น วอลุ่มแห้ง/RSI ต่ำ เป็นจังหวะเก็บของที่ดีที่สุด"
        else:
            color = "green"; title = "🐂 Strong Buy: ขาขึ้นแข็งแกร่ง"; strat = "Accumulate"
            adv = "เทรนด์หลักเป็นขาขึ้น ย่อตัวน่าสนใจ"
    elif score >= 1:
        if "Sideway Up" in ctx:
            color = "yellow"; title = "⚖️ Sideway Up: สะสมพลัง"; strat = "Accumulate"
            adv = "ราคาออกข้างแต่เงินไหลเข้า ดักเก็บที่แนวรับ ลุ้นเบรค"
        else:
            color = "yellow"; title = "⚖️ Neutral: รอความชัดเจน"; strat = "Wait & Watch"
            adv = "ปัจจัยขัดแย้งกัน (เช่น เทรนด์ดีแต่เจอแท่งเทียนกลับตัว) นั่งทับมือไปก่อน"
    elif score <= -4:
        if "Panic" in ctx:
            color = "red"; title = "💀 Panic Sell: หนีตาย"; strat = "Exit Immediately"
            adv = "วงแตก! แรงขายระดับวิกฤต (3 Crows / Vol Peak) ห้ามรับเด็ดขาด"
        else:
            color = "red"; title = "🩸 Falling Knife: มีดหล่น"; strat = "Avoid / Cut Loss"
            adv = "ราคาดิ่งแรง หลุดแนวรับสำคัญ รอให้หยุดลงและสร้างฐานก่อน"
    else: # Score 0 to -3
        color = "orange"; title = "🐻 Bearish Pressure: แรงกดดันสูง"; strat = "Reduce Port"
        adv = "แรงขายมากกว่าแรงซื้อ ระวังหลุดแนวรับ ไม่ควรรีบรับจนกว่าจะเห็นสัญญาณกลับตัว"

    if in_demand_zone: sl = active_zone['bottom'] - (atr_val*0.5)
    else: sl = price - (2*atr_val) if not np.isnan(atr_val) else price*0.95
    tp = price + (3*atr_val) if not np.isnan(atr_val) else price*1.05

    return {
        "status_color": color, "banner_title": title, "strategy": strat, "context": ctx,
        "bullish_factors": bullish, "bearish_factors": bearish, "sl": sl, "tp": tp, "holder_advice": adv,
        "candle_pattern": candle_pattern, "candle_color": candle_color, "candle_detail": candle_detail,
        "vol_quality_msg": vol_txt, "vol_quality_color": vol_col,
        "in_demand_zone": in_demand_zone, "confluence_msg": confluence_msg,
        "is_squeeze": is_squeeze, "obv_insight": obv_insight
    }
# --- 8. Main Execution & Display (ส่วนแสดงผลหลัก) ---

# 1. อัปเดต State เมื่อกดปุ่มค้นหา
if submit_btn:
    st.session_state['search_triggered'] = True
    st.session_state['last_symbol'] = symbol_input_raw

# 2. เริ่มทำงานถ้ามีการ Trigger
if st.session_state['search_triggered']:
    symbol_input = st.session_state['last_symbol']
    
    st.divider()
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)
    
    with st.spinner(f"AI God Mode กำลังเจาะลึก {symbol_input} (Analyzing 4-Bar Pattern & Context)..."):
        # 1. Main Data
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)
        
        # 2. Safety Net Data
        try:
            ticker_stats = yf.Ticker(symbol_input)
            df_stats_day = ticker_stats.history(period="2y", interval="1d")
            df_stats_week = ticker_stats.history(period="5y", interval="1wk")
        except:
            df_stats_day = pd.DataFrame(); df_stats_week = pd.DataFrame()

    if df is not None and not df.empty and len(df) > 20: 
        # --- Indicator Calculation ---
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50)
        
        ema200_series = ta.ema(df['Close'], length=200)
        df['EMA200'] = ema200_series if ema200_series is not None else np.nan

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        macd = ta.macd(df['Close'])
        if macd is not None: df = pd.concat([df, macd], axis=1)
        
        bbands = ta.bbands(df['Close'], length=20, std=2)
        if bbands is not None and len(bbands.columns) >= 3:
            bbl_col_name, bbu_col_name = bbands.columns[0], bbands.columns[2]
            df = pd.concat([df, bbands], axis=1)
        else: bbl_col_name, bbu_col_name = None, None
        
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        if adx is not None: df = pd.concat([df, adx], axis=1)
        
        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
        
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['OBV_SMA20'] = ta.sma(df['OBV'], length=20)
        df['OBV_Slope'] = ta.slope(df['OBV'], length=5) 
        
        df['Rolling_Min'] = df['Low'].rolling(window=20).min()
        df['Rolling_Max'] = df['High'].rolling(window=20).max()
        
        if bbu_col_name and bbl_col_name and 'EMA20' in df.columns:
            df['BB_Width'] = (df[bbu_col_name] - df[bbl_col_name]) / df['EMA20'] * 100
            df['BB_Width_Min20'] = df['BB_Width'].rolling(window=20).min()
            is_squeeze = df['BB_Width'].iloc[-1] <= (df['BB_Width_Min20'].iloc[-1] * 1.1) 
        else:
            is_squeeze = False

        demand_zones = find_demand_zones(df, atr_multiplier=0.25)
        supply_zones = find_supply_zones(df, atr_multiplier=0.25)
        
        last = df.iloc[-1]
        price = info.get('regularMarketPrice') if info.get('regularMarketPrice') else last['Close']
        ema20 = last['EMA20'] if 'EMA20' in last else np.nan
        ema50 = last['EMA50'] if 'EMA50' in last else np.nan
        ema200 = last['EMA200'] if 'EMA200' in last else np.nan
        
        if tf_code == "1wk":
            if ema200 is None or (isinstance(ema200, float) and np.isnan(ema200)):
                st.error(f"⚠️ **ข้อมูลไม่เพียงพอสำหรับ TF Week** (ต้องการ 200 สัปดาห์)")
                st.stop() 

        rsi = last['RSI'] if 'RSI' in last else np.nan
        atr = last['ATR'] if 'ATR' in last else np.nan
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
        
        mtf_trend = "Sideway"; mtf_ema200_val = 0
        if df_mtf is not None and not df_mtf.empty:
            if 'EMA200' not in df_mtf.columns: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
            if len(df_mtf) > 200 and not pd.isna(df_mtf['EMA200'].iloc[-1]):
                mtf_ema200_val = df_mtf['EMA200'].iloc[-1]
                if df_mtf['Close'].iloc[-1] > mtf_ema200_val: mtf_trend = "Bullish"
                else: mtf_trend = "Bearish"
        
        try: prev_open = df['Open'].iloc[-2]; prev_close = df['Close'].iloc[-2]; vol_avg = last['Vol_SMA20']
        except: prev_open = 0; prev_close = 0; vol_avg = 1

        # 🔑 ตัดข้อมูล 4 แท่ง
        df_candles_4 = df.iloc[-4:] 

        # 🧠 CALL GOD MODE BRAIN
        ai_report = ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, 
                                       vol_status, mtf_trend, atr, mtf_ema200_val,
                                       open_p, high_p, low_p, close_p, obv_val, obv_avg,
                                       obv_slope_val, 
                                       prev_open, prev_close, vol_now, vol_avg, demand_zones, 
                                       is_squeeze,
                                       df_candles_4)

        # --- LOG MANAGEMENT ---
        current_time = datetime.now().strftime("%H:%M:%S")
        pct_change = info.get('regularMarketChangePercent', 0)
        pct_str = f"{pct_change * 100:+.2f}%" if pct_change is not None else "0.00%"

        raw_strat = ai_report['strategy']
        if "Aggressive Buy" in raw_strat: th_action = "ลุยซื้อ (Aggressive)"
        elif "Buy on Dip" in raw_strat: th_action = "ย่อซื้อ (Dip)"
        elif "Accumulate" in raw_strat: th_action = "ทยอยสะสม"
        elif "Wait" in raw_strat: th_action = "รอจังหวะ"
        elif "No Trade" in raw_strat: th_action = "ทับมือ (ห้ามเล่น)"
        elif "Exit" in raw_strat: th_action = "หนีตาย (Exit)"
        elif "Reduce" in raw_strat: th_action = "ลดพอร์ต"
        elif "Sell" in raw_strat: th_action = "เด้งขาย"
        else: th_action = raw_strat 

        raw_color = ai_report['status_color']
        if raw_color == "green": th_score = "🟢 ขาขึ้น"
        elif raw_color == "red": th_score = "🔴 ขาลง"
        elif raw_color == "orange": th_score = "🟠 เสี่ยง"
        else: th_score = "🟡 พักตัว"

        log_entry = { 
            "เวลา": current_time, 
            "หุ้น": symbol_input, 
            "TF": timeframe, 
            "ราคา": f"{price:.2f}", 
            "Change%": pct_str,
            "สถานะ": th_score,
            "Action": th_action,
            "SL": f"{ai_report['sl']:.2f}", 
            "TP": f"{ai_report['tp']:.2f}"
        }
        
        if submit_btn: 
            st.session_state['history_log'].insert(0, log_entry)
            if len(st.session_state['history_log']) > 10: st.session_state['history_log'] = st.session_state['history_log'][:10]

        # --- DISPLAY UI ---
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
        elif st_color == "orange": c2.warning(f"⚠️ {main_status}\n\n**{tf_label}**")
        else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

        c3, c4 = st.columns(2)
        icon_flat_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#a3a3a3"><circle cx="12" cy="12" r="10"/></svg>"""
        with c3:
            rsi_str = f"{rsi:.2f}" if not np.isnan(rsi) else "N/A"; rsi_text = get_rsi_interpretation(rsi, adx_val > 25)
            st.markdown(custom_metric_html("⚡ RSI (14)", rsi_str, rsi_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        with c4:
            adx_disp = float(adx_val) if not np.isnan(adx_val) else np.nan
            if ema200 is not None and not np.isnan(ema200) and not np.isnan(adx_disp):
                is_uptrend = price >= ema200
                adx_text = get_adx_interpretation(adx_disp, is_uptrend)
                adx_str = f"{adx_disp:.2f}"
            else:
                is_uptrend = True 
                adx_str = "N/A"; adx_text = "N/A"
            st.markdown(custom_metric_html("💪 ADX Strength", adx_str, adx_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        
        st.write("") 
        c_ema, c_ai = st.columns([1.5, 2])
        with c_ema:
            st.subheader("📉 Technical Indicators")
            vol_str = format_volume(vol_now)
            e20_s = f"{ema20:.2f}" if not np.isnan(ema20) else "N/A"
            e50_s = f"{ema50:.2f}" if not np.isnan(ema50) else "N/A"
            e200_s = f"{ema200:.2f}" if (ema200 is not None and not np.isnan(ema200)) else "N/A"
            atr_pct = (atr / price) * 100 if not np.isnan(atr) and price > 0 else 0; atr_s = f"{atr:.2f} ({atr_pct:.1f}%)" if not np.isnan(atr) else "N/A"
            bb_s = f"{bb_upper:.2f} / {bb_lower:.2f}" if not np.isnan(bb_upper) else "N/A"

            st.markdown(f"""<div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'><div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd; font-weight:bold;'><span>Indicator</span> <span>Value</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{e20_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 50</span> <span>{e50_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{e200_s}</span></div><div style='display:flex; justify-content:space-between;'><span>Volume ({vol_str})</span> <span style='color:{ai_report['vol_quality_color']}'>{ai_report['vol_quality_msg']}</span></div><div style='display:flex; justify-content:space-between;'><span>ATR</span> <span>{atr_s}</span></div><div style='display:flex; justify-content:space-between;'><span>BB (Up/Low)</span> <span>{bb_s}</span></div></div>""", unsafe_allow_html=True)
            
            if tf_code == "1h": min_dist = atr * 1.0 
            elif tf_code == "1wk": min_dist = atr * 2.0 
            else: min_dist = atr * 1.5 

            st.subheader("🚧 Key Levels")
            
            # --- SUPPORTS ---
            candidates_supp = []
            if not np.isnan(ema20) and ema20 < price: candidates_supp.append({'val': ema20, 'label': f"EMA 20 ({tf_label} - ระยะสั้น)"})
            if not np.isnan(ema50) and ema50 < price: candidates_supp.append({'val': ema50, 'label': f"EMA 50 ({tf_label})"})
            if not np.isnan(ema200) and ema200 < price: candidates_supp.append({'val': ema200, 'label': f"EMA 200 ({tf_label} - Trend Support)"})
            if not np.isnan(bb_lower) and bb_lower < price: candidates_supp.append({'val': bb_lower, 'label': f"BB Lower ({tf_label} - แนวรับผันผวน)"})

            if not df_stats_day.empty:
                try: d_ema50 = ta.ema(df_stats_day['Close'], length=50).iloc[-1]
                except: d_ema50 = np.nan
                try: d_ema200 = ta.ema(df_stats_day['Close'], length=200).iloc[-1]
                except: d_ema200 = np.nan
                if not np.isnan(d_ema50) and d_ema50 < price: candidates_supp.append({'val': d_ema50, 'label': "EMA 50 (TF Day - รับระยะกลาง)"})
                if not np.isnan(d_ema200) and d_ema200 < price: candidates_supp.append({'val': d_ema200, 'label': "🛡️ EMA 200 (TF Day - รับใหญ่รายวัน)"})
            
            if not df_stats_week.empty:
                try: w_ema50 = ta.ema(df_stats_week['Close'], length=50).iloc[-1]
                except: w_ema50 = np.nan
                try: w_ema200 = ta.ema(df_stats_week['Close'], length=200).iloc[-1]
                except: w_ema200 = np.nan
                if not np.isnan(w_ema50) and w_ema50 < price: candidates_supp.append({'val': w_ema50, 'label': "EMA 50 (TF Week - รับระยะยาว)"})
                if not np.isnan(w_ema200) and w_ema200 < price: candidates_supp.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - รับระดับกองทุน)"})

            if demand_zones:
                for z in demand_zones: candidates_supp.append({'val': z['bottom'], 'label': f"Demand Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})

            candidates_supp.sort(key=lambda x: x['val'], reverse=True)
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
                is_vip = "EMA 200" in item['label'] or "EMA 50 (TF Week" in item['label'] or "52-Week" in item['label'] or "Confluence" in item['label']
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

            # --- RESISTANCES ---
            candidates_res = []
            if not np.isnan(ema20) and ema20 > price: candidates_res.append({'val': ema20, 'label': f"EMA 20 ({tf_label} - ต้านสั้น)"})
            if not np.isnan(ema50) and ema50 > price: candidates_res.append({'val': ema50, 'label': f"EMA 50 ({tf_label})"})
            if not np.isnan(ema200) and ema200 > price: candidates_res.append({'val': ema200, 'label': f"EMA 200 ({tf_label} - ต้านใหญ่)"})
            if not np.isnan(bb_upper) and bb_upper > price: candidates_res.append({'val': bb_upper, 'label': f"BB Upper ({tf_label} - เพดาน)"})
            
            if not df_stats_day.empty:
                try: d_ema50 = ta.ema(df_stats_day['Close'], length=50).iloc[-1]
                except: d_ema50 = np.nan
                if not np.isnan(d_ema50) and d_ema50 > price: candidates_res.append({'val': d_ema50, 'label': "EMA 50 (TF Day)"})
                try: high_60d = df_stats_day['High'].tail(60).max()
                except: high_60d = np.nan
                if not np.isnan(high_60d) and high_60d > price: candidates_res.append({'val': high_60d, 'label': "🏔️ High 60d (ดอย 3 เดือน)"})

            if not df_stats_week.empty:
                try: w_ema50 = ta.ema(df_stats_week['Close'], length=50).iloc[-1]
                except: w_ema50 = np.nan
                try: w_ema200 = ta.ema(df_stats_week['Close'], length=200).iloc[-1]
                except: w_ema200 = np.nan
                if not np.isnan(w_ema50) and w_ema50 > price: candidates_res.append({'val': w_ema50, 'label': "EMA 50 (TF Week - ต้านระยะยาว)"})
                if not np.isnan(w_ema200) and w_ema200 > price: candidates_res.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - ต้านระดับกองทุน)"})
                
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
                is_vip = "EMA 200" in item['label'] or "EMA 50 (TF Week" in item['label'] or "Confluence" in item['label']
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
            obv_col = "#22c55e" if "Bullish" in ai_report['obv_insight'] or "ซื้อ" in ai_report['obv_insight'] else ("#ef4444" if "Bearish" in ai_report['obv_insight'] or "ขาย" in ai_report['obv_insight'] else "#6b7280")
            dz_status = "✅ อยู่ในโซน (In Zone)" if ai_report['in_demand_zone'] else "❌ นอกโซน (รอราคา)"
            
            st.markdown(f"""
            <div class='xray-box'>
                <div class='xray-title'>🕯️ God Mode Insight</div>
                <div class='xray-item'><span>ทรงกราฟ (4 Bars):</span> <span style='font-weight:bold;'>{ai_report['candle_pattern']}</span></div>
                <div class='xray-item'><span>สถานะ:</span> <span>{ai_report['candle_color']}</span></div>
                <div class='xray-item'><span>รายละเอียด:</span> <span style='font-style:italic;'>{ai_report['candle_detail']}</span></div>
                <hr style='margin: 8px 0; opacity: 0.3;'>
                <div class='xray-item'><span>🔥 ความผันผวน (BB):</span> <span style='color:{sq_col}; font-weight:bold;'>{sq_txt}</span></div>
                <div class='xray-item'><span>📊 คุณภาพ Volume:</span> <span style='color:{vol_q_col}; font-weight:bold;'>{vol_txt}</span></div>
                <div class='xray-item'><span>🌊 รายใหญ่ (Smart OBV):</span> <span style='color:{obv_col}; font-weight:bold;'>{ai_report['obv_insight']}</span></div>
                <div class='xray-item'><span>🎯 Demand Zone:</span> <span style='font-weight:bold;'>{dz_status}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- ส่วนแสดงผล: 1. AI Strategy & 2. Execution Plan ---
            
            # เตรียมธีมสีสำหรับ AI Strategy (กล่องบน)
            color_map = {
                "green": {"bg": "#dcfce7", "border": "#22c55e", "text": "#14532d"}, 
                "red": {"bg": "#fee2e2", "border": "#ef4444", "text": "#7f1d1d"}, 
                "orange": {"bg": "#ffedd5", "border": "#f97316", "text": "#7c2d12"}, 
                "yellow": {"bg": "#fef9c3", "border": "#eab308", "text": "#713f12"}
            }
            c_theme = color_map.get(ai_report['status_color'], color_map["yellow"])

            # เตรียม Logic คำแนะนำ (Execution Plan) - ใช้ HTML <b> แทน Markdown **
            strat = ai_report['strategy']
            sl_val = ai_report['sl']
            tp_val = ai_report['tp']
            sl_str_bold = f"<b>{sl_val:.2f}</b>"

            if price < ema20:
                entry_txt = f"บริเวณนี้ ({price:.2f}) หรือแนวรับ"
            else:
                entry_txt = f"ย่อตัวลงมาใกล้ {ema20:.2f}"

            if "Buy" in strat or "Accumulate" in strat:
                adv_holder = f"<span style='color:#15803d'><b>🟢 ถือรันเทรนด์:</b></span> ยก Stop Loss ตามขึ้นไป (ระวังหลุด {sl_str_bold}) อย่าเพิ่งรีบขายหมู"
                adv_none = f"<span style='color:#15803d'><b>🛒 หาจังหวะเข้า:</b></span> {entry_txt} โดยห้ามหลุด {sl_str_bold}"
            elif "Sell" in strat or "Exit" in strat or "Reduce" in strat:
                adv_holder = f"<span style='color:#b91c1c'><b>🔴 ลดพอร์ต/หนี:</b></span> สถานการณ์ไม่ดี ถ้าหลุด {sl_str_bold} ต้องเลิก"
                adv_none = f"<span style='color:#b91c1c'><b>✋ ห้ามรับมีด:</b></span> ราคากำลังลงแรง อย่าเพิ่งสวน รอฐานชัดเจน"
            else:
                adv_holder = f"<span style='color:#854d0e'><b>🟡 ถือรอ:</b></span> ถ้าทุนต่ำถือต่อได้ แต่ถ้าหลุด {sl_str_bold} ต้องหนี"
                adv_none = f"<span style='color:#854d0e'><b>👀 เฝ้าดู:</b></span> ยังไม่ชัดเจน อย่าเพิ่งเข้าเทรด รอเลือกทางก่อน"

            # --- 📦 กล่องที่ 1: AI STRATEGY (สีตามสถานะ) ---
            st.subheader("🤖 AI STRATEGY (God Mode)")
            st.markdown(f"""
            <div style="background-color: {c_theme['bg']}; border-left: 6px solid {c_theme['border']}; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <h2 style="color: {c_theme['text']}; margin:0 0 10px 0; font-size: 26px; font-weight: 800;">{ai_report['banner_title']}</h2>
                <div style="font-size: 20px; font-weight: 700; color: {c_theme['text']}; margin-bottom: 5px;">
                    {ai_report['strategy']}
                </div>
                <div style="font-size: 18px; color: {c_theme['text']}; margin-bottom: 15px; line-height: 1.6;">
                    👉 {ai_report['holder_advice']}
                </div>
                <hr style="border-top: 1px solid {c_theme['text']}; opacity: 0.3; margin: 12px 0;">
                <div style="font-size: 16px; color: {c_theme['text']}; opacity: 0.95;">
                    <b>💡 Insight:</b> {ai_report['context']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- 📦 กล่องที่ 2: EXECUTION PLAN (สีม่วง Lavender - ไม่ซ้ำกับฟ้า) ---
            # ปรับสีใหม่: พื้นหลัง #faf5ff (ม่วงจาง), ขอบ #9333ea (ม่วงสด), ตัวหนังสือ #581c87 (ม่วงเข้ม)
            st.markdown(f"""
            <div style="background-color: #faf5ff; border: 1px solid #e9d5ff; border-left: 6px solid #9333ea; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <h3 style="color: #6b21a8; margin:0 0 15px 0; font-size: 22px; font-weight: 700;">🎯 แผนการเทรด (Execution Plan)</h3>
                
                <div style="margin-bottom: 15px; font-size: 17px; color: #581c87; line-height: 1.6;">
                    <div style="margin-bottom: 10px;">🎒 <b>สำหรับคนมีของ:</b><br>{adv_holder}</div>
                    <div>🛒 <b>สำหรับคนไม่มีของ:</b><br>{adv_none}</div>
                </div>
                
                <hr style="border-top: 1px solid #9333ea; opacity: 0.3; margin: 15px 0;">
                
                <div style="font-size: 17px; color: #581c87;">
                    <b>🧱 Setup (กรอบราคา):</b><br>
                    <div style="margin-top:8px; display:flex; gap:15px; flex-wrap:wrap;">
                        <span style="background:#fee2e2; color:#991b1b; padding:4px 12px; border-radius:6px; font-weight:bold; border:1px solid #fecaca;">
                            🛑 SL : {sl_val:.2f}
                        </span>
                        <span style="background:#dcfce7; color:#166534; padding:4px 12px; border-radius:6px; font-weight:bold; border:1px solid #bbf7d0;">
                            ✅ TP : {tp_val:.2f}
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- ส่วนที่ 3: Bullish/Bearish Factors (ย้ายลงมาล่างสุด) ---
            with st.chat_message("assistant"):
                if ai_report['bullish_factors']: 
                    st.markdown("**🟢 ปัจจัยบวก (Bullish Factors):**")
                    for r in ai_report['bullish_factors']: st.write(f"- {r}")
                if ai_report['bearish_factors']: 
                    st.markdown("**🔴 ปัจจัยลบ/ความเสี่ยง (Bearish Factors):**")
                    for w in ai_report['bearish_factors']: st.write(f"- {w}")

        st.write(""); st.markdown("""<div class='disclaimer-box'>⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากการวิเคราะห์ทางเทคนิคด้วยระบบ AI เพื่อประกอบการตัดสินใจเท่านั้น</div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        col_btn, col_info = st.columns([2, 4])
        
        with col_btn:
            if st.session_state['history_log']:
                latest_data = st.session_state['history_log'][0]
                save_key = f"save_{latest_data['หุ้น']}_{latest_data['เวลา']}"
                
                if st.button(f"💾 บันทึก {latest_data['หุ้น']} ลง Sheet", type="primary", use_container_width=True, key=save_key):
                    with st.spinner("กำลังส่งข้อมูลไป Google Sheet..."):
                        success = save_to_gsheet(latest_data)
                        
                    if success:
                        st.toast(f"✅ บันทึก {latest_data['หุ้น']} เรียบร้อย!", icon="☁️")
                        st.success(f"บันทึกข้อมูล {latest_data['หุ้น']} สำเร็จแล้ว")
                    else:
                        st.error("บันทึกไม่สำเร็จ โปรดตรวจสอบชื่อ Sheet หรือการแชร์สิทธิ์")
        
        st.divider()
        # แบ่งคอลัมน์: ซ้ายชื่อหัวข้อ / ขวาปุ่มล้าง
        c_head, c_reset = st.columns([3, 1]) 
        
        with c_head:
            st.subheader("📜 History Log (บันทึกการวิเคราะห์)")
            
        with c_reset:
            if st.button("⚠️ รีเซ็ต Google Sheet", type="secondary"):
                with st.spinner("กำลังล้างข้อมูลใน Google Sheet..."):
                    # ต้องมีฟังก์ชัน reset_gsheet ใน Part 1 ถึงจะใช้ปุ่มนี้ได้
                    # ถ้าไม่มีฟังก์ชันนี้ ให้ลบปุ่มนี้ออก หรือไปเพิ่มฟังก์ชันใน Part 1
                    try:
                        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                        if "gcp_service_account" in st.secrets:
                            creds_dict = dict(st.secrets["gcp_service_account"])
                            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                            client = gspread.authorize(creds)
                            sheet = client.open("Stock_Analysis_Log").sheet1
                            sheet.resize(rows=1)
                            sheet.resize(rows=1000)
                            st.toast("ล้างข้อมูลเรียบร้อยแล้ว!", icon="🧹")
                            st.session_state['history_log'] = [] 
                            time.sleep(1)
                            st.rerun()
                    except:
                        st.error("เกิดข้อผิดพลาด หรือยังไม่ได้ตั้งค่า Google Sheet")

        if st.session_state['history_log']: 
            df_hist = pd.DataFrame(st.session_state['history_log'])
            
            # เลือกโชว์เฉพาะคอลัมน์ที่จำเป็น (เพิ่ม SL, TP, Change%)
            cols_to_show = ["เวลา", "หุ้น", "TF", "ราคา", "Change%", "สถานะ", "Action", "SL", "TP"]
            final_cols = [c for c in cols_to_show if c in df_hist.columns]
            
            st.dataframe(
                df_hist[final_cols], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "หุ้น": st.column_config.TextColumn("Symbol", help="ชื่อหุ้น"),
                    "สถานะ": st.column_config.TextColumn("Status", help="สถานะจาก God Mode"),
                    "Change%": st.column_config.TextColumn("% Chg"),
                    "SL": st.column_config.TextColumn("Stop Loss", help="จุดหนี"),
                    "TP": st.column_config.TextColumn("Take Profit", help="เป้าขาย")
                }
            )

    else: 
        st.error("ไม่พบข้อมูลหุ้น หรือข้อมูลไม่เพียงพอสำหรับคำนวณ (ต้องมีมากกว่า 20 แท่ง)")

