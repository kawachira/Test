import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

if 'history_log' not in st.session_state:
    st.session_state['history_log'] = []

# --- 2. CSS ---
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
    }
    .xray-box {
        background-color: #f0f9ff; border: 1px solid #bae6fd;
        border-radius: 10px; padding: 15px; margin-bottom: 20px;
    }
    .xray-title {
        font-weight: bold; color: #0369a1; font-size: 1.1rem;
        margin-bottom: 10px; border-bottom: 1px solid #e0f2fe; padding-bottom: 5px;
    }
    .xray-item {
        display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.95rem;
    }
    .fund-box {
        padding: 10px; border-radius: 8px; margin-bottom: 5px; font-size: 0.9rem;
    }
    .fund-good { background-color: #dcfce7; color: #14532d; border: 1px solid #22c55e; }
    .fund-mid { background-color: #fef9c3; color: #713f12; border: 1px solid #eab308; }
    .fund-bad { background-color: #fee2e2; color: #7f1d1d; border: 1px solid #ef4444; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Header & Form ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ (Ultimate Final)🪐</span></h1>", unsafe_allow_html=True)

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
    body = abs(close - open_price)
    wick_upper = high - max(close, open_price)
    wick_lower = min(close, open_price) - low
    total_range = high - low
    color = "🟢 เขียว (Buying)" if close >= open_price else "🔴 แดง (Selling)"
    if total_range == 0: return "Doji (N/A)", color, "N/A", False

    pattern_name = "Normal Candle (ปกติ)"; detail = "แรงซื้อขายสมดุล"; is_big = False
    if wick_lower > (body * 2) and wick_upper < body:
        pattern_name = "Hammer/Pinbar (ค้อน)"; detail = "มีการปฏิเสธราคาต่ำ"
    elif wick_upper > (body * 2) and wick_lower < body:
        pattern_name = "Shooting Star (ดาวตก)"; detail = "มีการปฏิเสธราคาสูง"
    elif body > (total_range * 0.6):
        is_big = True
        if close > open_price: pattern_name = "Big Bullish (แท่งเขียวตัน)"; detail = "แรงซื้อคุมตลาดเบ็ดเสร็จ"
        else: pattern_name = "Big Bearish (แท่งแดงตัน)"; detail = "แรงขายคุมตลาดเบ็ดเสร็จ"
    elif body < (total_range * 0.1):
        pattern_name = "Doji (โดจิ)"; detail = "ตลาดเกิดความลังเล"
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
    return f"""<div style="margin-bottom: 15px;"><div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 5px;"><div style="font-size: 18px; font-weight: 700; opacity: 0.9; color: var(--text-color); white-space: nowrap;">{label}</div><div style="font-size: 24px; font-weight: 700; color: var(--text-color);">{value}</div></div><div style="display: flex; align-items: start; gap: 6px; font-size: 15px; font-weight: 600; color: {color_code}; line-height: 1.4;"><div style="margin-top: 3px; min-width: 24px;">{icon_svg}</div><div>{status_text}</div></div></div>"""

def get_rsi_interpretation(rsi):
    if np.isnan(rsi): return "N/A"
    if rsi >= 70: return "Overbought (ระวังแรงขาย)"
    elif rsi >= 55: return "Bullish (กระทิงแข็งแกร่ง)"
    elif rsi >= 45: return "Sideway/Neutral"
    elif rsi >= 30: return "Bearish (หมีครองตลาด)"
    else: return "Oversold (ระวังเด้งสวน)"

def get_adx_interpretation(adx, is_uptrend):
    if np.isnan(adx): return "N/A"
    trend_str = "ขาขึ้น" if is_uptrend else "ขาลง"
    if adx >= 50: return f"Super Strong {trend_str}"
    if adx >= 25: return f"Strong {trend_str}"
    if adx >= 20: return "Developing Trend"
    return "Weak/Sideway"

def display_learning_section(rsi, rsi_interp, macd_val, macd_signal, macd_interp, adx_val, price, ema200):
    st.markdown("### 📘 มุมความรู้"); 
    with st.expander("คลิกเพื่อเรียนรู้ Indicator", expanded=False):
        st.markdown(f"#### MACD ({macd_val:.3f})\n* โมเมนตัม: {'บวก' if macd_val > macd_signal else 'ลบ'}")
        st.markdown(f"#### RSI ({rsi:.2f})\n* สถานะ: {rsi_interp}")

def filter_levels(levels, threshold_pct=0.025):
    selected = []
    for val, label in levels:
        if np.isnan(val): continue
        if not selected: selected.append((val, label))
        else:
            last_val = selected[-1][0]; diff = abs(val - last_val) / last_val
            if diff > threshold_pct: selected.append((val, label))
    return selected

def analyze_fundamental(info):
    pe = info.get('trailingPE', None); eps_growth = info.get('earningsQuarterlyGrowth', None)
    score = 0
    pe_msg = "N/A"
    if pe:
        pe_msg = f"{pe:.2f}"
        if pe < 0: score -= 2; pe_msg += " (ขาดทุน)"
        elif pe < 20: score += 1; pe_msg += " (ถูก)"
        elif pe > 50: score -= 1; pe_msg += " (แพง)"
    
    growth_msg = "N/A"
    if eps_growth:
        growth_pct = eps_growth * 100; growth_msg = f"{growth_pct:+.2f}%"
        if growth_pct > 15: score += 2; growth_msg += " (โตแรง)"
        elif growth_pct > 0: score += 1
        else: score -= 2; growth_msg += " (กำไรหด)"
    
    if score >= 2: return {"pe": pe_msg, "growth": growth_msg, "status": "Strong Fundamental (งบดี)", "color_class": "fund-good", "summary": "✅ งบแกร่ง", "advice": "ถือยาวได้"}
    elif score <= -2: return {"pe": pe_msg, "growth": growth_msg, "status": "Weak Fundamental (งบเน่า)", "color_class": "fund-bad", "summary": "🔴 งบแย่", "advice": "เก็งกำไรสั้นๆ เท่านั้น"}
    else: return {"pe": pe_msg, "growth": growth_msg, "status": "Moderate (งบกลางๆ)", "color_class": "fund-mid", "summary": "⚖️ งบกลางๆ", "advice": "เล่นตามรอบเทคนิค"}

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
        if not df_mtf.empty:
            df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
        
        try: raw_info = ticker.info 
        except: raw_info = {} 

        # Header Data
        df_header = ticker.history(period="5d", interval="1d")
        if not df_header.empty:
            h_price = df_header['Close'].iloc[-1]
            h_chg = h_price - df_header['Close'].iloc[-2] if len(df_header) > 1 else 0
            h_pct = h_chg / df_header['Close'].iloc[-2] if len(df_header) > 1 else 0
        else: h_price = 0; h_chg = 0; h_pct = 0

        stock_info = {
            'longName': raw_info.get('longName', symbol), 'marketState': raw_info.get('marketState', 'REGULAR'),
            'trailingPE': raw_info.get('trailingPE', None), 'earningsQuarterlyGrowth': raw_info.get('earningsQuarterlyGrowth', None),
            'revenueGrowth': raw_info.get('revenueGrowth', None), 'regularMarketPrice': h_price, 
            'regularMarketChange': h_chg, 'regularMarketChangePercent': h_pct,
            'preMarketPrice': raw_info.get('preMarketPrice'), 'preMarketChange': raw_info.get('preMarketChange'),
            'postMarketPrice': raw_info.get('postMarketPrice'), 'postMarketChange': raw_info.get('postMarketChange'),
            'dayHigh': df_header['High'].iloc[-1] if not df_header.empty else 0,
            'dayLow': df_header['Low'].iloc[-1] if not df_header.empty else 0,
            'regularMarketOpen': df_header['Open'].iloc[-1] if not df_header.empty else 0,
        }
        
        try:
            cal = ticker.calendar
            if cal is not None and not cal.empty:
                if isinstance(cal, pd.DataFrame): stock_info['nextEarnings'] = cal.iloc[0, 0].strftime("%Y-%m-%d") if isinstance(cal.iloc[0, 0], (datetime, pd.Timestamp)) else str(cal.iloc[0, 0])
                elif isinstance(cal, dict): stock_info['nextEarnings'] = cal.get('Earnings Date', ['N/A'])[0]
            else: stock_info['nextEarnings'] = "N/A"
        except: stock_info['nextEarnings'] = "N/A"

        return df, stock_info, df_mtf
    except: return None, None, None

def analyze_volume(row, vol_ma):
    vol = row['Volume']
    if np.isnan(vol_ma): return "Normal", "gray"
    if vol > vol_ma * 1.5: return "High", "green"
    elif vol < vol_ma * 0.7: return "Low", "red"
    else: return "Normal", "gray"

# --- 7. AI Logic ---
def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, vol_status, mtf_trend, atr_val, mtf_ema200_val, open_p, close_p, obv_slope, rolling_min, prev_open, prev_close, vol_now, vol_avg):
    
    score = 0; bullish_factors = []; bearish_factors = []
    
    # Gap
    if prev_close > 0:
        if open_p > prev_close * 1.005: score+=2; bullish_factors.append("🚀 Gap Up (เปิดกระโดด)")
        elif open_p < prev_close * 0.995: score-=2; bearish_factors.append("🩸 Gap Down (เปิดกระโดดลง)")

    # Engulfing
    if prev_close < prev_open and close_p > open_p and close_p > prev_open and open_p < prev_close:
        score+=2; bullish_factors.append("🔥 Bullish Engulfing")
    if prev_close > prev_open and close_p < open_p and close_p < prev_open and open_p > prev_close:
        score-=2; bearish_factors.append("🩸 Bearish Engulfing")

    # Trend
    if price > ema200: score+=2; bullish_factors.append("ราคา > EMA 200 (เทรนด์ขึ้น)")
    else: score-=2; bearish_factors.append("ราคา < EMA 200 (เทรนด์ลง)")
    
    if price > ema20: score+=1
    else: score-=1

    if macd_val > macd_sig: score+=1; bullish_factors.append("MACD > Signal (Bullish)")
    else: score-=1; bearish_factors.append("MACD < Signal (Bearish)")

    # OBV
    obv_stat = "Neutral"
    if obv_slope > 0:
        obv_stat = "Accumulation"; score+=1
        if price < ema20: score+=2; bullish_factors.append("🚀 OBV Divergence (เจ้าเก็บของ)")
    elif obv_slope < 0:
        obv_stat = "Distribution"; score-=1
        if price > ema20: score-=2; bearish_factors.append("⚠️ OBV Divergence (รินขาย)")

    # Volume
    rvol = vol_now / vol_avg if vol_avg > 0 else 0
    if rvol > 3.0: 
        score+=2
        if price > open_p: bullish_factors.append(f"🚀 Vol Explosion {rvol:.1f}x")
        else: bearish_factors.append(f"💥 Vol Explosion {rvol:.1f}x")

    # Result
    if score >= 5: color="green"; title="🚀 Super Nova"; advice="Aggressive Buy"
    elif score >= 1: color="green"; title="📈 Moderate Bullish"; advice="Accumulate"
    elif score >= -2: color="yellow"; title="⚖️ Neutral"; advice="Wait & See"
    else: color="red"; title="🐻 Bearish"; advice="Avoid / Cut Loss"

    # SL/TP
    sl = rolling_min if price > rolling_min else price * 0.95
    tp = price + (3*atr_val) if not np.isnan(atr_val) else price * 1.05
    rrr = (tp - price) / (price - sl) if (price - sl) > 0 else 0
    if rrr > 2: bullish_factors.append(f"💰 RRR สูง ({rrr:.2f})")

    return {"color": color, "title": title, "advice": advice, "bull": bullish_factors, "bear": bearish_factors, "sl": sl, "tp": tp, "obv": obv_stat, "context": "วิเคราะห์ตามเทรนด์"}

# --- 8. Display ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังทำงาน..."):
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)

    if df is not None and not df.empty and len(df) > 10:
        # Calc
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50) # Need EMA50 here
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None: df = pd.concat([df, bb], axis=1)
        df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'], length=14)[f'ADX_14']
        df['Vol_SMA'] = ta.sma(df['Volume'], length=20)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['OBV_Slope'] = ta.slope(df['OBV'], length=5)
        df['Roll_Min'] = df['Low'].rolling(20).min()

        last = df.iloc[-1]
        price = info.get('regularMarketPrice') or last['Close']
        
        # MTF
        mtf_ema50 = np.nan; mtf_ema200 = np.nan
        if df_mtf is not None:
            df_mtf['EMA50'] = ta.ema(df_mtf['Close'], length=50)
            df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
            mtf_ema50 = df_mtf['EMA50'].iloc[-1]
            mtf_ema200 = df_mtf['EMA200'].iloc[-1]

        # Grandparent Logic (TF Hour -> Day -> Week)
        g_ema50 = np.nan; g_ema200 = np.nan
        if tf_code == "1h" and df_mtf is not None:
            try:
                df_wk = df_mtf['Close'].resample('W-FRI').last()
                g_ema50 = ta.ema(df_wk, length=50).iloc[-1]
                g_ema200 = ta.ema(df_wk, length=200).iloc[-1]
            except: pass

        # AI Call
        ai = ai_hybrid_analysis(price, last['EMA20'], last['EMA50'], last['EMA200'], last['RSI'], 
                                last['MACD_12_26_9'], last['MACDs_12_26_9'], last['ADX'], 
                                last.get(bb.columns[2], price*1.05), last.get(bb.columns[0], price*0.95),
                                "Normal", "Sideway", last['ATR'], mtf_ema200, 
                                last['Open'], last['Close'], last['OBV_Slope'], last['Roll_Min'],
                                df['Open'].iloc[-2], df['Close'].iloc[-2], last['Volume'], last['Vol_SMA'])

        # Log
        st.session_state['history_log'].insert(0, {"เวลา": datetime.now().strftime("%H:%M"), "หุ้น": symbol_input, "ราคา": f"{price:.2f}", "Score": ai['title']})

        # --- UI ---
        st.markdown(f"<h2 style='text-align: center;'>{info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
        
        # Status Bar
        m_state = info.get('marketState', 'CLOSED')
        st_msg = "🟢 Market Open" if m_state == "REGULAR" else "🔴 Market Closed/Pre"
        st_bg = "#dcfce7" if m_state == "REGULAR" else "#fee2e2"
        st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><span style='background:{st_bg}; padding: 5px 15px; border-radius: 15px;'>{st_msg}</span></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Price", f"{price:,.2f}", f"{info.get('regularMarketChange', 0):+.2f}")
        
        c_st = "success" if ai['color']=="green" else "error" if ai['color']=="red" else "warning"
        getattr(c2, c_st)(f"### {ai['title']}\n{ai['advice']}")

        c3, c4, c5 = st.columns(3)
        with c3:
            fund = analyze_fundamental(info)
            with st.expander(f"📊 {fund['status']}"):
                st.write(f"P/E: {fund['pe']} | Growth: {fund['growth']}")
                st.info(fund['advice'])
        with c4: st.metric("RSI (14)", f"{last['RSI']:.2f}")
        with c5: st.metric("ADX", f"{last['ADX']:.2f}")

        # --- Indicators & Key Levels ---
        cw1, cw2 = st.columns([1.5, 2])
        with cw1:
            st.subheader("📉 Technical Indicators")
            # EMA 50 Added Here
            e20 = f"{last['EMA20']:.2f}"; e50 = f"{last['EMA50']:.2f}"; e200 = f"{last['EMA200']:.2f}"
            st.markdown(f"""
            <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px;'>
                <div style='display:flex; justify-content:space-between;'><span>EMA 20</span><span>{e20}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>EMA 50</span><span>{e50}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>EMA 200</span><span>{e200}</span></div>
                <div style='display:flex; justify-content:space-between;'><span>MACD</span><span>{last['MACD_12_26_9']:.3f}</span></div>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("🚧 Smart Support")
            # Logic: Nearest First + Parent Injection
            supports = [
                (last.get(bb.columns[0]), "BB Lower"), (last['EMA200'], "EMA 200 (TF)"),
                (last['EMA50'], "EMA 50 (TF)"), (df['Low'].tail(60).min(), "Low 60d"),
                (mtf_ema50, f"EMA 50 {mtf_code.upper()}"), (mtf_ema200, f"🛡️ EMA 200 {mtf_code.upper()}"),
                (g_ema50, "EMA 50 Week") if tf_code=="1h" else (np.nan, ""),
                (g_ema200, "🔥 EMA 200 Week") if tf_code=="1h" else (np.nan, ""),
                (df['Low'].min(), "💎 Major Low")
            ]
            supports.sort(key=lambda x: x[0] if not np.isnan(x[0]) else -1, reverse=True)
            
            cnt = 0
            for v, l in supports:
                if not np.isnan(v) and v < price:
                    st.write(f"- **{v:.2f}** : {l}")
                    cnt+=1
                    if cnt>=4: break
            if cnt==0: st.error("New Low!")

        with cw2:
            st.subheader("🔍 AI Analysis")
            if ai['bull']: st.success("\n".join([f"+ {x}" for x in ai['bull']]))
            if ai['bear']: st.error("\n".join([f"- {x}" for x in ai['bear']]))
            st.info(f"Target: {ai['tp']:.2f} | Stop: {ai['sl']:.2f}")

    else: st.error("ไม่พบข้อมูล")
