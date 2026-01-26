import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (UI สวยงาม) ---
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

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ (Hybrid Sniper)</span></h1>", unsafe_allow_html=True)

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
            # Logic การจับคู่ Timeframe
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
    if np.isnan(ema200):
        is_uptrend = True 
        trend_context = "ไม่สามารถยืนยันเทรนด์ได้ (ข้อมูล EMA 200 ไม่เพียงพอ)"
    else:
        is_uptrend = price > ema200
        
    is_bullish_momentum = macd_val > macd_signal
    
    if not np.isnan(ema200):
        if is_uptrend and is_bullish_momentum:
            trend_context = "ขาขึ้นเต็มตัว (Uptrend) และมีแรงส่งที่ดี"
        elif is_uptrend and not is_bullish_momentum:
            trend_context = "ขาขึ้น (Uptrend) แต่ระยะสั้นกำลังพักตัว/ย่อตัว (Correction)"
        elif not is_uptrend and not is_bullish_momentum:
            trend_context = "ขาลงเต็มตัว (Downtrend) แรงขายยังกดดันต่อเนื่อง"
        else: 
            trend_context = "ขาลง (Downtrend) แต่เริ่มมีการดีดกลับระยะสั้น (Rebound)"
        
    if np.isnan(adx): adx_explain = "⚠️ **ADX:** คำนวณไม่ได้ (ข้อมูลไม่เพียงพอ)"
    elif adx >= 50: adx_explain = f"🔥 **ความแรงเทรนด์:** รุนแรงมาก! ตลาดกำลังอยู่ในสภาวะ '{trend_context}' อย่างหนักหน่วง"
    elif adx >= 25: adx_explain = f"💪 **ความแรงเทรนด์:** แข็งแกร่ง! ทิศทางชัดเจนว่าเป็น '{trend_context}' ไม่ใช่การแกว่งมั่วๆ"
    elif adx >= 20: adx_explain = f"🌱 **ความแรงเทรนด์:** กำลังก่อตัว... เริ่มเห็นทรงว่าเป็น '{trend_context}'"
    else: adx_explain = f"😴 **ความแรงเทรนด์:** ตลาดไร้ทิศทาง (Sideway) แรงซื้อขายยังไม่เลือกทางชัดเจน"

    if np.isnan(rsi): rsi_explain = "⚠️ **RSI:** คำนวณไม่ได้"
    elif rsi >= 70: rsi_explain = "⚠️ **RSI (Overbought):** ราคาขึ้นมาสูงจน 'ตึงมือ' ระวังคนเทขายใส่"
    elif rsi <= 30: rsi_explain = "💎 **RSI (Oversold):** ราคาลงมาลึกจน 'เริ่มถูก' อาจมีเด้งสั้นๆ"
    else: rsi_explain = "⚖️ **RSI (Neutral):** ราคาสมเหตุสมผล ซื้อขายกันตามปกติ"

    if is_bullish_momentum: 
        macd_explain = "🟢 **MACD:** แรงซื้อกลับมานำตลาด (โมเมนตัมบวก)"
    else: 
        macd_explain = "🔴 **MACD:** แรงขายยังคุมตลาดอยู่ (โมเมนตัมลบ)"

    return adx_explain, rsi_explain, macd_explain, trend_context

