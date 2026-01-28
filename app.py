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

# --- Initialize Session States ---
if 'history_log' not in st.session_state: st.session_state['history_log'] = []
if 'analyzed_data' not in st.session_state: st.session_state['analyzed_data'] = None

# --- CSV Handling (Journal) ---
CSV_FILE = 'trading_journal.csv'
def load_journal():
    if os.path.exists(CSV_FILE): return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=["Date", "Time", "Symbol", "Price", "Score", "Strategy", "Note"])

def save_to_journal(data_dict):
    df = load_journal()
    new_row = pd.DataFrame([data_dict])
    df = pd.concat([new_row, df], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    return df

# --- 2. CSS ---
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
    .disclaimer-box {
        margin-top: 20px; margin-bottom: 20px; padding: 20px;
        background-color: #fff8e1; border: 2px solid #ffc107;
        border-radius: 12px; font-size: 1rem; color: #5d4037; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Header ---
st.markdown("<h1>💎  Stock Master <br><span style='font-size: 1.2rem; opacity: 0.7;'>Hybrid Sniper + Banker's Eye 👁️</span></h1>", unsafe_allow_html=True)

# --- 4. Helper Functions ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:bold'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:bold'>▼</span>"

def format_volume(vol):
    if vol >= 1_000_000_000: return f"{vol/1_000_000_000:.2f}B"
    if vol >= 1_000_000: return f"{vol/1_000_000:.2f}M"
    if vol >= 1_000: return f"{vol/1_000:.2f}K"
    return f"{vol:,.0f}"

def custom_metric_html(label, value, status_text, color_status, icon_svg):
    if color_status == "green": color_code = "#16a34a"
    elif color_status == "red": color_code = "#dc2626"
    else: color_code = "#a3a3a3"
    return f"""
    <div style="margin-bottom: 15px;">
        <div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 5px;">
            <div style="font-size: 18px; font-weight: 700; opacity: 0.9; color: var(--text-color);">{label}</div>
            <div style="font-size: 24px; font-weight: 700; color: var(--text-color);">{value}</div>
        </div>
        <div style="display: flex; align-items: start; gap: 6px; font-size: 15px; font-weight: 600; color: {color_code};">
            <div style="margin-top: 3px; min-width: 24px;">{icon_svg}</div><div>{status_text}</div>
        </div>
    </div>
    """

def get_rsi_interpretation(rsi):
    if np.isnan(rsi): return "N/A"
    if rsi >= 70: return "Overbought (ระวังแรงขาย)"
    elif rsi >= 55: return "Bullish (กระทิงแข็งแกร่ง)"
    elif rsi >= 45: return "Sideway (รอเลือกทาง)"
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
    if adx >= 50: return f"Super Strong {trend_str}"
    if adx >= 25: return f"Strong {trend_str}"
    if adx >= 20: return "Developing Trend"
    return "Weak Trend"

def get_detailed_explanation(adx, rsi, macd_val, macd_signal, price, ema200):
    is_uptrend = price > ema200 if not np.isnan(ema200) else True
    trend_context = "ขาขึ้น (Uptrend)" if is_uptrend else "ขาลง (Downtrend)"
    if np.isnan(adx): adx_explain = "⚠️ ADX: N/A"
    elif adx >= 50: adx_explain = f"🔥 **เทรนด์:** รุนแรงมาก! ({trend_context})"
    elif adx >= 25: adx_explain = f"💪 **เทรนด์:** แข็งแกร่ง ({trend_context})"
    else: adx_explain = f"😴 **เทรนด์:** ตลาดไร้ทิศทาง (Sideway)"
    if macd_val > macd_signal: macd_explain = "🟢 **MACD:** แรงซื้อนำ (Bullish)"
    else: macd_explain = "🔴 **MACD:** แรงขายนำ (Bearish)"
    return adx_explain, macd_explain

def display_learning_section(rsi, rsi_interp, macd_val, macd_signal, macd_interp, adx_val, price, ema200, bb_upper, bb_lower):
    st.markdown("### 📘 มุมความรู้: ค่าต่างๆ คืออะไร?")
    with st.expander("คลิกเพื่อเรียนรู้ความหมาย", expanded=False):
        st.markdown(f"#### 1. MACD\n* **ค่าปัจจุบัน:** `{macd_val:.3f}`")
        st.divider()
        st.markdown(f"#### 2. RSI\n* **ค่าปัจจุบัน:** `{rsi:.2f}`")
        st.divider()
        st.markdown(f"#### 3. Bollinger Bands\n* **กรอบ:** `{bb_lower:.2f}` - `{bb_upper:.2f}`")

def filter_levels(levels, threshold_pct=0.025):
    selected = []
    for val, label in levels:
        if np.isnan(val): continue
        label = label.replace("BB Lower (Volatility)", "BB Lower (กรอบล่าง)")
        label = label.replace("Low 60 Days (Price Action)", "Low 60 วัน (ฐานราคา)")
        label = label.replace("EMA 200 (Trend Wall)", "EMA 200 (เทรนด์หลัก)")
        label = label.replace("EMA 50 (Short Trend)", "EMA 50 (ระยะกลาง)")
        label = label.replace("EMA 20 (Momentum)", "EMA 20 (โมเมนตัม)")
        label = label.replace("BB Upper (Ceiling)", "BB Upper (ต้านใหญ่)")
        label = label.replace("High 60 Days (Peak)", "High 60 วัน (ยอดดอย)")
        if "MTF" in label: label = "EMA 200 (TF ใหญ่)"
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
        period_val = "730d"
        if interval == "1wk": period_val = "10y"
        elif interval == "1d": period_val = "5y"

        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval)
        
        try: raw_info = ticker.info 
        except: raw_info = {} 

        current_price = df['Close'].iloc[-1] if not df.empty else 0
        prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
        
        stock_info = {
            'longName': raw_info.get('longName', symbol),
            'marketState': raw_info.get('marketState', 'REGULAR'), 
            'trailingPE': raw_info.get('trailingPE', None),
            'price': current_price,
            'change': current_price - prev_price,
            'change_pct': ((current_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0,
            # ✅ ดึงข้อมูล OHLC และ Pre/Post เพื่อนำไปแสดงผล
            'dayOpen': df['Open'].iloc[-1] if not df.empty else None,
            'dayHigh': df['High'].iloc[-1] if not df.empty else None,
            'dayLow': df['Low'].iloc[-1] if not df.empty else None,
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

# --- 7. AI Logic (Super Nova Fixed & Situation Insight) ---
def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, vol_status, mtf_trend, atr_val, mtf_ema200_val):
    score = 0
    bullish_factors, bearish_factors = [], []
    
    # 🌟 Situation Insight
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

    # Logic การให้คะแนน
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

    # Strategy Generation
    sl_val = price - (2 * atr_val) if not np.isnan(atr_val) else price * 0.95
    tp_val = price + (3 * atr_val) if not np.isnan(atr_val) else price * 1.05
    
    # --- 🔥 Super Nova Logic FIXED (เช็คแนวต้านก่อน) ---
    status_color, banner_title, strategy_text = "yellow", "Neutral", "Wait & See"
    context_text, holder_advice = "ตลาดไร้ทิศทาง", "รอสัญญาณชัดเจนกว่านี้"

    if score >= 6:
        status_color, banner_title, strategy_text = "green", "🚀 Super Nova", "Aggressive Buy"
        # ✅ Logic: เช็คก่อนว่าทะลุ BB Upper หรือยัง?
        if price < bb_up:
            context_text = f"🔥 กระทิงดุ! โมเมนตัมแรงมาก แต่ราคากำลังทดสอบแนวต้านใหญ่ที่ {bb_up:.2f}"
            holder_advice = "🎉 ถือต่อ (Run Trend) แต่อย่าเพิ่งไล่ราคาโซนนี้ รอทะลุแนวต้านให้ขาดก่อน"
        else:
            context_text = "🚀 ทะลุทุกแนวต้าน! ตลาดเข้าสู่สภาวะ Euphoria (ไร้แนวต้านขวางกั้น)"
            holder_advice = "🥳 Let Profit Run เต็มที่! ใช้ Trailing Stop เกาะไปเรื่อยๆ จนกว่ากราฟจะหักหัว"
            
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
        "status": status, "color": color, "action": action,
        "context": context_text, "bullish_factors": bullish_factors, "bearish_factors": bearish_factors,
        "sl": sl_val, "tp": tp_val, "holder_advice": holder_advice, "situation_insight": situation_insight
    }

# --- 8. UI Layout ---
c_search, c_space = st.columns([2, 1])
with c_search:
    with st.form(key='search_form'):
        c1, c2 = st.columns([3, 1])
        with c1: symbol_input = st.text_input("ชื่อหุ้น (เช่น TSLA, BTC-USD)", value="").upper().strip()
        with c2: timeframe = st.selectbox("TF:", ["1h", "1d", "1wk"], index=1)
        submitted = st.form_submit_button("🚀 วิเคราะห์ (Analyze)")

# --- 9. Execution ---
if submitted and symbol_input:
    with st.spinner("AI กำลังทำงาน..."):
        mtf_code = "1d" if timeframe == "1h" else ("1mo" if timeframe == "1wk" else "1wk")
        df, info, df_mtf = get_data_hybrid(symbol_input, timeframe, mtf_code)
        
        if df is not None and len(df) > 50:
            # Calc Indicators
            df['EMA20'] = ta.ema(df['Close'], 20); df['EMA50'] = ta.ema(df['Close'], 50); df['EMA200'] = ta.ema(df['Close'], 200)
            df['RSI'] = ta.rsi(df['Close'], 14); df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], 14)
            macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
            bbands = ta.bbands(df['Close'], 20, 2); 
            if bbands is not None: df = pd.concat([df, bbands], axis=1); bbl_col, bbu_col = bbands.columns[0], bbands.columns[2]
            else: bbl_col, bbu_col = None, None
            adx = ta.adx(df['High'], df['Low'], df['Close'], 14); df = pd.concat([df, adx], axis=1)
            df['Vol_SMA'] = ta.sma(df['Volume'], 20)
            
            # --- Banker's Cost Logic ---
            banker_price = np.nan
            if len(df) >= 90:
                last_90 = df.tail(90)
                max_vol_idx = last_90['Volume'].idxmax()
                max_vol_row = last_90.loc[max_vol_idx]
                banker_price = (max_vol_row['High'] + max_vol_row['Low']) / 2

            last = df.iloc[-1]
            price = info['price']
            
            vol_now = last['Volume']
            vol_ma = last['Vol_SMA'] if not np.isnan(last['Vol_SMA']) else vol_now
            if vol_now > vol_ma * 1.5: vol_stat = "High Volume"
            elif vol_now < vol_ma * 0.7: vol_stat = "Low Volume"
            else: vol_stat = "Normal"
            
            mtf_trend, mtf_ema200_val = "Sideway", 0
            if df_mtf is not None and not df_mtf.empty:
                df_mtf['EMA200'] = ta.ema(df_mtf['Close'], 200)
                if len(df_mtf) > 200:
                    mtf_ema200_val = df_mtf['EMA200'].iloc[-1]
                    if df_mtf['Close'].iloc[-1] > mtf_ema200_val: mtf_trend = "Bullish"
                    else: mtf_trend = "Bearish"

            # AI Logic Call
            res = ai_hybrid_analysis(price, last['EMA20'], last['EMA50'], last['EMA200'], 
                                     last['RSI'], last['MACD_12_26_9'], last['MACDs_12_26_9'], 
                                     last['ADX_14'], last[bbu_col] if bbu_col else 0, last[bbl_col] if bbl_col else 0,
                                     vol_stat, mtf_trend, last['ATR'], mtf_ema200_val)
            
            # Save to Session State
            st.session_state['analyzed_data'] = {
                "symbol": symbol_input, "info": info, "last": last, "res": res, 
                "timeframe": timeframe, "banker_price": banker_price, 
                "bb_upper": last[bbu_col] if bbu_col else 0, "bb_lower": last[bbl_col] if bbl_col else 0,
                "mtf_ema200": mtf_ema200_val, "vol_stat": vol_stat, "mtf_code": mtf_code
            }
        else:
            st.error("ไม่พบข้อมูลหุ้น")

