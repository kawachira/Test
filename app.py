import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (คงเดิม 100%) ---
st.markdown("""
    <style>
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
    .disclaimer-box {
        margin-top: 20px; margin-bottom: 20px; padding: 20px;
        background-color: #fff8e1; border: 2px solid #ffc107; border-radius: 12px;
        font-size: 1rem; color: #5d4037; text-align: center; font-weight: 500;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)

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
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
        st.markdown("---")
        realtime_mode = st.checkbox("🔴 เปิดโหมด Real-time (ราคาขยับเองทุก 10 วิ)", value=False)
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที / รีเฟรชข้อมูล")

# --- 4. Helper Functions (คงเดิม) ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

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

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "Extreme Overbought (80+): ระวังแรงขายรุนแรง"
    elif rsi >= 70: return "Overbought (70-80): ราคาตึงตัว อาจพักฐาน"
    elif rsi >= 55: return "Bullish Zone (55-70): โมเมนตัมกระทิงแข็งแกร่ง"
    elif rsi >= 45: return "Sideway/Neutral (45-55): รอเลือกทาง"
    elif rsi >= 30: return "Bearish Zone (30-45): โมเมนตัมหมีครองตลาด"
    elif rsi > 20: return "Oversold (20-30): เริ่มเข้าเขตของถูก"
    else: return "Extreme Oversold (<20): ลงลึกมาก ลุ้นเด้ง"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "N/A"
    if pe < 0: return "ขาดทุน (Loss)"
    if pe < 15: return "หุ้นถูก (Value)"
    if pe < 30: return "ราคาเหมาะสม (Fair)"
    return "หุ้นแพง (Growth)"

def get_adx_interpretation(adx):
    if adx >= 50: return "Super Strong Trend: เทรนด์แรงมาก"
    if adx >= 25: return "Strong Trend: มีเทรนด์ชัดเจน"
    return "Weak Trend/Sideway: ตลาดไร้ทิศทาง"

def display_learning_section(rsi, rsi_interp, macd_val, macd_signal, macd_interp, adx_val, adx_interp, price, bb_upper, bb_lower):
    st.markdown("### 📘 มุมความรู้: ค่าต่างๆ คืออะไร? มาจากไหน?")
    with st.expander("คลิกเพื่อเรียนรู้ความหมายของอินดิเคเตอร์แต่ละตัว", expanded=False):
        st.markdown(f"#### 1. MACD\n* **ค่าปัจจุบัน:** `{macd_val:.3f}` -> {macd_interp}")
        st.divider()
        st.markdown(f"#### 2. RSI\n* **ค่าปัจจุบัน:** `{rsi:.2f}` -> {rsi_interp}")
        st.divider()
        st.markdown(f"#### 3. ADX\n* **ค่าปัจจุบัน:** `{adx_val:.2f}` -> {adx_interp}")

# --- 5. Get Data (คงเดิม) ---
@st.cache_data(ttl=10, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "10y"
        df = ticker.history(period=period_val, interval=interval)
        
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
        }
        
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]
             stock_info['regularMarketChangePercent'] = (stock_info['regularMarketChange'] / df['Close'].iloc[-2])

        return df, stock_info
    except:
        return None, None

# --- 6. AI Logic (คงเดิม) ---
def analyze_market_structure_smart(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, vol_now, vol_ma, atr_val):
    # เริ่มต้น Score System
    score = 0
    reasons = []

    # 1. Trend Analysis (EMA Structure)
    if price > ema200:
        score += 2  # เทรนด์ใหญ่ขาขึ้น
        if price > ema20: score += 1  # ระยะสั้นแข็งแกร่ง
        else: reasons.append("ระยะสั้นย่อตัว (Dip)")
    else:
        score -= 2  # เทรนด์ใหญ่ขาลง
        if price < ema20: score -= 1  # ระยะสั้นลงต่อ
        else: reasons.append("ระยะสั้นเด้งรีบาวด์")

    # 2. Momentum (MACD)
    if macd_val > macd_signal: score += 1
    else: score -= 1

    # 3. Volume Analysis (ความฉลาดที่เพิ่มเข้ามา) 🔊
    vol_status = "Normal"
    if vol_now > vol_ma * 1.5:
        vol_status = "High (มีนัยยะ)"
        if price > ema20: # วอลุ่มเข้าตอนขึ้น = ดี
            score += 1 
            reasons.append("Volume เข้าสนับสนุนขาขึ้น")
        else: # วอลุ่มเข้าตอนลง = แย่
            score -= 1
            reasons.append("แรงขายหนาแน่น (Panic Sell)")
    elif vol_now < vol_ma * 0.7:
        vol_status = "Low (แห้ง)"
        reasons.append("Volume เบาบาง")

    # 4. Volatility (ATR) 📏
    atr_pct = (atr_val / price) * 100
    volatility_msg = "ความผันผวนปกติ"
    if atr_pct > 2.0: # ผันผวนสูง
        volatility_msg = "⚠️ ผันผวนสูง (High Volatility)"
        score -= 0.5 # หักคะแนนความเสี่ยงนิดหน่อย

    # --- สร้าง Report โดยรักษา Structure เดิมของ Single Frame ---
    report = { "technical": {}, "context": "", "action": {}, "status_color": "", "banner_title": "" }

    # แปลง Score เป็น Status
    if score >= 4:
        report["status_color"] = "green"
        report["banner_title"] = "🚀 Super Bullish: ขาขึ้นสมบูรณ์แบบ"
        report["context"] = f"เทรนด์แข็งแกร่งมาก + {reasons[-1] if reasons else ''}. ตลาดยังมีแรงส่งต่อ"
        report["action"] = {"strategy": "**Follow Trend**", "steps": ["ถือต่อ (Let Profit Run)", f"เลื่อน Stop Loss ตาม EMA 20"]}
    elif score >= 1:
        report["status_color"] = "green"
        report["banner_title"] = "Bullish: ขาขึ้น (Buy on Dip)"
        report["context"] = "ภาพรวมยังดี แต่อาจมีการพักตัว รอจังหวะย่อซื้อจะปลอดภัยกว่า"
        report["action"] = {"strategy": "**Buy on Dip**", "steps": [f"รอรับแถว EMA 20 ({ema20:.2f})", f"เผื่อ Stop Loss ด้วย ATR ({atr_val:.2f})"]}
    elif score >= -1:
        # เช็ค Sniper Case (Oversold)
        if rsi < 30 or price < bb_lower:
            report["status_color"] = "orange"
            report["banner_title"] = "🔫 Oversold Bounce: ลุ้นเด้งสั้น"
            report["context"] = f"ราคาลงแรงเกินไป ({volatility_msg}) มีโอกาสเด้งทางเทคนิค"
            report["action"] = {"strategy": "**Sniper (สวนเทรนด์)**", "steps": ["เข้าไว ออกไว (Hit & Run)", "ตั้ง Stop Loss ที่ Low เดิมทันที"]}
        else:
            report["status_color"] = "yellow"
            report["banner_title"] = "Sideway: รอเลือกทาง"
            report["context"] = f"แรงซื้อขายยังก้ำกึ่ง ({volatility_msg}) ควรรอให้เทรนด์ชัดเจนก่อน"
            report["action"] = {"strategy": "**Wait & See**", "steps": ["รอเบรคกรอบ Bollinger Band", "เน้นซื้อแนวรับ ขายแนวต้าน"]}
    else:
        report["status_color"] = "red"
        report["banner_title"] = "Bearish: ขาลงเต็มตัว"
        report["context"] = f"แรงขายครองตลาด + {reasons[-1] if reasons else ''}. การเด้งคือจังหวะขาย"
        report["action"] = {"strategy": "**Defensive / Short**", "steps": ["ห้ามรับมีดเด็ดขาด", "หาจังหวะเด้งเพื่อ Cut Loss"]}

    # อัปเดตข้อมูล Technical ให้ฉลาดขึ้น (โชว์ ATR, Vol)
    report["technical"]["structure"] = f"AI Score: {score:.1f}/5 | Vol: {vol_status}"
    report["technical"]["status"] = f"ATR (ความเหวี่ยง): {atr_val:.2f} ({atr_pct:.1f}%)"

    return report

# --- 7. Display (UI เดิม 100%) ---
if submit_btn:
    st.divider()
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)
    
    result_placeholder = st.empty()
    
    while True:
        with result_placeholder.container():
            with st.spinner(f"AI กำลังประมวลผล {symbol_input} (Smart Logic Engine)..."):
                df, info = get_data(symbol_input, tf_code)

            if df is not None and not df.empty and len(df) > 200:
                # คำนวณ Indicator พื้นฐาน
                df['EMA20'] = ta.ema(df['Close'], length=20)
                df['EMA50'] = ta.ema(df['Close'], length=50)
                df['EMA200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)
                macd = ta.macd(df['Close'])
                df = pd.concat([df, macd], axis=1)
                bbands = ta.bbands(df['Close'], length=20, std=2)
                if bbands is not None:
                     bbl_col, bbu_col = bbands.columns[0], bbands.columns[2]
                     df = pd.concat([df, bbands], axis=1)
                adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                df = pd.concat([df, adx], axis=1)

                # --- 🔥 ส่วนที่เพิ่ม: Advanced Indicators (Volume SMA & ATR) ---
                df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
                df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
                # ---------------------------------------------------------

                last = df.iloc[-1]
                price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
                rsi = last['RSI']
                ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
                
                # ดึงค่าใหม่
                vol_now = last['Volume']
                vol_ma = last['Vol_SMA20'] if pd.notna(last['Vol_SMA20']) else vol_now
                atr_val = last['ATR'] if pd.notna(last['ATR']) else 0
                # ✅ เพิ่มการคำนวณ atr_pct ตรงนี้
                atr_pct = (atr_val / price) * 100 if price else 0

                try: macd_val, macd_signal = last['MACD_12_26_9'], last['MACDs_12_26_9']
                except: macd_val, macd_signal = 0, 0
                try: adx_val = last['ADX_14']
                except: adx_val = 0

                if bbu_col and bbl_col: bb_upper, bb_lower = last[bbu_col], last[bbl_col]
                else: bb_upper, bb_lower = price * 1.05, price * 0.95
                
                # --- เรียกใช้ Logic ใหม่ (Smart Logic) ---
                ai_report = analyze_market_structure_smart(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, vol_now, vol_ma, atr_val)

                # --- ส่วนแสดงผล (คงเดิมทุกประการ) ---
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
                      <div style="font-size:40px; font-weight:600; line-height: 1;">
                        {reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span>
                      </div>
                      <div style="display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text}; padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">
                        {arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # OHLC Pill & Pre/Post Logic (คงเดิมตามคำขอ)
                    def make_pill(change, percent):
                        color = "#16a34a" if change >= 0 else "#dc2626"
                        bg = "#e8f5ec" if change >= 0 else "#fee2e2"
                        arrow = "▲" if change >= 0 else "▼"
                        return f'<span style="background:{bg}; color:{color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{arrow} {change:+.2f} ({percent:.2f}%)</span>'

                    ohlc_html = ""
                    m_state = info.get('marketState', '').upper()
                    if m_state != "REGULAR": 
                        d_open = info.get('regularMarketOpen')
                        d_high = info.get('dayHigh')
                        d_low = info.get('dayLow')
                        d_close = info.get('regularMarketPrice')
                        if d_open and d_high and d_low and d_close:
                            day_chg = info.get('regularMarketChange', 0)
                            val_color = "#16a34a" if day_chg >= 0 else "#dc2626"
                            ohlc_html = f"""
                            <div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; font-family: 'Source Sans Pro', sans-serif; white-space: nowrap; overflow-x: auto;">
                                <span style="margin-right: 5px; opacity: 0.7;">O</span><span style="color: {val_color}; margin-right: 12px;">{d_open:.2f}</span>
                                <span style="margin-right: 5px; opacity: 0.7;">H</span><span style="color: {val_color}; margin-right: 12px;">{d_high:.2f}</span>
                                <span style="margin-right: 5px; opacity: 0.7;">L</span><span style="color: {val_color}; margin-right: 12px;">{d_low:.2f}</span>
                                <span style="margin-right: 5px; opacity: 0.7;">C</span><span style="color: {val_color};">{d_close:.2f}</span>
                            </div>"""

                    pre_post_html = ""
                    if info.get('preMarketPrice') and info.get('preMarketChange'):
                        p = info['preMarketPrice']; c = info['preMarketChange']; pct = (c/(p-c))*100 if p!=c else 0
                        pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">☀️ Pre: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'
                    if info.get('postMarketPrice') and info.get('postMarketChange'):
                         p = info['postMarketPrice']; c = info['postMarketChange']; pct = (c/(p-c))*100 if p!=c else 0
                         pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">🌙 Post: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'

                    if ohlc_html or pre_post_html:
                        st.markdown(f'<div style="margin-top: -5px; margin-bottom: 15px;">{ohlc_html}{pre_post_html}</div>', unsafe_allow_html=True)
                    
                if tf_code == "1h": tf_label = "TF Hour"
                elif tf_code == "1wk": tf_label = "TF Week"
                else: tf_label = "TF Day"
                
                st_color = ai_report["status_color"]
                main_status = ai_report["banner_title"]
                if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
                elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
                else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

                c3, c4, c5 = st.columns(3)
                # Icons
                icon_up_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>"""
                icon_down_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12l7 7 7-7"/></svg>"""
                icon_flat_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#6b7280"><circle cx="12" cy="12" r="10"/></svg>"""
                icon_wave_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l3-3-3-3"/><path d="M6 9l-3 3 3 3"/><path d="M21 12H3"/></svg>"""

                with c3:
                    pe_val = info['trailingPE']
                    pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
                    pe_interp = get_pe_interpretation(pe_val)
                    pe_color = "gray"; pe_icon = icon_flat_svg
                    if isinstance(pe_val, (int,float)):
                        if pe_val < 0: pe_color = "red"; pe_icon = icon_down_svg
                        elif pe_val < 15: pe_color = "green"; pe_icon = icon_up_svg
                        elif pe_val < 30: pe_color = "green"; pe_icon = icon_flat_svg
                        else: pe_color = "red"; pe_icon = icon_down_svg
                    st.markdown(custom_metric_html("📊 P/E Ratio", pe_str, pe_interp, pe_color, pe_icon), unsafe_allow_html=True)

                with c4:
                    rsi_interp = get_rsi_interpretation(rsi)
                    if rsi >= 70: c_stat = "red"; icon_final = icon_up_svg
                    elif rsi >= 55: c_stat = "green"; icon_final = icon_up_svg
                    elif rsi >= 45: c_stat = "gray"; icon_final = icon_flat_svg
                    elif rsi >= 30: c_stat = "red"; icon_final = icon_down_svg
                    else: c_stat = "green"; icon_final = icon_down_svg
                    st.markdown(custom_metric_html("⚡ RSI (14)", f"{rsi:.2f}", rsi_interp, c_stat, icon_final), unsafe_allow_html=True)

                with c5:
                    adx_interp = get_adx_interpretation(adx_val)
                    c_stat = "green" if adx_val > 25 else "gray"
                    icon_final = icon_up_svg if adx_val > 25 else icon_wave_svg
                    st.markdown(custom_metric_html("💪 ADX Strength", f"{adx_val:.2f}", adx_interp, c_stat, icon_final), unsafe_allow_html=True)

                st.write("") 
                c_ema, c_ai = st.columns([1.5, 2])
                with c_ema:
                    st.subheader("📉 Technical Indicators")
                    # ✅ เพิ่ม (เปอร์เซ็นต์) ตรงนี้
                    st.markdown(f"""
                    <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'>
                        <div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd; font-weight:bold;'><span>Indicator</span> <span>Value</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{ema20:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 50</span> <span>{ema50:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{ema200:.2f}</span></div>
                        <div style='margin-top:5px; margin-bottom:5px; border-bottom:1px solid #ddd;'></div>
                        <div style='display:flex; justify-content:space-between;'><span>MACD</span> <span style='color:{'green' if macd_val > macd_signal else 'red'}'>{macd_val:.3f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>ATR (Volat)</span> <span>{atr_val:.2f} ({atr_pct:.1f}%)</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>Volume</span> <span>{vol_now/1000:.1f}K</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.subheader("🚧 Key Levels")
                    # ... (Logic เดิมของ Key Levels คงไว้) ...
                    potential_levels = [
                        (ema20, "EMA 20"), (ema50, "EMA 50"), (ema200, "EMA 200"),
                        (bb_lower, "BB Lower"), (bb_upper, "BB Upper"),
                        (df['High'].tail(60).max(), "High 60 Days"), (df['Low'].tail(60).min(), "Low 60 Days")
                    ]
                    raw_supports = []; raw_resistances = []
                    for val, label in potential_levels:
                        if val < price: raw_supports.append((val, label))
                        elif val > price: raw_resistances.append((val, label))
                    raw_supports.sort(key=lambda x: x[0], reverse=True)
                    raw_resistances.sort(key=lambda x: x[0])
                    def filter_levels(levels, threshold_pct=0.015):
                        selected = []
                        for val, label in levels:
                            if not selected: selected.append((val, label))
                            else:
                                last_val = selected[-1][0]
                                if abs(val - last_val) / last_val > threshold_pct: selected.append((val, label))
                        return selected
                    final_supports = filter_levels(raw_supports)[:3]
                    final_resistances = filter_levels(raw_resistances)[:2]
                    st.markdown("#### 🟢 แนวรับ (จุดรอซื้อ)")
                    if final_supports: 
                        for v, d in final_supports: st.write(f"- **{v:.2f}** : {d}")
                    else: st.write("- ไม่มีแนวรับใกล้เคียง")
                    st.markdown("#### 🔴 แนวต้าน (จุดรอขาย)")
                    if final_resistances: 
                        for v, d in final_resistances: st.write(f"- **{v:.2f}** : {d}")
                    else: st.write("- ไม่มีแนวต้านใกล้เคียง")

                with c_ai:
                    # AI Context ฉลาดขึ้น (มีข้อมูล ATR/Vol ใน report['technical'])
                    st.subheader("🧐 AI Explanation")
                    with st.container():
                        # แสดงผล structure ที่คำนวณจาก Logic ใหม่
                        st.info(f"🧠 **AI Logic:** {ai_report['technical']['structure']}")
                        st.info(f"📏 **Volatility:** {ai_report['technical']['status']}")
                        
                    st.subheader("🤖 AI STRATEGY")
                    with st.chat_message("assistant"):
                        st.markdown(f"### 🎯 {ai_report['action']['strategy']}")
                        for step in ai_report['action']['steps']: st.write(f"- {step}")
                        st.markdown("---")
                        st.info(f"**👁️ มุมมอง:**\n\n{ai_report['context']}")

                st.write("")
                st.markdown("""
                <div class='disclaimer-box'>
                    ⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากการวิเคราะห์ทางเทคนิคด้วยระบบ AI เพื่อประกอบการตัดสินใจเท่านั้น <br>
                    ผู้ใช้งานควรศึกษาก่อนการลงทุน ผู้พัฒนาไม่รับผิดชอบต่อความเสียหายใดๆ ที่เกิดขึ้นจากการนำข้อมูลนี้ไปใช้
                </div>
                """, unsafe_allow_html=True)
                st.divider()
                
                # Learning Section (คงเดิม)
                display_learning_section(rsi, get_rsi_interpretation(rsi), macd_val, macd_signal, "Bull/Bear", adx_val, get_adx_interpretation(adx_val), price, bb_upper, bb_lower)

            else:
                st.error("ไม่พบข้อมูลหุ้น หรือ ข้อมูลไม่เพียงพอสำหรับคำนวณ Indicator")
        
        if not realtime_mode: break
        time.sleep(10)