def display_learning_section(rsi, rsi_interp, macd_val, macd_signal, macd_interp, adx_val, price, ema200, bb_upper, bb_lower):
    is_up = price >= ema200 if not np.isnan(ema200) else True
    adx_interp = get_adx_interpretation(adx_val, is_up)
    
    st.markdown("### 📘 มุมความรู้: ค่าต่างๆ คืออะไร? มาจากไหน?")
    with st.expander("คลิกเพื่อเรียนรู้ความหมายของอินดิเคเตอร์แต่ละตัว", expanded=False):
        st.markdown(f"#### 1. MACD (Moving Average Convergence Divergence)\n* **ค่าปัจจุบัน:** `{macd_val:.3f}` -> {macd_interp}")
        st.markdown("* **คืออะไร?:** เครื่องมือดู 'โมเมนตัม' หรือแรงส่งของราคา\n* **มาจากไหน?:** เกิดจากการเอาเส้นค่าเฉลี่ย 2 เส้นมาลบกัน คือ **EMA(12) - EMA(26)**")
        st.divider()
        st.markdown(f"#### 2. RSI (Relative Strength Index)\n* **ค่าปัจจุบัน:** `{rsi:.2f}` -> {rsi_interp}")
        st.markdown("* **คืออะไร?:** ดัชนีวัดการ 'ซื้อมากเกินไป' หรือ 'ขายมากเกินไป'\n* **มาจากไหน?:** คำนวณจากสัดส่วนของวันที่หุ้นขึ้นเทียบกับวันที่หุ้นลงในรอบ 14 วัน")
        st.divider()
        st.markdown(f"#### 3. ADX (Average Directional Index)\n* **ค่าปัจจุบัน:** `{adx_val:.2f}` -> {adx_interp}")
        st.markdown("* **คืออะไร?:** เครื่องมือวัด 'ความรุนแรงของเทรนด์' (ไม่บอกทิศทาง บอกแค่ว่าแรงไหม)")
        st.divider()
        st.markdown(f"#### 4. Bollinger Bands (BB)\n* **Upper:** `{bb_upper:.2f}` | **Lower:** `{bb_lower:.2f}`")
        st.markdown("* **คืออะไร?:** กรอบการแกว่งตัวของราคาเปรียบเหมือนขอบถนน ถ้าราคาทะลุออกไปมักจะเด้งกลับเข้ามา")

def filter_levels(levels, threshold_pct=0.015):
    selected = []
    for val, label in levels:
        if np.isnan(val): continue
        if not selected: selected.append((val, label))
        else:
            last_val = selected[-1][0]
            diff = abs(val - last_val) / last_val
            if diff > threshold_pct: selected.append((val, label))
    return selected

# --- 5. Data Fetching (Smart Logic) ---
@st.cache_data(ttl=10, show_spinner=False)
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        
        # ✅ SMART SELECTION: เลือกช่วงเวลาตามความเหมาะสมของแต่ละ Timeframe
        if interval == "1wk":
            period_val = "10y"  # Week: 10 ปี (ได้ ~520 แท่ง) เหมาะสุดสำหรับ EMA 200
        elif interval == "1d":
            period_val = "5y"   # Day: 5 ปี (ได้ ~1,250 แท่ง) เหลือเฟือและไม่หนักเครื่อง
        else: # 1h
            period_val = "730d" # Hour: 2 ปี (Max ของ Yahoo)

        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval) # MTF ดึง 10 ปีเสมอ เพื่อให้ EMA 200 Week คำนวณได้ชัวร์
        news = ticker.news
        
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'marketState': ticker.info.get('marketState', 'UNKNOWN'),
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
            'sector': ticker.info.get('sector', 'Unknown'),
        }
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]
             stock_info['regularMarketChangePercent'] = (stock_info['regularMarketChange'] / df['Close'].iloc[-2])
        return df, stock_info, df_mtf, news
    except:
        return None, None, None, None

# --- 6. Analysis Logic ---
def analyze_volume(row, vol_ma):
    vol = row['Volume']
    if np.isnan(vol_ma): return "Normal Volume", "gray"
    if vol > vol_ma * 1.5: return "High Volume", "green"
    elif vol < vol_ma * 0.7: return "Low Volume", "red"
    else: return "Normal Volume", "gray"

def analyze_news_sentiment(news_list):
    if not news_list: return "No News", 0
    score = 0
    bullish_keywords = ['soar', 'jump', 'surge', 'beat', 'profit', 'growth', 'buy', 'strong', 'record', 'up']
    bearish_keywords = ['drop', 'fall', 'plunge', 'miss', 'loss', 'down', 'sell', 'weak', 'crash', 'risk']
    for item in news_list[:5]:
        title = item.get('title', '').lower()
        for w in bullish_keywords: 
            if w in title: score += 1
        for w in bearish_keywords: 
            if w in title: score -= 1
    return score

