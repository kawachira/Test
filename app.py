import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import requests
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master Pro", page_icon="💎", layout="wide")

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
    .disclaimer-box {
        margin-top: 20px; padding: 20px; background-color: #fff8e1;
        border: 2px solid #ffc107; border-radius: 12px;
        font-size: 0.9rem; color: #5d4037; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai Pro<br><span style='font-size: 1.2rem; opacity: 0.7;'>Institutional Grade Analysis System</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น (Full Stream Analysis)")
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
        submit_btn = st.form_submit_button("🚀 วิเคราะห์เชิงลึก (AI Full Loop)")

# --- 4. Helper Functions (Display) ---
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

# --- 5. Advanced Data Fetching (Main + MTF + News) ---
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

# --- 6. Analysis Logic Modules ---

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
    
    relevant_news = []
    
    for item in news_list[:5]: # เช็ค 5 ข่าวล่าสุด
        title = item.get('title', '').lower()
        found = False
        for word in bullish_keywords:
            if word in title:
                score += 1
                found = True
        for word in bearish_keywords:
            if word in title:
                score -= 1
                found = True
            
    if score >= 1: return "Positive (ข่าวดี)", score
    elif score <= -1: return "Negative (ข่าวร้าย)", score
    else: return "Neutral (ข่าวทรงๆ)", score

# --- 7. The SUPER AI Decision Engine ---
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
    
    # 1. Trend Analysis (Weight: 40%)
    trend_state = "Sideway"
    if price > ema200 and price > ema50:
        if price > ema20: 
            trend_state = "Strong Uptrend"
            score += 3
            reasons.append("ราคายืนเหนือ EMA ทุกเส้น (Bullish Structure)")
        else:
            trend_state = "Uptrend Pullback"
            score += 1
            reasons.append("เทรนด์หลักขาขึ้น แต่ระยะสั้นย่อตัว")
    elif price < ema200 and price < ema50:
        trend_state = "Downtrend"
        score -= 3
        reasons.append("ราคาอยู่ใต้ EMA ทุกเส้น (Bearish Structure)")
    
    # 2. MTF Confirmation (Weight: 20%)
    if mtf_trend == "Bullish":
        if score > 0: 
            score += 2
            reasons.append(f"Timeframe ใหญ่สนับสนุนขาขึ้น (Confluence)")
        elif score < 0:
            warnings.append("Timeframe ใหญ่ขัดแย้ง (ระวังเด้งเพื่อลงต่อ)")
    elif mtf_trend == "Bearish":
        if score < 0:
            score -= 2
            reasons.append(f"Timeframe ใหญ่ยืนยันขาลง")
        elif score > 0:
            warnings.append("Timeframe ใหญ่เป็นขาลง (ระวัง Bull Trap)")
            score -= 1 # ลดคะแนนความมั่นใจ

    # 3. Momentum & Volume (Weight: 20%)
    if rsi > 50 and macd_val > macd_sig:
        score += 1
        reasons.append("Momentum เป็นบวก (RSI>50, MACD Cross)")
    elif rsi < 50 and macd_val < macd_sig:
        score -= 1
        
    if "High Volume" in vol_status:
        if candle_color == "green": 
            score += 1
            reasons.append("Volume เข้าสนับสนุนการขึ้น")
        elif candle_color == "red":
            score -= 1
            reasons.append("Volume ขายออกมาเยอะมาก")
    
    if obv_slope > 0: reasons.append("OBV ชี้ขึ้น (เงินไหลเข้าสะสม)")
    
    # 4. Overbought/Oversold & Risk (Correction)
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
        with st.spinner(f"🤖 AI Pro กำลังรวบรวมข้อมูล Big Data และวิเคราะห์ {symbol_input}..."):
            # 1. Fetch Data
            df, df_mtf, news, info = get_data_pro(symbol_input, tf_code, mtf_code)
        
        if df is None or df.empty or len(df) < 200:
            st.error("❌ ไม่พบข้อมูลหุ้น หรือข้อมูลไม่เพียงพอสำหรับการวิเคราะห์ขั้นสูง (ต้องมี Data > 200 แท่ง)")
            break
        else:
            # 2. Calculate Indicators (Batch Calculation)
            # Main Timeframe
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # --- FIX: Explicitly name the ATR column ---
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            # -------------------------------------------
            
            macd = ta.macd(df['Close'])
            df = pd.concat([df, macd], axis=1)
            
            bb = ta.bbands(df['Close'], length=20, std=2)
            df = pd.concat([df, bb], axis=1)
            
            adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            df = pd.concat([df, adx], axis=1)
            
            # Volume Indicators
            df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
            df['OBV'] = ta.obv(df['Close'], df['Volume'])
            
            # MTF Calculation (Simplified Trend Check)
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
            
            # OBV Slope
            try:
                obv_slope = last['OBV'] - df['OBV'].iloc[-5] 
            except:
                obv_slope = 0

            # 5. Run AI Engine
            ai_result = ai_decision_engine(
                price, last['EMA20'], last['EMA50'], last['EMA200'],
                rsi, macd_val, macd_sig, adx_val,
                bb_up, bb_low,
                vol_status, obv_slope,
                mtf_trend,
                candle_pattern, candle_color,
                atr
            )

            # --- DISPLAY SECTION ---
            
            # Header & Price
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

            # Dashboard Metrics
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

            # Main Strategy Banner
            st.markdown("---")
            strat_color = "success" if ai_result['score'] > 2 else "error" if ai_result['score'] < -2 else "warning"
            
            if strat_color == "success": st.success(f"## {ai_result['strategy']}")
            elif strat_color == "error": st.error(f"## {ai_result['strategy']}")
            else: st.warning(f"## {ai_result['strategy']}")
            
            # Deep Dive Analysis
            c_chart, c_logic = st.columns([1.5, 2])
            
            with c_chart:
                st.subheader("📉 Risk Management (ATR Based)")
                st.info(f"""
                **🎯 แผนการเทรด (Trade Setup):**
                
                * **Entry:** {price:.2f} (ราคาปัจจุบัน)
                * **🛑 Stop Loss:** **{ai_result['sl']:.2f}** (ระยะห่าง {price - ai_result['sl']:.2f})
                * **✅ Take Profit:** **{ai_result['tp']:.2f}** (Reward Ratio 1:{abs(ai_result['tp']-price)/abs(price-ai_result['sl']):.1f})
                * **Volatility (ATR):** {atr:.2f} (หุ้นเหวี่ยงตัวประมาณนี้ต่อแท่ง)
                """)
                
                st.subheader("🌍 Multi-Timeframe Status")
                mtf_color = "green" if mtf_trend == "Bullish" else "red" if mtf_trend == "Bearish" else "orange"
                st.markdown(f"""
                * **Main TF ({tf_code}):** {ai_result['trend_state']}
                * **Big Picture ({mtf_code}):** <span style='color:{mtf_color}; font-weight:bold;'>{mtf_trend} Trend</span>
                """, unsafe_allow_html=True)

            with c_logic:
                st.subheader("🧠 AI Logic & Reasoning")
                
                # Reasons (Pros)
                if ai_result['reasons']:
                    st.markdown("**✅ ปัจจัยสนับสนุน (Pros):**")
                    for r in ai_result['reasons']: st.markdown(f"- {r}")
                
                # Warnings (Cons)
                if ai_result['warnings']:
                    st.markdown("**⚠️ ปัจจัยเสี่ยง (Cons/Risks):**")
                    for w in ai_result['warnings']: st.markdown(f"- {w}")
                    
                st.markdown("---")
                st.subheader("📝 Action Step")
                for step in ai_result['action']:
                    st.write(f"👉 {step}")

            # News Expander
            with st.expander("📰 อ่านหัวข้อข่าวที่ AI ใช้ประเมิน (Click to expand)", expanded=False):
                if news:
                    for n in news[:5]:
                        try:
                            # Handle different yahoo finance news formats
                            link = n.get('link', '#')
                            title = n.get('title', 'No Title')
                            pub_time = n.get('providerPublishTime', 0)
                            date_str = datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d')
                            st.write(f"- [{title}]({link}) ({date_str})")
                        except:
                            pass
                else:
                    st.write("- ไม่มีข้อมูลข่าวล่าสุด")

            st.markdown("<div class='disclaimer-box'>⚠️ <b>Disclaimer:</b> ระบบ Pro นี้ใช้ AI Decision Tree ขั้นสูงในการประมวลผลข้อมูล 5 มิติ (Price, Vol, Timeframe, Risk, Sentiment) แต่การลงทุนยังมีความเสี่ยง โปรดใช้ Money Management อย่างเคร่งครัด</div>", unsafe_allow_html=True)

        if not realtime_mode: break
        time.sleep(10)
        st.rerun()
