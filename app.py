import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import os
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- Initialize Session State ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = []

# --- 2. CSS Styles (คงเดิม) ---
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
    </style>
    """, unsafe_allow_html=True)

# --- 3. Header ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ (Hybrid Sniper)🪐</span></h1>", unsafe_allow_html=True)

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
    is_uptrend = price > ema200 if not np.isnan(ema200) else True
    trend_context = "ขาขึ้น (Uptrend)" if is_uptrend else "ขาลง (Downtrend)"
    
    if np.isnan(adx): adx_explain = "⚠️ **ADX:** ข้อมูลไม่เพียงพอ"
    elif adx >= 50: adx_explain = f"🔥 **เทรนด์:** รุนแรงมาก! ({trend_context})"
    elif adx >= 25: adx_explain = f"💪 **เทรนด์:** แข็งแกร่ง ({trend_context})"
    else: adx_explain = f"😴 **เทรนด์:** ตลาดไร้ทิศทาง (Sideway)"

    if np.isnan(rsi): rsi_explain = "⚠️ **RSI:** N/A"
    elif rsi >= 70: rsi_explain = "⚠️ **RSI:** สูง (Overbought) ระวังแรงขาย"
    elif rsi <= 30: rsi_explain = "💎 **RSI:** ต่ำ (Oversold) ลุ้นเด้ง"
    else: rsi_explain = "⚖️ **RSI:** ปกติ"

    if macd_val > macd_signal: macd_explain = "🟢 **MACD:** แรงซื้อนำ (Bullish)"
    else: macd_explain = "🔴 **MACD:** แรงขายนำ (Bearish)"

    return adx_explain, rsi_explain, macd_explain, trend_context

def display_learning_section(rsi, rsi_interp, macd_val, macd_signal, macd_interp, adx_val, price, ema200, bb_upper, bb_lower):
    is_up = price >= ema200 if not np.isnan(ema200) else True
    adx_interp = get_adx_interpretation(adx_val, is_up)
    
    st.markdown("### 📘 มุมความรู้: ค่าต่างๆ คืออะไร? มาจากไหน?")
    with st.expander("คลิกเพื่อเรียนรู้ความหมายของอินดิเคเตอร์แต่ละตัว", expanded=False):
        st.markdown(f"#### 1. MACD\n* **ค่าปัจจุบัน:** `{macd_val:.3f}` -> {macd_interp}")
        st.divider()
        st.markdown(f"#### 2. RSI\n* **ค่าปัจจุบัน:** `{rsi:.2f}` -> {rsi_interp}")
        st.divider()
        st.markdown(f"#### 3. ADX\n* **ค่าปัจจุบัน:** `{adx_val:.2f}` -> {adx_interp}")
        st.divider()
        st.markdown(f"#### 4. Bollinger Bands\n* **กรอบ:** `{bb_lower:.2f}` - `{bb_upper:.2f}`")

def filter_levels(levels, threshold_pct=0.025):
    selected = []
    for val, label in levels:
        if np.isnan(val): continue
        # Rename for clarity
        label = label.replace("BB Lower (Volatility)", "BB Lower (กรอบล่าง)")
        label = label.replace("Low 60 Days (Price Action)", "Low 60 วัน (ฐานราคา)")
        label = label.replace("EMA 200 (Trend Wall)", "EMA 200 (เทรนด์หลัก)")
        label = label.replace("EMA 50 (Short Trend)", "EMA 50 (ระยะกลาง)")
        label = label.replace("EMA 20 (Momentum)", "EMA 20 (โมเมนตัม)")
        label = label.replace("BB Upper (Ceiling)", "BB Upper (ต้านใหญ่)")
        label = label.replace("High 60 Days (Peak)", "High 60 วัน (ยอดดอย)")
        if "MTF" in label or "1wk" in label.lower() or "1mo" in label.lower(): label = "EMA 200 (TF ใหญ่)"
        
        if not selected: selected.append((val, label))
        else:
            last_val = selected[-1][0]
            if abs(val - last_val) / last_val > threshold_pct: selected.append((val, label))
    return selected

# --- 5. Data Fetching (Hybrid) ---
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
            'longName': raw_info.get('longName', symbol),
            'trailingPE': raw_info.get('trailingPE', None),
            'regularMarketPrice': df['Close'].iloc[-1] if not df.empty else None,
            'regularMarketChange': (df['Close'].iloc[-1] - df['Close'].iloc[-2]) if len(df) > 1 else 0,
            'regularMarketChangePercent': ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) if len(df) > 1 else 0,
            'dayHigh': df['High'].iloc[-1] if not df.empty else None,
            'dayLow': df['Low'].iloc[-1] if not df.empty else None,
            'regularMarketOpen': df['Open'].iloc[-1] if not df.empty else None,
            'preMarketPrice': raw_info.get('preMarketPrice'),
            'preMarketChange': raw_info.get('preMarketChange'),
            'preMarketChangePercent': raw_info.get('preMarketChangePercent'),
            'postMarketPrice': raw_info.get('postMarketPrice'),
            'postMarketChange': raw_info.get('postMarketChange'),
            'postMarketChangePercent': raw_info.get('postMarketChangePercent'),
        }
        return df, stock_info, df_mtf
    except: return None, None, None

def analyze_volume(row, vol_ma):
    vol = row['Volume']
    if np.isnan(vol_ma): return "Normal Volume", "gray"
    if vol > vol_ma * 1.5: return "High Volume", "green"
    elif vol < vol_ma * 0.7: return "Low Volume", "red"
    else: return "Normal Volume", "gray"

# --- 7. AI Logic ---
def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, vol_status, mtf_trend, atr_val, mtf_ema200_val):
    score = 0
    bullish_factors, bearish_factors = [], []
    
    # Situation Insight
    situation_insight = ""
    if not np.isnan(ema20) and not np.isnan(ema50) and not np.isnan(ema200):
        if price < ema20 and price > ema50 and price > ema200:
            situation_insight = f"⚠️ **ระวัง:** ราคาหลุดแนวรับ EMA 20 ({ema20:.2f}) ลงมาแล้ว! เส้นนี้เปลี่ยนเป็น **'แนวต้าน'** ทันที"
        elif price > ema20 and price > ema200:
            situation_insight = f"✅ **สถานการณ์ดี:** ราคายืนเหนือแนวรับสั้น EMA 20 ({ema20:.2f}) ได้อย่างมั่นคง (แนวต้านกลายเป็นแนวรับ)"
        elif price > ema20 and price < ema50:
             situation_insight = f"🚀 **Rebound (ทะลุแนวต้านสั้น):** ราคาทะลุแนวต้าน EMA 20 ({ema20:.2f}) ขึ้นมาได้แล้ว! เป้าต่อไปคือ EMA 50"
        elif price < ema50 and price > ema200:
            situation_insight = f"📉 **Deep Pullback:** ราคาย่อตัวลึกต่ำกว่า EMA 50 เข้าหาฐานใหญ่ EMA 200 ({ema200:.2f}) เป็นจุดวัดใจ"
        elif price < ema200:
            situation_insight = f"⛔ **Bearish:** ราคาอยู่ใต้เส้น EMA 200 ({ema200:.2f}) ซึ่งเป็นกำแพงหนาของขาลง"

    if not np.isnan(ema200):
        if price > ema200:
            score += 3; bullish_factors.append("ราคา > EMA 200 (เทรนด์หลักขาขึ้น)")
            if price > ema20: score += 1; bullish_factors.append("ราคา > EMA 20 (แข็งแกร่ง)")
            else: score -= 0; bearish_factors.append("ราคาหลุด EMA 20 (พักตัว)")
        else:
            score -= 3; bearish_factors.append("ราคา < EMA 200 (เทรนด์หลักขาลง)")
            
    if macd_val > macd_sig: score += 1; bullish_factors.append("MACD ตัดขึ้น")
    else: score -= 1; bearish_factors.append("MACD ตัดลง")
    
    if mtf_trend == "Bullish": score += 2; bullish_factors.append("TF ใหญ่เป็นขาขึ้น")
    elif mtf_trend == "Bearish": score -= 2; bearish_factors.append("TF ใหญ่เป็นขาลง")
    
    if "High Volume" in vol_status:
        if price > ema20: score += 1; bullish_factors.append("Volume ซื้อสนับสนุน")
        else: score -= 1; bearish_factors.append("Volume ขายกดดัน")
        
    if rsi > 70: bearish_factors.append(f"RSI สูง ({rsi:.0f}) ระวังแรงขาย")
    elif rsi < 30: bullish_factors.append(f"RSI ต่ำ ({rsi:.0f}) ลุ้นเด้ง")

    # Strategy
    status_color, banner_title, strategy_text = "yellow", "Neutral", "Wait & See"
    context_text, holder_advice = "ตลาดไร้ทิศทาง", "รอสัญญาณชัดเจนกว่านี้"
    
    sl_val = price - (2 * atr_val) if not np.isnan(atr_val) else price * 0.95
    tp_val = price + (3 * atr_val) if not np.isnan(atr_val) else price * 1.05
    
    if score >= 6:
        status_color, banner_title, strategy_text = "green", "🚀 Super Nova", "Aggressive Buy"
        context_text = "ทุก Timeframe เป็นขาขึ้น วอลุ่มซื้อถล่มทลาย"
        holder_advice = "🎉 ถือต่อ (Let Profit Run) ใช้ Trailing Stop เกาะเทรนด์ไป"
    elif score >= 4:
        status_color, banner_title, strategy_text = "green", "🐂 Strong Bullish", "Buy / Hold"
        context_text = "เทรนด์ขาขึ้นชัดเจน โมเมนตัมบวก"
        holder_advice = "🥳 ถือต่อได้สบายใจ ถ้ามีย่อตัวใกล้ EMA 20 ถือเป็นโอกาสเก็บเพิ่ม"
    elif score >= 2:
        status_color, banner_title, strategy_text = "green", "📈 Moderate Bullish", "Buy on Dip"
        context_text = "ภาพรวมขาขึ้น แต่ระยะสั้นมีการพักตัว"
        holder_advice = "🙂 ถือต่อได้ แต่ถ้าหลุด EMA 20 ให้แบ่งขายทำกำไรบางส่วน"
    elif score >= -1:
        status_color, banner_title, strategy_text = "yellow", "⚖️ Neutral", "Wait & See"
        context_text = "แรงซื้อขายสูสี รอเลือกทาง"
        holder_advice = "🤔 ถ้าทุนต่ำถือรอได้ ถ้าทุนสูงให้ตั้ง Stop Loss ที่กรอบล่าง"
    elif score >= -3:
        status_color, banner_title, strategy_text = "orange", "☁️ Weak Warning", "Defensive"
        context_text = "โมเมนตัมแผ่วลง ระวังฐานแตก"
        holder_advice = "🦅 อย่าเพิ่งรับมีด! รอให้ราคากลับมายืนเหนือ EMA 20 ให้ได้ก่อน"
    else:
        status_color, banner_title, strategy_text = "red", "🐻 Strong Bearish", "Strong Sell / Avoid"
        context_text = "หลุดแนวรับสำคัญ เทรนด์เปลี่ยนเป็นขาลง"
        holder_advice = "🥶 Cut Loss Now! อย่าเสียดาย ห้ามถัวเฉลี่ยขาลงเด็ดขาด"

    return {
        "status_color": status_color, "banner_title": banner_title, "strategy": strategy_text,
        "context": context_text, "bullish_factors": bullish_factors, "bearish_factors": bearish_factors,
        "sl": sl_val, "tp": tp_val, "holder_advice": holder_advice, "situation_insight": situation_insight
    }

# --- 8. Display ---
if submit_btn:
    st.divider()
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)
    
    with st.spinner(f"AI กำลังประมวลผล {symbol_input} (ค้นหาต้นทุนเจ้า + Hybrid Logic)..."):
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)

    if df is not None and not df.empty and len(df) > 10: 
        # Indicators
        df['EMA20'] = ta.ema(df['Close'], 20); df['EMA50'] = ta.ema(df['Close'], 50); df['EMA200'] = ta.ema(df['Close'], 200)
        df['RSI'] = ta.rsi(df['Close'], 14); df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], 14)
        macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
        bbands = ta.bbands(df['Close'], 20, 2); 
        if bbands is not None: df = pd.concat([df, bbands], axis=1); bbl_col, bbu_col = bbands.columns[0], bbands.columns[2]
        else: bbl_col, bbu_col = None, None
        adx = ta.adx(df['High'], df['Low'], df['Close'], 14); df = pd.concat([df, adx], axis=1)
        df['Vol_SMA20'] = ta.sma(df['Volume'], 20)

        # --- 🔥 NEW FEATURE: Banker's Cost (ต้นทุนเจ้า) ---
        banker_price = np.nan
        if len(df) >= 90:
            last_90 = df.tail(90)
            max_vol_idx = last_90['Volume'].idxmax()
            max_vol_row = last_90.loc[max_vol_idx]
            # ราคากลางของแท่งที่ Volume พีคที่สุด
            banker_price = (max_vol_row['High'] + max_vol_row['Low']) / 2
        # -----------------------------------------------

        last = df.iloc[-1]
        price = info.get('regularMarketPrice') if info.get('regularMarketPrice') else last['Close']
        
        rsi = last['RSI'] if 'RSI' in last else np.nan
        atr = last['ATR'] if 'ATR' in last else np.nan
        ema20 = last['EMA20'] if 'EMA20' in last else np.nan
        ema50 = last['EMA50'] if 'EMA50' in last else np.nan
        ema200 = last['EMA200'] if 'EMA200' in last else np.nan
        vol_now = last['Volume']
        
        try: macd_val, macd_signal = last['MACD_12_26_9'], last['MACDs_12_26_9']
        except: macd_val, macd_signal = np.nan, np.nan
        try: adx_val = last['ADX_14']
        except: adx_val = np.nan

        if bbu_col and bbl_col: bb_upper, bb_lower = last[bbu_col], last[bbl_col]
        else: bb_upper, bb_lower = price * 1.05, price * 0.95

        vol_status, vol_color = analyze_volume(last, last['Vol_SMA20'])
        mtf_trend, mtf_ema200_val = "Sideway", 0
        if df_mtf is not None and not df_mtf.empty:
            df_mtf['EMA200'] = ta.ema(df_mtf['Close'], 200)
            if len(df_mtf) > 200:
                mtf_ema200_val = df_mtf['EMA200'].iloc[-1]
                if df_mtf['Close'].iloc[-1] > mtf_ema200_val: mtf_trend = "Bullish"
                else: mtf_trend = "Bearish"
        
        ai_report = ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, 
                                        vol_status, mtf_trend, atr, mtf_ema200_val)

        # Log History
        current_time = datetime.now().strftime("%H:%M:%S")
        log_entry = {"เวลา": current_time, "หุ้น": symbol_input, "ราคา": f"{price:.2f}", "สถานะ": ai_report['banner_title'].split(':')[0], "Action": ai_report['strategy']}
        st.session_state['history_log'].insert(0, log_entry)
        if len(st.session_state['history_log']) > 10: st.session_state['history_log'] = st.session_state['history_log'][:10]

        # --- UI Display ---
        logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
        fallback_url = "https://cdn-icons-png.flaticon.com/512/720/720453.png"
        icon_html = f"""<img src="{logo_url}" onerror="this.onerror=null; this.src='{fallback_url}';" style="height: 50px; width: 50px; border-radius: 50%; vertical-align: middle; margin-right: 10px; object-fit: contain; background-color: white; border: 1px solid #e0e0e0; padding: 2px;">"""
        st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>{icon_html} {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            reg_price, reg_chg = info.get('regularMarketPrice'), info.get('regularMarketChange')
            pct = (reg_chg / (reg_price - reg_chg) * 100) if reg_price and reg_chg else 0
            color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"
            bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
            st.markdown(f"""<div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;"><div style="font-size:40px; font-weight:600; line-height: 1;">{reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span></div><div style="display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text}; padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">{arrow_html(reg_chg)} {reg_chg:+.2f} ({pct:.2f}%)</div></div>""", unsafe_allow_html=True)
            
            def make_pill(c, p): return f'<span style="background:{"#e8f5ec" if c>=0 else "#fee2e2"}; color:{"#16a34a" if c>=0 else "#dc2626"}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{"▲" if c>=0 else "▼"} {c:+.2f} ({p:.2f}%)</span>'
            if info.get('preMarketPrice'): st.markdown(f'<div style="margin-top: -5px; margin-bottom: 15px;">☀️ Pre: <b>{info["preMarketPrice"]:.2f}</b> {make_pill(info["preMarketChange"], info["preMarketChangePercent"]*100)}</div>', unsafe_allow_html=True)

        if tf_code == "1h": tf_label = "TF Hour"
        elif tf_code == "1wk": tf_label = "TF Week"
        else: tf_label = "TF Day"
        
        st_color = ai_report["status_color"]
        if st_color == "green": c2.success(f"📈 {ai_report['banner_title']}\n\n**{tf_label}**")
        elif st_color == "red": c2.error(f"📉 {ai_report['banner_title']}\n\n**{tf_label}**")
        else: c2.warning(f"⚖️ {ai_report['banner_title']}\n\n**{tf_label}**")

        c3, c4, c5 = st.columns(3)
        icon_up = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>"""
        icon_down = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12l7 7 7-7"/></svg>"""
        with c3:
            pe = info.get('trailingPE'); pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A"
            st.markdown(custom_metric_html("📊 P/E Ratio", pe_str, get_pe_interpretation(pe), "gray", ""), unsafe_allow_html=True)
        with c4:
            st.markdown(custom_metric_html("⚡ RSI (14)", f"{rsi:.2f}" if not np.isnan(rsi) else "N/A", get_rsi_interpretation(rsi), "red" if rsi>70 or rsi<30 else "gray", icon_up if rsi>55 else icon_down), unsafe_allow_html=True)
        with c5:
            st.markdown(custom_metric_html("💪 ADX Strength", f"{adx_val:.2f}" if not np.isnan(adx_val) else "N/A", get_adx_interpretation(adx_val, price>ema200), "green" if adx_val>25 else "gray", icon_up if adx_val>25 else ""), unsafe_allow_html=True)

        st.write("")
        c_ema, c_ai = st.columns([1.5, 2])
        with c_ema:
            st.subheader("📉 Technical Indicators")
            atr_pct = (atr / price * 100) if not np.isnan(atr) else 0
            st.markdown(f"""
            <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'>
                <div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{ema20:.2f}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{ema200:.2f}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>MACD</span> <span>{macd_val:.3f}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>Volume</span> <span style='color:{vol_color}'>{vol_status.split()[0]}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>ATR</span> <span>{atr:.2f} ({atr_pct:.1f}%)</span></div>
            </div>""", unsafe_allow_html=True)
            
            st.subheader("🚧 Key Levels")
            # Create Potential Levels List including Banker's Price
            potential_levels = [
                (bb_lower, "BB Lower (กรอบล่าง)"),
                (df['Low'].tail(60).min(), "Low 60 วัน (ฐานราคา)"),
                (ema200, "EMA 200 (เทรนด์หลัก)"),
                (mtf_ema200_val, f"EMA 200 ({mtf_code.upper()})"),
                (ema50, "EMA 50 (ระยะกลาง)"),
                (ema20, "EMA 20 (โมเมนตัม)"),
                (bb_upper, "BB Upper (ต้านใหญ่)"),
                (df['High'].tail(60).max(), "High 60 วัน (ยอดดอย)"),
                # ✅ ใส่ทุนเจ้าเข้าไป
                (banker_price, "💰 ทุนเจ้า (Big Lot 90 Days)")
            ]
            
            supports = sorted([x for x in potential_levels if not np.isnan(x[0]) and x[0] < price], key=lambda x: x[0], reverse=True)
            resistances = sorted([x for x in potential_levels if not np.isnan(x[0]) and x[0] > price], key=lambda x: x[0])
            
            valid_sup = filter_levels(supports); valid_res = filter_levels(resistances)
            
            st.markdown("#### 🟢 แนวรับ (Support)")
            if valid_sup: 
                for v, d in valid_sup[:3]: st.write(f"- **{v:.2f}** : {d}")
            else: st.write("- All Time High")
            
            st.markdown("#### 🔴 แนวต้าน (Resistance)")
            if valid_res: 
                for v, d in valid_res[:2]: st.write(f"- **{v:.2f}** : {d}")
            else: st.write("- All Time Low")

            if ai_report['situation_insight']:
                with st.expander("💡 อ่านสถานการณ์กราฟ", expanded=True): st.warning(ai_report['situation_insight'])

        with c_ai:
            st.subheader("🧐 AI Deep Analysis")
            adx_exp, rsi_exp, macd_exp, tr_exp = get_detailed_explanation(adx_val, rsi, macd_val, macd_signal, price, ema200)
            with st.container(): st.info(f"{adx_exp}"); st.info(f"{macd_exp}")
            
            st.subheader("🤖 AI STRATEGY")
            c_map = {"green": "#dcfce7", "red": "#fee2e2", "orange": "#ffedd5", "yellow": "#fef9c3"}
            c_bg = c_map.get(ai_report['status_color'], "#f3f4f6")
            st.markdown(f"""<div style="background-color: {c_bg}; padding: 20px; border-radius: 10px; border-left: 6px solid gray;">
                <h2 style="margin:0;">{ai_report['banner_title'].split(':')[0]}</h2>
                <h3 style="margin:5px 0;">{ai_report['strategy']}</h3>
                <p>{ai_report['context']}</p></div>""", unsafe_allow_html=True)
            
            with st.chat_message("assistant"):
                if ai_report['bullish_factors']: st.markdown("**🟢 Pros:**"); 
                for f in ai_report['bullish_factors']: st.write(f"- {f}")
                if ai_report['bearish_factors']: st.markdown("**🔴 Cons:**"); 
                for f in ai_report['bearish_factors']: st.write(f"- {f}")
                st.divider()
                st.info(f"**Advice:** {ai_report['holder_advice']}")
                st.write(f"🛑 Stop Loss: {ai_report['sl']:.2f} | ✅ Take Profit: {ai_report['tp']:.2f}")

        st.divider()
        st.subheader("📜 ประวัติการวิเคราะห์ (Session History)")
        if st.session_state['history_log']:
            st.dataframe(pd.DataFrame(st.session_state['history_log']), use_container_width=True, hide_index=True)
        
        display_learning_section(rsi, get_rsi_interpretation(rsi), macd_val, macd_signal, "Bull/Bear", adx_val, price, ema200, bb_upper, bb_lower)
    else:
        st.error("ไม่พบข้อมูลหุ้น")