# --- 7. AI Decision Engine (Master Logic) ---
def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, 
                       vol_status, mtf_trend, news_score, atr_val, mtf_ema200_val):
    score = 0
    bullish_factors = [] 
    bearish_factors = []
    
    # 1. Trend Analysis
    if not np.isnan(ema200):
        if price > ema200:
            score += 3
            bullish_factors.append("ราคาอยู่เหนือเส้น EMA 200 (เทรนด์หลักขาขึ้น)")
            if not np.isnan(ema20) and price > ema20:
                score += 1
                bullish_factors.append("ราคายืนเหนือ EMA 20 (ระยะสั้นแข็งแกร่ง)")
            elif not np.isnan(ema20):
                bearish_factors.append("ระยะสั้นหลุด EMA 20 (มีการพักตัวในขาขึ้น)")
        else:
            score -= 3
            bearish_factors.append("ราคาอยู่ใต้เส้น EMA 200 (เทรนด์หลักขาลง)")
            if not np.isnan(ema20) and price < ema20:
                bearish_factors.append("ราคาอยู่ใต้ EMA 20 (แรงขายระยะสั้นยังกดดัน)")
            elif not np.isnan(ema20):
                bullish_factors.append("ราคาดีดกลับมายืนเหนือ EMA 20 ได้ (ลุ้น Rebound)")
    else:
        bullish_factors.append("ข้อมูลกราฟไม่เพียงพอสำหรับ EMA 200")

    # 2. Momentum
    if not np.isnan(macd_val) and not np.isnan(macd_sig):
        if macd_val > macd_sig:
            score += 1
            bullish_factors.append("MACD ตัดขึ้น (โมเมนตัมบวก)")
        else:
            score -= 1
            bearish_factors.append("MACD ตัดลง (โมเมนตัมลบ/แรงส่งแผ่ว)")

    # 3. MTF Logic (Fix: Use EMA 200 for Long Term Trend)
    mtf_label = "Week" if mtf_trend != "Unknown" else "MTF"
    if mtf_trend == "Bullish":
        score += 2
        bullish_factors.append(f"ภาพใหญ่ ({mtf_label}) ยืนเหนือ EMA 200 เป็นขาขึ้นช่วยหนุน")
    elif mtf_trend == "Bearish":
        score -= 2
        bearish_factors.append(f"ภาพใหญ่ ({mtf_label}) อยู่ใต้ EMA 200 เป็นขาลงกดดันภาพรวม")

    # 4. Volume
    if "High Volume" in vol_status:
        if not np.isnan(ema20) and price > ema20: 
            score += 1
            bullish_factors.append("มีวอลุ่มซื้อเข้ามาสนับสนุนอย่างหนาแน่น")
        else:
            score -= 1
            bearish_factors.append("มีวอลุ่มเทขายออกมาอย่างหนาแน่น")
    elif "Low Volume" in vol_status:
        bearish_factors.append("วอลุ่มเบาบาง (ตลาดขาดความสนใจ)")

    # 5. RSI
    if not np.isnan(rsi):
        if rsi > 70:
            bearish_factors.append(f"RSI สูงระดับ {rsi:.0f} (Overbought) ระวังแรงเทขายทำกำไร")
        elif rsi < 30:
            bullish_factors.append(f"RSI ต่ำระดับ {rsi:.0f} (Oversold) ราคาเริ่มถูก อาจมีเด้งสั้น")

    # --- Strategy Generator ---
    status_color = "yellow"
    banner_title = ""
    strategy_text = ""
    context_text = ""
    holder_advice = ""

    # เตรียมตัวแปรราคาสำหรับโชว์ในข้อความ (Price Embedding)
    e20_str = f"{ema20:,.2f}" if not np.isnan(ema20) else "N/A"
    sl_val = price - (2 * atr_val) if not np.isnan(atr_val) else price * 0.95
    tp_val = price + (3 * atr_val) if not np.isnan(atr_val) else price * 1.05
    sl_str = f"{sl_val:,.2f}"
    
    # Logic 7 Levels
    if score >= 6:
        status_color = "green"
        banner_title = "🚀 Super Nova: กระทิงดุขั้นสุด"
        strategy_text = "Aggressive Buy / Let Profit Run"
        context_text = "ตลาดเข้าสู่สภาวะ 'Euphoria' (ตื่นตัวสุดขีด) ทุก Timeframe เป็นขาขึ้น วอลุ่มซื้อถล่มทลาย ไม่มีแนวต้านขวางกั้น"
        holder_advice = f"🎉 **Jackpot:** กอดหุ้นไว้ให้แน่นที่สุด! อย่าเพิ่งรีบขายหมู ใช้ Trailing Stop (โซน {sl_str}) เกาะไปเรื่อยๆ จนกว่าเทรนด์จะหักหัวลง"

    elif score >= 4:
        status_color = "green"
        banner_title = "🐂 Strong Bullish: ขาขึ้นแข็งแกร่ง"
        strategy_text = "Strong Buy (ซื้อเพิ่ม/ถือต่อ)"
        context_text = "เทรนด์หลักและรองเป็นขาขึ้นชัดเจน โมเมนตัมเป็นบวก แต่อาจมีความร้อนแรงน้อยกว่าระดับสูงสุดเล็กน้อย"
        holder_advice = f"🥳 **Enjoy the ride:** ถือต่อได้อย่างสบายใจ แนวโน้มยังไปต่อได้อีกไกล ถ้ามีย่อตัวใกล้ EMA 20 ({e20_str}) ถือเป็นโอกาสในการเก็บเพิ่ม (Pyramiding)"

    elif score >= 2:
        status_color = "green"
        banner_title = "📈 Moderate Bullish: ขาขึ้นแบบค่อยเป็นค่อยไป"
        strategy_text = "Buy on Dip (ย่อซื้อสะสม)"
        context_text = "ภาพรวมเป็นขาขึ้น แต่ระยะสั้นมีการพักตัวหรือแรงขายทำกำไรออกมาบ้าง ไม่ใช่เรื่องน่าห่วง เป็นการย่อเพื่อไปต่อ"
        holder_advice = f"🙂 **Hold & Watch:** ถือต่อได้ แต่ถ้าหลุดเส้น EMA 20 ({e20_str}) ให้แบ่งขายทำกำไรบางส่วน (Trim) แล้วมารอรับคืนข้างล่างเพื่อลดต้นทุน"

    elif score >= -1:
        status_color = "yellow"
        banner_title = "⚖️ Neutral: เลือกทางไม่ถูก"
        strategy_text = "Wait & See (ทับมือ/รอดูสถานการณ์)"
        context_text = "ตลาดไร้ทิศทาง (Non-Trend) แรงซื้อและแรงขายสู้กันสูสี ราคาแกว่งตัวในกรอบแคบๆ เพื่อรอปัจจัยใหม่มากระตุ้น"
        holder_advice = f"🤔 **Be Patient:** ถ้าทุนต่ำถือรอได้ แต่ถ้าทุนสูงให้ตั้ง Stop Loss ({sl_str}) ไว้ที่กรอบล่างของกล่อง ห้ามลึกกว่านั้น ถ้าราคาไม่ไปไหนนานๆ อาจพิจารณาเปลี่ยนตัวเล่น"

    # ✅ LEVEL 3 (UPDATED): Deep Pullback Strategy
    elif score >= -3:
        status_color = "orange"
        banner_title = "☁️ Weak Warning: พักตัวลึก/ระวังฐานแตก"
        strategy_text = "Defensive / Wait for Reversal (ตั้งการ์ด/รอจุดกลับตัว)"
        context_text = "โมเมนตัมระยะสั้นแผ่วลงชัดเจน คล้ายสภาวะ **'Deep Pullback' (ย่อลึกในขาขึ้น)** ความเสี่ยงยังสูง ห้ามรับมีด! ต้องรอให้แรงขายหมดและราคาสร้างฐานใหม่ให้เสร็จก่อน"
        
        # คำแนะนำแบบ Step-by-Step พร้อมราคา
        holder_advice = (
            f"🦅 **Sniper Mode:** ใจเย็นๆ! อย่าเพิ่งรีบช้อนตอนเห็นสีแดง\n"
            f"1. **Wait:** รอให้กราฟ Day หยุดทำ Low ใหม่ หรือเริ่มออกข้าง\n"
            f"2. **Confirm:** รอให้ราคากลับมายืนเหนือ **EMA 20 ({e20_str})** ให้ได้ก่อน (เพื่อความชัวร์)\n"
            f"3. **Action:** จุดนั้นคือ 'Low Risk, High Reward' ที่ดีที่สุดในการเข้าซื้อเพิ่ม!"
        )

    elif score >= -5:
        status_color = "red"
        banner_title = "🐻 Strong Bearish: ขาลงเต็มตัว"
        strategy_text = "Strong Sell / Avoid (ขายทิ้ง/ห้ามยุ่ง)"
        context_text = "โครงสร้างราคาเสียหาย หลุดแนวรับสำคัญ เทรนด์หลักเปลี่ยนทิศเป็นขาลง แรงขายครองตลาดอย่างสมบูรณ์"
        holder_advice = f"🥶 **Cut Loss Now:** อย่าเสียดาย! การรักษาเงินต้นสำคัญที่สุด ต้องยอมมอบตัวตอนนี้ก่อนที่จะเสียหายหนักกว่าเดิม ห้ามถัวเฉลี่ยขาลงเด็ดขาด จนกว่าจะยืน EMA 20 ({e20_str}) ได้"

    else:
        status_color = "red"
        banner_title = "🩸 Extreme Crash: วิกฤต/เทกระจาด"
        strategy_text = "Run Away (หนีตาย/ล้างพอร์ต)"
        context_text = "เกิดแรงเทขายแบบ Panic Sell รุนแรง! ทุกอินดิเคเตอร์ชี้ลงเหว อาจมีข่าวร้ายแรงมากระทบ เป็นจุดที่อันตรายที่สุด"
        holder_advice = "🚑 **Emergency Exit:** ขายทุกราคา (Market Price) เพื่อเอาชีวิตรอด การถือต่อมีความเสี่ยงที่ราคาจะลงลึกแบบไร้ก้นเหว (Bottomless)"

    return {
        "status_color": status_color,
        "banner_title": banner_title,
        "strategy": strategy_text,
        "context": context_text,
        "bullish_factors": bullish_factors, 
        "bearish_factors": bearish_factors,
        "sl": sl_val,
        "tp": tp_val,
        "holder_advice": holder_advice
    }