# --- 10. Display Result ---
if st.session_state['analyzed_data']:
    data = st.session_state['analyzed_data']
    info = data['info']; last = data['last']; res = data['res']
    
    st.divider()
    
    # Header & Price
    col_head, col_score = st.columns([1.5, 2])
    with col_head:
        # Pre/Post Pill Helper
        def make_pill(c, p): return f'<span style="background:{"#e8f5ec" if c>=0 else "#fee2e2"}; color:{"#16a34a" if c>=0 else "#dc2626"}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{"▲" if c>=0 else "▼"} {c:+.2f} ({p:.2f}%)</span>'
        
        st.markdown(f"## {data['symbol']} ({data['timeframe']})")
        val_color = "#16a34a" if info['change'] >= 0 else "#dc2626"
        st.markdown(f"<h1 style='margin:0;'>{info['price']:,.2f}</h1>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:{val_color}; font-size:1.2rem; font-weight:bold'>{info['change']:+.2f} ({info['change_pct']:.2f}%)</span>", unsafe_allow_html=True)
        
        # ✅ FIX: Display OHLC (เปิดแสดงเสมอ)
        if info.get('dayOpen'):
            st.markdown(f"""
            <div style="font-size: 14px; margin-top: 5px; opacity: 0.8; font-family: monospace;">
                O: {info['dayOpen']:.2f} | H: {info['dayHigh']:.2f} | L: {info['dayLow']:.2f}
            </div>
            """, unsafe_allow_html=True)

        # ✅ FIX: Display Pre AND Post Market (ถ้ามี)
        if info.get('preMarketPrice'): 
            st.markdown(f'<div style="margin-top:5px; font-size:13px;">☀️ Pre: <b>{info["preMarketPrice"]:.2f}</b> {make_pill(info["preMarketChange"], info["preMarketChangePercent"]*100)}</div>', unsafe_allow_html=True)
        if info.get('postMarketPrice'):
            st.markdown(f'<div style="margin-top:2px; font-size:13px;">🌙 Post: <b>{info["postMarketPrice"]:.2f}</b> {make_pill(info["postMarketChange"], info["postMarketChangePercent"]*100)}</div>', unsafe_allow_html=True)
        
    with col_score:
        bg_color = {"green": "#dcfce7", "yellow": "#fef9c3", "orange": "#ffedd5", "red": "#fee2e2"}
        text_color = {"green": "#14532d", "yellow": "#713f12", "orange": "#7c2d12", "red": "#7f1d1d"}
        c_bg = bg_color.get(res['color'], "#f3f4f6"); c_txt = text_color.get(res['color'], "#1f2937")
        st.markdown(f"""<div style="background-color:{c_bg}; padding:15px; border-radius:10px; border-left: 5px solid {res['color']};"><h3 style="color:{c_txt}; margin:0;">{res['status']}</h3><p style="color:{c_txt}; margin:5px 0 0 0; font-weight:bold;">🎯 Action: {res['action']}</p></div>""", unsafe_allow_html=True)

    # Metrics
    c3, c4, c5 = st.columns(3)
    icon_up = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>"""
    icon_down = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12l7 7 7-7"/></svg>"""
    with c3:
        pe = info.get('trailingPE'); pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A"
        st.markdown(custom_metric_html("📊 P/E Ratio", pe_str, get_pe_interpretation(pe), "gray", ""), unsafe_allow_html=True)
    with c4:
        st.markdown(custom_metric_html("⚡ RSI (14)", f"{last['RSI']:.2f}", get_rsi_interpretation(last['RSI']), "red" if last['RSI']>70 or last['RSI']<30 else "gray", icon_up if last['RSI']>55 else icon_down), unsafe_allow_html=True)
    with c5:
        adx_val = last['ADX_14']
        st.markdown(custom_metric_html("💪 ADX Strength", f"{adx_val:.2f}", get_adx_interpretation(adx_val, info['price']>last['EMA200']), "green" if adx_val>25 else "gray", icon_up if adx_val>25 else ""), unsafe_allow_html=True)

    st.write("")
    c_ema, c_ai = st.columns([1.5, 2])
    with c_ema:
        st.subheader("📉 Technical Indicators")
        atr_pct = (last['ATR'] / info['price']) * 100 if info['price'] > 0 else 0
        st.markdown(f"""
        <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'>
            <div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{last['EMA20']:.2f}</span></div>
            <div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{last['EMA200']:.2f}</span></div>
            <div style='display:flex; justify-content:space-between;'><span>MACD</span> <span>{last['MACD_12_26_9']:.3f}</span></div>
            <div style='display:flex; justify-content:space-between;'><span>ATR</span> <span>{last['ATR']:.2f} ({atr_pct:.1f}%)</span></div>
            <div style='display:flex; justify-content:space-between;'><span>Volume</span> <span>{data['vol_stat']}</span></div>
        </div>""", unsafe_allow_html=True)
        
        st.subheader("🚧 Key Levels")
        potential_levels = [
            (data['bb_lower'], "BB Lower (กรอบล่าง)"),
            (last['EMA200'], "EMA 200 (เทรนด์หลัก)"),
            (data['mtf_ema200'], f"EMA 200 ({data['mtf_code'].upper()})"),
            (last['EMA50'], "EMA 50 (ระยะกลาง)"),
            (last['EMA20'], "EMA 20 (โมเมนตัม)"),
            (data['bb_upper'], "BB Upper (ต้านใหญ่)"),
            (data['banker_price'], "💰 ทุนเจ้า (Big Lot 90 Days)")
        ]
        supports = sorted([x for x in potential_levels if not np.isnan(x[0]) and x[0] < info['price']], key=lambda x: x[0], reverse=True)
        resistances = sorted([x for x in potential_levels if not np.isnan(x[0]) and x[0] > info['price']], key=lambda x: x[0])
        valid_sup = filter_levels(supports); valid_res = filter_levels(resistances)
        
        st.markdown("#### 🟢 แนวรับ (Support)")
        if valid_sup: 
            for v, d in valid_sup[:3]: st.write(f"- **{v:.2f}** : {d}")
        else: st.write("- All Time High")
        st.markdown("#### 🔴 แนวต้าน (Resistance)")
        if valid_res: 
            for v, d in valid_res[:2]: st.write(f"- **{v:.2f}** : {d}")
        else: st.write("- All Time Low")

        if res['situation_insight']:
            st.write("")
            with st.expander("💡 อ่านสถานการณ์กราฟ (Click)", expanded=True): st.warning(res['situation_insight'])

    with c_ai:
        st.subheader("🧐 AI Deep Analysis")
        adx_exp, macd_exp = get_detailed_explanation(last['ADX_14'], last['RSI'], last['MACD_12_26_9'], last['MACDs_12_26_9'], info['price'], last['EMA200'])
        with st.container(): st.info(adx_exp); st.info(macd_exp)
        
        st.subheader("🤖 AI STRATEGY")
        st.markdown(f"""<div style="background-color:{c_bg}; padding:20px; border-radius:10px; border-left: 6px solid gray;"><h2 style="margin:0;">{res['status']}</h2><h3 style="margin:5px 0;">{res['action']}</h3><p>{res['context']}</p></div>""", unsafe_allow_html=True)
        
        with st.chat_message("assistant"):
            if res['bulls']: st.markdown("**🟢 Pros:**"); 
            for f in res['bulls']: st.write(f"- {f}")
            if res['bears']: st.markdown("**🔴 Cons:**"); 
            for f in res['bears']: st.write(f"- {f}")
            st.divider()
            st.info(f"**Advice:** {res['holder_advice']}")
            st.write(f"🛑 Stop Loss: {res['sl']:.2f} | ✅ Take Profit: {res['tp']:.2f}")

    # --- SAVE BUTTON ---
    st.write("---")
    c_btn1, c_btn2 = st.columns([1, 3])
    with c_btn1:
        if st.button("💾 บันทึกผลลงสมุด (Save Journal)"):
            record = {
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Time": datetime.now().strftime("%H:%M"),
                "Symbol": data['symbol'],
                "Price": round(info['price'], 2),
                "Score": res['status'],
                "Strategy": res['action'],
                "Note": f"RSI:{last['RSI']:.0f} | ATR:{atr_pct:.1f}%"
            }
            save_to_journal(record)
            st.success("✅ บันทึกเรียบร้อย!"); time.sleep(1); st.rerun()

# --- 11. Journal Display ---
st.divider()
st.subheader("📓 สมุดจดการเทรด (Trading Journal)")
journal_df = load_journal()
if not journal_df.empty: st.dataframe(journal_df.iloc[::-1], use_container_width=True, hide_index=True)
else: st.info("ยังไม่มีข้อมูลในสมุดจด")
