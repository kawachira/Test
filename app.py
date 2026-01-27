import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Single Frame Pro", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (UI สวยงาม) ---
st.markdown("""
    <style>
    /* ล็อคหน้าจอตอนโหลด */
    body { overflow: hidden; }
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
    
    /* กล่องข้อความ Status (Banner) */
    .status-box {
        padding: 20px; border-radius: 12px; margin-bottom: 20px;
        border-left: 6px solid; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* กล่อง Disclaimer */
    .disclaimer-box {
        margin-top: 20px; padding: 20px; background-color: #fff8e1;
        border: 2px solid #ffc107; border-radius: 12px;
        font-size: 0.9rem; color: #5d4037; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>Single Frame Pro (ฉลาด+ไว) ⚡🧠</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น NVDA, TSLA, BTC-USD)", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            # Map timeframe
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
        
        st.markdown("---")
        realtime_mode = st.checkbox("🔴 เปิดโหมด Real-time (ราคาขยับเองทุก 10 วิ)", value=False)
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ระดับ Pro")

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
    else: color_code = "#6b7280"
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

# --- 5. AI Logic Helpers (ส่วนความฉลาด) ---
def get_detailed_explanation(adx, rsi, macd_val, macd_signal, price, ema200):
    # Trend Context
    if price > ema200: 
        trend = "ขาขึ้น (Uptrend)"
        if macd_val > macd_signal: trend_context = "ขาขึ้นที่แข็งแกร่ง (Strong Uptrend)"
        else: trend_context = "ขาขึ้นที่กำลังพักตัว (Uptrend Correction)"
    else: 
        trend = "ขาลง (Downtrend)"
        if macd_val < macd_signal: trend_context = "ขาลงเต็มตัว (Strong Downtrend)"
        else: trend_context = "ขาลงที่เริ่มมีการเด้ง (Downtrend Rebound)"

    # ADX Logic
    if adx >= 50: adx_explain = f"🔥 **ADX ({adx:.2f}):** เทรนด์แรงระดับ Super Strong! ระวังการกลับตัวฉับพลัน"
    elif adx >= 25: adx_explain = f"💪 **ADX ({adx:.2f}):** เทรนด์แข็งแกร่ง (Strong) ทิศทางชัดเจน"
    else: adx_explain = f"😴 **ADX ({adx:.2f}):** เทรนด์อ่อนแอ/ไซด์เวย์ (Weak/Sideway)"

    # RSI Logic
    if rsi >= 70: rsi_explain = f"⚠️ **RSI ({rsi:.2f}):** Overbought (แพงเกินไป) ระวังแรงเทขาย"
    elif rsi <= 30: rsi_explain = f"💎 **RSI ({rsi:.2f}):** Oversold (ถูกเกินไป) มีโอกาสเด้งสั้นๆ"
    else: rsi_explain = f"⚖️ **RSI ({rsi:.2f}):** Neutral (ปกติ) ราคาสมเหตุสมผล"

    return adx_explain, rsi_explain, trend_context

def analyze_volume(vol_now, vol_ma):
    if vol_now > vol_ma * 1.5: return "High Volume (วอลุ่มเข้า)", "green"
    elif vol_now < vol_ma * 0.7: return "Low Volume (วอลุ่มแห้ง)", "red"
    else: return "Normal Volume (ปกติ)", "gray"

# --- 6. Get Data ---
@st.cache_data(ttl=15, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "5y"
        df = ticker.history(period=period_val, interval=interval)
        
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'marketState': ticker.info.get('marketState', 'UNKNOWN'),
            'regularMarketPrice': ticker.info.get('regularMarketPrice'),
            'regularMarketChange': ticker.info.get('regularMarketChange'),
            # OHLC for Header
            'regularMarketOpen': ticker.info.get('regularMarketOpen'),
            'dayHigh': ticker.info.get('dayHigh'),
            'dayLow': ticker.info.get('dayLow'),
            'preMarketPrice': ticker.info.get('preMarketPrice'),
            'preMarketChange': ticker.info.get('preMarketChange'),
            'postMarketPrice': ticker.info.get('postMarketPrice'),
            'postMarketChange': ticker.info.get('postMarketChange'),
        }
        
        # Fallback if live data is None
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]
             stock_info['dayHigh'] = df['High'].iloc[-1]
             stock_info['dayLow'] = df['Low'].iloc[-1]
             stock_info['regularMarketOpen'] = df['Open'].iloc[-1]
             
        return df, stock_info
    except:
        return None, None

# --- 7. AI Score Engine (สมองกลตัวใหม่) 🧠 ---
def ai_score_system(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, vol_status):
    score = 0
    bullish_factors = []
    bearish_factors = []

    # 1. Trend Structure (Max 3 Points)
    if price > ema200:
        score += 2
        bullish_factors.append("ราคาอยู่เหนือ EMA 200 (เทรนด์หลักขาขึ้น)")
        if price > ema20:
            score += 1
            bullish_factors.append("ราคายืนเหนือ EMA 20 (ระยะสั้นแข็งแกร่ง)")
        else:
            bearish_factors.append("ราคาหลุด EMA 20 (พักตัวระยะสั้น)")
    else:
        score -= 2
        bearish_factors.append("ราคาอยู่ใต้ EMA 200 (เทรนด์หลักขาลง)")
        if price < ema20:
            score -= 1
            bearish_factors.append("ราคาอยู่ใต้ EMA 20 (แรงขายกดดันต่อเนื่อง)")
        else:
            bullish_factors.append("ราคาดีดกลับมายืน EMA 20 ได้ (Rebound)")

    # 2. Momentum (Max 1 Point)
    if macd_val > macd_sig:
        score += 1
        bullish_factors.append("MACD ตัดขึ้น (โมเมนตัมบวก)")
    else:
        score -= 1
        bearish_factors.append("MACD ตัดลง (โมเมนตัมลบ)")

    # 3. Volume Check
    if "High Volume" in vol_status:
        if price > ema20: # วอลุ่มเข้าตอนขึ้น
            score += 1
            bullish_factors.append("มีวอลุ่มซื้อหนาแน่นสนับสนุน")
        else: # วอลุ่มเข้าตอนลง
            score -= 1
            bearish_factors.append("มีวอลุ่มเทขายหนาแน่น")

    # 4. RSI Warning (Deduction only)
    if rsi > 70:
        bearish_factors.append(f"RSI สูง ({rsi:.0f}) เข้าเขต Overbought ระวังแรงขาย")
    elif rsi < 30:
        bullish_factors.append(f"RSI ต่ำ ({rsi:.0f}) เข้าเขต Oversold ลุ้นเด้ง")
    
    # --- Status Interpretation ---
    if score >= 4:
        status_color = "green"
        banner_title = "🚀 Super Bullish: กระทิงดุ (Strong Buy)"
        action = "Follow Trend / Run Profit"
        advice = "เทรนด์แข็งแกร่งมาก ถือต่อหรือหาจังหวะย่อซื้อ (Buy on Dip) ใช้ EMA 20 เป็นจุด Stop Loss"
    elif score >= 1:
        status_color = "green"
        banner_title = "📈 Moderate Bullish: ขาขึ้น (Buy/Hold)"
        action = "Buy on Dip / Hold"
        advice = "ภาพรวมเป็นขาขึ้น แต่อาจมีการพักตัวบ้าง ทยอยสะสมเมื่อราคาย่อมาใกล้เส้น EMA 20 หรือ 50"
    elif score >= -1:
        if rsi < 30: # Sniper Case
            status_color = "orange"
            banner_title = "🔫 Sniper Opportunity: ลุ้นเด้ง (Oversold)"
            action = "Scalp / Swing Trade"
            advice = "ราคาลงแรงเกินไป (Oversold) มีโอกาสเด้งสั้นๆ เข้าไวออกไว (High Risk)"
        else:
            status_color = "yellow"
            banner_title = "⚖️ Neutral/Sideway: รอเลือกทาง"
            action = "Wait & See"
            advice = "ตลาดยังไม่ชัดเจน หรือกำลังพักตัวออกข้าง รอให้เบรคกรอบชัดๆ ก่อนเข้า"
    elif score >= -3:
        status_color = "orange"
        banner_title = "🐻 Weak Bearish: ขาลง/พักตัวลึก"
        action = "Sell on Rally / Wait"
        advice = "ระวัง! แรงขายเริ่มเยอะ ถ้ามีของให้หาจังหวะเด้งเพื่อขายออก อย่าเพิ่งรีบรับจนกว่าจะยืน EMA 20 ได้"
    else:
        status_color = "red"
        banner_title = "🩸 Strong Bearish: เทกระจาด (Strong Sell)"
        action = "Avoid / Cut Loss"
        advice = "อันตราย! โครงสร้างขาลงสมบูรณ์แบบ ห้ามรับมีดเด็ดขาด ถ้าหลุด Low เดิมให้หนีทันที"

    return {
        "score": score,
        "status_color": status_color,
        "banner_title": banner_title,
        "action": action,
        "advice": advice,
        "bullish_factors": bullish_factors,
        "bearish_factors": bearish_factors
    }

# --- 8. Display ---
if submit_btn:
    st.divider()
    
    # ปลดล๊อคหน้าจอให้เลื่อนได้
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)
    
    result_placeholder = st.empty()

    while True:
        with result_placeholder.container():
            with st.spinner(f"AI กำลังประมวลผล {symbol_input} ระดับ Pro..."):
                df, info = get_data(symbol_input, tf_code)

            if df is not None and not df.empty and len(df) > 100:
                # Calculations
                df['EMA20'] = ta.ema(df['Close'], length=20)
                df['EMA50'] = ta.ema(df['Close'], length=50)
                df['EMA200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)
                macd = ta.macd(df['Close'])
                df = pd.concat([df, macd], axis=1)
                adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                df = pd.concat([df, adx], axis=1)
                df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
                
                # Bollinger Bands
                bb = ta.bbands(df['Close'], length=20, std=2)
                df = pd.concat([df, bb], axis=1)
                bb_upper = df.iloc[-1][bb.columns[2]]
                bb_lower = df.iloc[-1][bb.columns[0]]
                
                # Last Values
                last = df.iloc[-1]
                price = info['regularMarketPrice']
                ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
                rsi=last['RSI']; vol_now=last['Volume']; vol_ma=last['Vol_SMA20']
                
                try: macd_val, macd_sig = last['MACD_12_26_9'], last['MACDs_12_26_9']
                except: macd_val, macd_sig = 0, 0
                try: adx_val = last['ADX_14']
                except: adx_val = 0

                # Run AI Score (ส่วนสำคัญที่ต่างจากตัวเก่า)
                vol_status, vol_color = analyze_volume(vol_now, vol_ma)
                report = ai_score_system(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx_val, vol_status)

                # Header Logo & Name
                logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
                icon_html = f"""<img src="{logo_url}" onerror="this.onerror=null; this.src='https://cdn-icons-png.flaticon.com/512/720/720453.png';" style="height:50px;width:50px;border-radius:50%;margin-right:10px;vertical-align:middle;">"""
                st.markdown(f"<h2 style='text-align:center;'>{icon_html} {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)

                # Price Info & OHLC
                c1, c2 = st.columns(2)
                with c1:
                    reg_price = info.get('regularMarketPrice')
                    reg_chg = info.get('regularMarketChange')
                    pct = (reg_chg / (reg_price - reg_chg)) * 100 if reg_price else 0
                    color = "#16a34a" if reg_chg >= 0 else "#dc2626"
                    
                    # Big Price
                    st.markdown(f"""<div style='font-size:40px;font-weight:bold;'>{reg_price:,.2f} <span style='font-size:20px;color:{color};'>{reg_chg:+.2f} ({pct:.2f}%)</span></div>""", unsafe_allow_html=True)
                    
                    # OHLC Pill
                    def make_pill(change, percent):
                        color = "#16a34a" if change >= 0 else "#dc2626"
                        bg = "#e8f5ec" if change >= 0 else "#fee2e2"
                        arrow = "▲" if change >= 0 else "▼"
                        return f'<span style="background:{bg}; color:{color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{arrow} {change:+.2f} ({percent:.2f}%)</span>'

                    # Pre/Post Market
                    if info.get('preMarketPrice'):
                         p = info['preMarketPrice']; c = info['preMarketChange']; pct = (c/(p-c))*100 if p!=c else 0
                         st.markdown(f'<div style="font-size:12px; margin-top:5px;">☀️ Pre: <b>{p:.2f}</b> {make_pill(c, pct)}</div>', unsafe_allow_html=True)

                # AI Status Banner (ส่วนที่สวยงาม)
                color_map = {"green": "#dcfce7", "orange": "#ffedd5", "red": "#fee2e2", "yellow": "#fef9c3"}
                border_map = {"green": "#22c55e", "orange": "#f97316", "red": "#ef4444", "yellow": "#eab308"}
                text_map = {"green": "#14532d", "orange": "#7c2d12", "red": "#7f1d1d", "yellow": "#713f12"}
                c_status = report['status_color']
                
                with c2:
                    st.markdown(f"""
                    <div class="status-box" style="background-color:{color_map[c_status]}; border-left-color:{border_map[c_status]};">
                        <h3 style="color:{text_map[c_status]}; margin:0;">{report['banner_title']}</h3>
                        <p style="color:{text_map[c_status]}; margin:5px 0 0 0; font-weight:bold;">🎯 Action: {report['action']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Main Content
                col_metrics, col_analysis = st.columns([1, 1.5])
                
                with col_metrics:
                    st.subheader("📊 Key Metrics")
                    st.markdown(custom_metric_html("RSI (14)", f"{rsi:.2f}", "Overbought" if rsi>70 else "Oversold" if rsi<30 else "Neutral", "red" if rsi>70 or rsi<30 else "gray", """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>"""), unsafe_allow_html=True)
                    st.markdown(custom_metric_html("MACD", f"{macd_val:.3f}", "Bullish" if macd_val>macd_sig else "Bearish", "green" if macd_val>macd_sig else "red", """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20V10M18 20V4M6 20v-4"/></svg>"""), unsafe_allow_html=True)
                    st.markdown(custom_metric_html("Volume", format_volume(vol_now), vol_status, vol_color, """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/></svg>"""), unsafe_allow_html=True)
                    
                    st.info(f"💡 **AI Advice:** {report['advice']}")
                    
                    # Smart Support/Resistance
                    st.subheader("🚧 Smart Levels")
                    levels = [ema20, ema50, ema200, bb_lower, bb_upper]
                    levels.sort()
                    for lvl in levels:
                        if lvl < price * 0.99: st.write(f"🟢 รับ: {lvl:.2f}")
                        elif lvl > price * 1.01: st.write(f"🔴 ต้าน: {lvl:.2f}")

                with col_analysis:
                    st.subheader("🧐 AI Deep Analysis")
                    adx_exp, rsi_exp, trend_exp = get_detailed_explanation(adx_val, rsi, macd_val, macd_sig, price, ema200)
                    
                    # บทวิเคราะห์ภาษาไทย
                    with st.expander("อ่านบทวิเคราะห์ละเอียด (Click)", expanded=True):
                        st.markdown(f"**1. เทรนด์ (Trend):** {trend_exp}")
                        st.markdown(f"**2. ความแรง (ADX):** {adx_exp}")
                        st.markdown(f"**3. แรงซื้อขาย (RSI):** {rsi_exp}")
                    
                    # Pros & Cons (ฟีเจอร์เด็ดที่มีเฉพาะในตัว Pro)
                    c_pros, c_cons = st.columns(2)
                    with c_pros:
                        if report['bullish_factors']:
                            st.success("**✅ ปัจจัยบวก (Pros)**")
                            for f in report['bullish_factors']: st.write(f"- {f}")
                        else: st.write("- ไม่มีปัจจัยบวกชัดเจน")
                    
                    with c_cons:
                        if report['bearish_factors']:
                            st.error("**❌ ปัจจัยลบ (Cons)**")
                            for f in report['bearish_factors']: st.write(f"- {f}")
                        else: st.write("- ความเสี่ยงต่ำ")

                # Disclaimer
                st.markdown("""
                <div class='disclaimer-box'>
                    ⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากการวิเคราะห์ทางเทคนิคด้วยระบบ AI (Scoring System) เพื่อประกอบการตัดสินใจเท่านั้น
                </div>
                """, unsafe_allow_html=True)

            else:
                st.error("ไม่พบข้อมูลหุ้น หรือข้อมูลไม่เพียงพอ")
        
        if not realtime_mode: break
        time.sleep(10)