# --- 8. Display Execution ---
if submit_btn:
    st.divider()
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)
    
    with st.spinner(f"AI กำลังประมวลผล {symbol_input} แบบ Hybrid Full Loop..."):
        df, info, df_mtf, news = get_data_hybrid(symbol_input, tf_code, mtf_code)

    if df is not None and not df.empty and len(df) > 10: 
        # Calculations
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50)
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        
        bbands = ta.bbands(df['Close'], length=20, std=2)
        if bbands is not None and len(bbands.columns) >= 3:
            bbl_col_name, bbu_col_name = bbands.columns[0], bbands.columns[2]
            df = pd.concat([df, bbands], axis=1)
        else: bbl_col_name, bbu_col_name = None, None

        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        df = pd.concat([df, adx], axis=1)
        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)

        # Last Values
        last = df.iloc[-1]
        price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
        
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

        if bbu_col_name and bbl_col_name: 
            bb_upper, bb_lower = last[bbu_col_name], last[bbl_col_name]
        else: 
            bb_upper, bb_lower = price * 1.05, price * 0.95

        # Inputs for AI
        vol_status, vol_color = analyze_volume(last, last['Vol_SMA20'])
        mtf_trend = "Sideway"
        mtf_ema200_val = 0
        
        if df_mtf is not None and not df_mtf.empty:
            # ✅ FIX: ใช้ EMA 200 แทน EMA 50 สำหรับ Multi-Frame เพื่อความแม่นยำ
            df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200) 
            if len(df_mtf) > 200 and not pd.isna(df_mtf['EMA200'].iloc[-1]):
                mtf_ema200_val = df_mtf['EMA200'].iloc[-1]
                if df_mtf['Close'].iloc[-1] > mtf_ema200_val: mtf_trend = "Bullish"
                else: mtf_trend = "Bearish"
        
        news_score = analyze_news_sentiment(news)
        ai_report = ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, 
                                        vol_status, mtf_trend, news_score, atr, mtf_ema200_val)

        # --- DISPLAY ---
        logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
        fallback_url = "https://cdn-icons-png.flaticon.com/512/720/720453.png"
        icon_html = f"""<img src="{logo_url}" onerror="this.onerror=null; this.src='{fallback_url}';" style="height: 50px; width: 50px; border-radius: 50%; vertical-align: middle; margin-right: 10px; object-fit: contain; background-color: white; border: 1px solid #e0e0e0; padding: 2px;">"""

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
                <div style="font-size:40px; font-weight:600; line-height: 1;">{reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span></div>
                <div style="display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text}; padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">{arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)</div>
            </div>
            """, unsafe_allow_html=True)
            
            def make_pill(change, percent):
                color = "#16a34a" if change >= 0 else "#dc2626"
                bg = "#e8f5ec" if change >= 0 else "#fee2e2"
                arrow = "▲" if change >= 0 else "▼"
                return f'<span style="background:{bg}; color:{color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{arrow} {change:+.2f} ({percent:.2f}%)</span>'
            ohlc_html = ""
            m_state = info.get('marketState', '').upper()
            if m_state != "REGULAR": 
                d_open = info.get('regularMarketOpen'); d_high = info.get('dayHigh'); d_low = info.get('dayLow'); d_close = info.get('regularMarketPrice')
                if d_open and d_high and d_low and d_close:
                    day_chg = info.get('regularMarketChange', 0); val_color = "#16a34a" if day_chg >= 0 else "#dc2626"
                    ohlc_html = f"""<div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; font-family: 'Source Sans Pro', sans-serif; white-space: nowrap; overflow-x: auto;"><span style="margin-right: 5px; opacity: 0.7;">O</span><span style="color: {val_color}; margin-right: 12px;">{d_open:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">H</span><span style="color: {val_color}; margin-right: 12px;">{d_high:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">L</span><span style="color: {val_color}; margin-right: 12px;">{d_low:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">C</span><span style="color: {val_color};">{d_close:.2f}</span></div>"""
            pre_post_html = ""
            if info.get('preMarketPrice') and info.get('preMarketChange'):
                p = info['preMarketPrice']; c = info['preMarketChange']; prev_p = p - c; pct = (c / prev_p) * 100 if prev_p != 0 else 0
                pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">☀️ Pre: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'
            if info.get('postMarketPrice') and info.get('postMarketChange'):
                    p = info['postMarketPrice']; c = info['postMarketChange']; prev_p = p - c; pct = (c / prev_p) * 100 if prev_p != 0 else 0
                    pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">🌙 Post: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'
            if ohlc_html or pre_post_html: st.markdown(f'<div style="margin-top: -5px; margin-bottom: 15px;">{ohlc_html}{pre_post_html}</div>', unsafe_allow_html=True)

        if tf_code == "1h": tf_label = "TF Hour"
        elif tf_code == "1wk": tf_label = "TF Week"
        else: tf_label = "TF Day"
        
        st_color = ai_report["status_color"]
        main_status = ai_report["banner_title"]
        if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
        elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
        else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

        # --- Metrics Section ---
        c3, c4, c5 = st.columns(3)
        
        # SVG Icons
        icon_up_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>"""
        icon_down_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12l7 7 7-7"/></svg>"""
        icon_wave_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#a3a3a3" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12c0-1.5 1-2 2.5-2s2 1 3 1 2-1 3.5-1 2 1 3.5 1 2-1 3-1 2.5.5 2.5 2"/><path d="M4 12v0"/></svg>"""
        icon_flat_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#a3a3a3"><circle cx="12" cy="12" r="10"/></svg>"""

        # 1. P/E Ratio
        with c3:
            pe_val = info['trailingPE']
            pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
            pe_interp = get_pe_interpretation(pe_val)
            if isinstance(pe_val, (int,float)):
                if pe_val < 0: pe_color = "red"; pe_icon = icon_down_svg
                elif pe_val < 15: pe_color = "green"; pe_icon = icon_up_svg
                elif pe_val < 30: pe_color = "green"; pe_icon = icon_flat_svg
                else: pe_color = "red"; pe_icon = icon_down_svg
            else: pe_color = "gray"; pe_icon = icon_flat_svg
            st.markdown(custom_metric_html("📊 P/E Ratio", pe_str, pe_interp, pe_color, pe_icon), unsafe_allow_html=True)

        # 2. RSI
        with c4:
            rsi_str = f"{rsi:.2f}" if not np.isnan(rsi) else "N/A"
            rsi_text = get_rsi_interpretation(rsi)
            if np.isnan(rsi): rsi_color = "gray"; rsi_icon = icon_flat_svg
            elif rsi >= 70: rsi_color = "red"; rsi_icon = icon_up_svg
            elif rsi >= 55: rsi_color = "green"; rsi_icon = icon_up_svg
            elif rsi >= 45: rsi_color = "gray"; rsi_icon = icon_wave_svg
            elif rsi >= 30: rsi_color = "red"; rsi_icon = icon_down_svg
            else: rsi_color = "red"; rsi_icon = icon_down_svg
            st.markdown(custom_metric_html("⚡ RSI (14)", rsi_str, rsi_text, rsi_color, rsi_icon), unsafe_allow_html=True)

        # 3. ADX
        with c5:
            is_uptrend = price >= ema200 if not np.isnan(ema200) else True
            adx_text = get_adx_interpretation(adx_val, is_uptrend)
            adx_str = f"{adx_val:.2f}" if not np.isnan(adx_val) else "N/A"
            
            if np.isnan(adx_val): adx_color = "gray"; adx_icon = icon_flat_svg
            elif adx_val >= 25: 
                if is_uptrend: adx_color = "green"; adx_icon = icon_up_svg
                else: adx_color = "red"; adx_icon = icon_down_svg
            else: 
                adx_color = "gray"; adx_icon = icon_wave_svg
                
            st.markdown(custom_metric_html("💪 ADX Strength", adx_str, adx_text, adx_color, adx_icon), unsafe_allow_html=True)

        st.write("") 

        c_ema, c_ai = st.columns([1.5, 2])
        with c_ema:
            st.subheader("📉 Technical Indicators")
            
            vol_str = format_volume(vol_now)
            e20_s = f"{ema20:.2f}" if not np.isnan(ema20) else "N/A"
            e200_s = f"{ema200:.2f}" if not np.isnan(ema200) else "N/A"
            atr_s = f"{atr:.2f}" if not np.isnan(atr) else "N/A"
            macd_s = f"{macd_val:.3f}" if not np.isnan(macd_val) else "N/A"
            
            st.markdown(f"""
            <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd; font-weight:bold;'><span>Indicator</span> <span>Value</span></div>
                <div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{e20_s}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{e200_s}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>MACD</span> <span>{macd_s}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>Volume ({vol_str})</span> <span style='color:{vol_color}'>{vol_status.split(' ')[0]}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>ATR (ราคาแกว่งเฉลี่ย)</span> <span>{atr_s}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader("🚧 Key Levels (Smart Filter)")
            low_60d = df['Low'].tail(60).min()
            high_60d = df['High'].tail(60).max()
            mtf_label_str = f"EMA 200 ({mtf_code.upper()})" if mtf_ema200_val > 0 else "MTF EMA 200 (N/A)"
            
            # Filter Valid Levels
            potential_supports = [
                (bb_lower, "BB Lower (Volatility)"),
                (low_60d, "Low 60 Days (Price Action)"),
                (ema200, "EMA 200 (Trend Wall)"),
                (mtf_ema200_val, mtf_label_str),
                (ema50, "EMA 50 (Short Trend)"),
                (ema20, "EMA 20 (Momentum)")
            ]
            raw_supports = sorted([x for x in potential_supports if not np.isnan(x[0]) and x[0] < price and x[0] > 0], key=lambda x: x[0], reverse=True)
            valid_supports = filter_levels(raw_supports, threshold_pct=0.015)
            
            potential_resistances = [
                (ema20, "EMA 20 (Momentum)"),
                (ema50, "EMA 50 (Short Trend)"),
                (ema200, "EMA 200 (Trend Wall)"),
                (bb_upper, "BB Upper (Ceiling)"),
                (high_60d, "High 60 Days (Peak)")
            ]
            raw_resistances = sorted([x for x in potential_resistances if not np.isnan(x[0]) and x[0] > price and x[0] > 0], key=lambda x: x[0])
            valid_resistances = filter_levels(raw_resistances, threshold_pct=0.015)
            
            st.markdown("#### 🟢 แนวรับ (Strategic Supports)")
            if valid_supports:
                for v, d in valid_supports[:3]: st.write(f"- **{v:.2f}** : {d}")
            else: st.write("- ราคาทำ All Time High / ไม่มีแนวรับใกล้เคียง")
            
            st.markdown("#### 🔴 แนวต้าน (Resistances)")
            if valid_resistances:
                for v, d in valid_resistances[:3]: st.write(f"- **{v:.2f}** : {d}")
            else: st.write("- ราคาทำ All Time Low / ไม่มีแนวต้านใกล้เคียง")

        with c_ai:
            exp_adx, exp_rsi, exp_macd, exp_trend = get_detailed_explanation(adx_val, rsi, macd_val, macd_signal, price, ema200)
            
            st.subheader("🧐 AI Deep Analysis (ฉบับเข้าใจง่าย)")
            with st.container():
                st.info(f"{exp_adx}")
                st.info(f"{exp_macd}")
                sent_icon = "😊" if news_score > 0 else "😡" if news_score < 0 else "😐"
                st.info(f"📰 **Sentiment:** {sent_icon} Score: {news_score} (ประเมินจากพาดหัวข่าว {len(news)} ข่าวล่าสุด)")

            # ✅ UPDATE: ส่วนแสดงผล Highlight Box
            st.subheader("🤖 AI STRATEGY (บทสรุป)")
            
            color_map = {
                "green": {"bg": "#dcfce7", "border": "#22c55e", "text": "#14532d"},
                "red": {"bg": "#fee2e2", "border": "#ef4444", "text": "#7f1d1d"},
                "orange": {"bg": "#ffedd5", "border": "#f97316", "text": "#7c2d12"},
                "yellow": {"bg": "#fef9c3", "border": "#eab308", "text": "#713f12"}
            }
            c_theme = color_map.get(ai_report['status_color'], color_map["yellow"])

            st.markdown(f"""
            <div style="
                background-color: {c_theme['bg']};
                border-left: 6px solid {c_theme['border']};
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            ">
                <h2 style="color: {c_theme['text']}; margin:0 0 10px 0; font-size: 28px;">
                    {ai_report['banner_title'].split(':')[0]}
                </h2>
                <h3 style="color: {c_theme['text']}; margin:0 0 15px 0; font-size: 20px; opacity: 0.9;">
                    {ai_report['strategy']}
                </h3>
                <p style="color: {c_theme['text']}; font-size: 16px; margin:0; line-height: 1.6;">
                    <b>💡 ภาพรวม:</b> {ai_report['context']}
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.chat_message("assistant"):
                # ✅ Display Factors
                if ai_report['bullish_factors']:
                    st.markdown("**🟢 ปัจจัยสนับสนุนขาขึ้น (Bullish Drivers):**")
                    for r in ai_report['bullish_factors']: st.write(f"- {r}")
                
                if ai_report['bearish_factors']:
                    st.markdown("**🔴 ความเสี่ยงที่ต้องระวัง (Bearish Risks):**")
                    for w in ai_report['bearish_factors']: st.write(f"- {w}")
                
                # ✅ NEW: คำแนะนำสำหรับคนมีของ
                st.markdown("---")
                st.markdown("#### 🎒 คำแนะนำสำหรับคนมีของ (Existing Holders):")
                st.info(ai_report['holder_advice']) 
                    
                st.markdown("---")
                st.markdown(f"**🛡️ แผนควบคุมความเสี่ยง (Risk Management):**")
                st.write(f"🛑 **ตัดขาดทุน (Stop Loss):** {ai_report['sl']:.2f}")
                st.write(f"✅ **ขายทำกำไร (Take Profit):** {ai_report['tp']:.2f}")

        st.write("")
        st.markdown("""<div class='disclaimer-box'>⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากการวิเคราะห์ทางเทคนิคด้วยระบบ AI (Hybrid Logic) เพื่อประกอบการตัดสินใจเท่านั้น <br>ผู้ใช้งานควรศึกษาก่อนการลงทุน ผู้พัฒนาไม่รับผิดชอบต่อความเสียหายใดๆ ที่เกิดขึ้นจากการนำข้อมูลนี้ไปใช้</div>""", unsafe_allow_html=True)
        st.divider()
        
        rsi_interp_str = get_rsi_interpretation(rsi)
        macd_interp_str = "🟢 Bullish" if macd_val > macd_signal else "🔴 Bearish"
        
        display_learning_section(rsi, rsi_interp_str, macd_val, macd_signal, macd_interp_str, adx_val, price, ema200, bb_upper, bb_lower)
    else:
        st.error("ไม่พบข้อมูลหุ้น หรือ ข้อมูลไม่เพียงพอสำหรับคำนวณ Indicator (ต้องมีมากกว่า 200 แท่งเทียน)")
