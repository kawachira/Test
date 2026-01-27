import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import random
import time

# --- 1. ตั้งค่าหน้าเว็บ (เหมือนเดิม) ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (ตัวเดิมที่คุณชอบ) ---
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
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ (Smart Engine 🧠)</span></h1>", unsafe_allow_html=True)

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

# --- 4. Helper Functions ---
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

# --- Functions แปลผล (จากตัวเดิม) ---
def get_rsi_interpretation(rsi):
    if rsi >= 80: return "Extreme Overbought (80+): ระวังแรงขาย"
    elif rsi >= 70: return "Overbought (70-80): ตึงตัว พักฐาน"
    elif rsi >= 55: return "Bullish Zone (55-70): กระทิงดุ"
    elif rsi >= 45: return "Sideway/Neutral (45-55): รอเลือกทาง"
    elif rsi >= 30: return "Bearish Zone (30-45): หมีครองตลาด"
    elif rsi > 20: return "Oversold (20-30): เริ่มถูก"
    else: return "Extreme Oversold (<20): ถูกมาก ลุ้นเด้ง"

def get_adx_interpretation(adx):
    if adx >= 50: return "Super Strong: เทรนด์แรงมาก"
    if adx >= 25: return "Strong: เทรนด์ชัดเจน"
    return "Weak/Sideway: ไร้ทิศทาง"

def display_learning_section(rsi, rsi_interp, macd_val, macd_signal, macd_interp, adx_val, adx_interp, price, bb_upper, bb_lower):
    st.markdown("### 📘 มุมความรู้: ค่าต่างๆ คืออะไร? มาจากไหน?")
    with st.expander("คลิกเพื่อเรียนรู้ความหมายของอินดิเคเตอร์แต่ละตัว", expanded=False):
        st.markdown(f"#### 1. MACD\n* **ค่าปัจจุบัน:** `{macd_val:.3f}` -> {macd_interp}\n* **คือ:** โมเมนตัมของราคา")
        st.divider()
        st.markdown(f"#### 2. RSI\n* **ค่าปัจจุบัน:** `{rsi:.2f}` -> {rsi_interp}\n* **คือ:** ดัชนีวัดการซื้อ/ขายมากเกินไป")
        st.divider()
        st.markdown(f"#### 3. ADX\n* **ค่าปัจจุบัน:** `{adx_val:.2f}` -> {adx_interp}\n* **คือ:** ความรุนแรงของเทรนด์")

# --- 5. New Smart Logic (สมองใหม่ ใส่ในร่างเดิม) 🧠 ---
def analyze_volume(vol_now, vol_ma):
    if vol_now > vol_ma * 1.5: return "High Volume (วอลุ่มเข้า)", "green"
    elif vol_now < vol_ma * 0.7: return "Low Volume (วอลุ่มแห้ง)", "red"
    else: return "Normal Volume (ปกติ)", "gray"

def ai_smart_logic(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, vol_status):
    # เริ่มต้นคะแนน 0
    score = 0
    bullish_factors = []
    bearish_factors = []
    
    # 1. Trend (EMA)
    if price > ema200:
        score += 2; bullish_factors.append("ราคา > EMA 200 (เทรนด์หลักขาขึ้น)")
        if price > ema20: score += 1; bullish_factors.append("ราคา > EMA 20 (ระยะสั้นแข็งแกร่ง)")
        else: bearish_factors.append("ราคาหลุด EMA 20 (พักตัวระยะสั้น)")
    else:
        score -= 2; bearish_factors.append("ราคา < EMA 200 (เทรนด์หลักขาลง)")
        if price < ema20: score -= 1; bearish_factors.append("ราคา < EMA 20 (แรงขายกดดัน)")
        else: bullish_factors.append("ราคา Rebound ยืนเหนือ EMA 20 ได้")

    # 2. Momentum (MACD)
    if macd_val > macd_signal: score += 1; bullish_factors.append("MACD ตัดขึ้น (Buy Signal)")
    else: score -= 1; bearish_factors.append("MACD ตัดลง (Sell Signal)")

    # 3. Volume
    if "High Volume" in vol_status:
        if price > ema20: score += 1; bullish_factors.append("Volume เข้าสนับสนุนขาขึ้น")
        else: score -= 1; bearish_factors.append("Volume เทขายหนาแน่น")

    # 4. RSI Check
    if rsi > 70: bearish_factors.append(f"RSI Overbought ({rsi:.0f}) ระวังแรงเทขาย")
    elif rsi < 30: bullish_factors.append(f"RSI Oversold ({rsi:.0f}) ลุ้นเด้ง")

    # ตัดสินผลลัพธ์ (Mapping to Original UI Structure)
    report = { "technical": {}, "context": "", "action": {}, "status_color": "", "banner_title": "", "pros": bullish_factors, "cons": bearish_factors, "score": score }

    if score >= 4:
        report["status_color"] = "green"
        report["banner_title"] = "🚀 Super Bullish: กระทิงดุ"
        report["context"] = "เทรนด์แข็งแกร่งมาก มีวอลุ่มสนับสนุน โอกาสไปต่อสูง"
        report["action"] = {"strategy": "**Follow Trend / Let Profit Run**", "steps": ["ถือต่อ ใช้ EMA 20 เป็นจุด Stop Loss", "ถ้ามีกำไรให้แบ่งขายบางส่วนเมื่อ RSI สูงจัด"]}
    elif score >= 1:
        report["status_color"] = "green"
        report["banner_title"] = "📈 Moderate Bullish: ขาขึ้น"
        report["context"] = "ภาพรวมเป็นขาขึ้น แต่อาจมีการพักตัวบ้าง"
        report["action"] = {"strategy": "**Buy on Dip (ย่อซื้อ)**", "steps": ["รอราคาย่อมาที่ EMA 20 หรือ 50", "สะสมของเมื่อ RSI ต่ำลง"]}
    elif score >= -1:
        # เช็คกรณีพิเศษ Sniper (Oversold Bounce)
        if rsi < 30 or price < bb_lower:
            report["status_color"] = "orange"
            report["banner_title"] = "🔫 Sniper: ลุ้นเด้ง (Oversold)"
            report["context"] = "ราคาลงแรงเกินไป (Oversold) มีโอกาสเด้งสั้นๆ"
            report["action"] = {"strategy": "**Scalp / เด้งเพื่อขาย**", "steps": ["เข้าเร็ว ออกเร็ว (Hit & Run)", "ตั้ง Stop Loss ที่ Low เดิมทันที"]}
        else:
            report["status_color"] = "yellow"
            report["banner_title"] = "⚖️ Sideway: รอเลือกทาง"
            report["context"] = "แรงซื้อและขายยังก้ำกึ่ง ไม่ชัดเจน"
            report["action"] = {"strategy": "**Wait & See**", "steps": ["รอเบรคกรอบ EMA หรือ Bollinger Band", "เน้นซื้อแนวรับ ขายแนวต้าน"]}
    else:
        report["status_color"] = "red"
        report["banner_title"] = "🐻 Bearish: ขาลงเต็มตัว"
        report["context"] = "แรงขายครองตลาด เทรนด์หลักเป็นขาลงชัดเจน"
        report["action"] = {"strategy": "**Avoid / Short Sell**", "steps": ["ห้ามรับมีดเด็ดขาด", "ถ้ามีของ ให้หาจังหวะเด้งเพื่อขายหนี (Cut Loss)"]}

    # Technical Text (เพื่อความเข้ากันได้กับโค้ดเดิม)
    report["technical"]["structure"] = f"AI Score: {score}/5"
    report["technical"]["status"] = f"RSI: {rsi:.0f} | ADX: {adx_val:.0f}"
    
    return report

# --- 6. Get Data ---
@st.cache_data(ttl=10, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "10y"
        df = ticker.history(period=period_val, interval=interval)
        
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'regularMarketPrice': ticker.info.get('regularMarketPrice'),
            'regularMarketChange': ticker.info.get('regularMarketChange'),
            # OHLC
            'regularMarketOpen': ticker.info.get('regularMarketOpen'),
            'dayHigh': ticker.info.get('dayHigh'),
            'dayLow': ticker.info.get('dayLow'),
            'preMarketPrice': ticker.info.get('preMarketPrice'),
            'preMarketChange': ticker.info.get('preMarketChange'),
            'postMarketPrice': ticker.info.get('postMarketPrice'),
            'postMarketChange': ticker.info.get('postMarketChange'),
        }
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]
             stock_info['dayHigh'] = df['High'].iloc[-1]
             stock_info['dayLow'] = df['Low'].iloc[-1]
             stock_info['regularMarketOpen'] = df['Open'].iloc[-1]
        return df, stock_info
    except:
        return None, None

# --- 7. Display ---
if submit_btn:
    st.divider()
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)

    result_placeholder = st.empty()
    
    while True:
        with result_placeholder.container():
            with st.spinner(f"AI กำลังประมวลผล {symbol_input} ด้วย Smart Engine..."):
                df, info = get_data(symbol_input, tf_code)

            if df is not None and not df.empty and len(df) > 200:
                # คำนวณ Indicator
                df['EMA20'] = ta.ema(df['Close'], length=20)
                df['EMA50'] = ta.ema(df['Close'], length=50)
                df['EMA200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)
                macd = ta.macd(df['Close'])
                df = pd.concat([df, macd], axis=1)
                bbands = ta.bbands(df['Close'], length=20, std=2)
                df = pd.concat([df, bbands], axis=1)
                adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                df = pd.concat([df, adx], axis=1)
                df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)

                # ดึงค่าล่าสุด
                last = df.iloc[-1]
                price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
                rsi = last['RSI']
                ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
                vol_now=last['Volume']; vol_ma=last['Vol_SMA20']
                
                try: macd_val, macd_signal = last['MACD_12_26_9'], last['MACDs_12_26_9']
                except: macd_val, macd_signal = 0, 0
                try: adx_val = last['ADX_14']
                except: adx_val = 0
                
                bbl_col = bbands.columns[0]; bbu_col = bbands.columns[2]
                bb_upper = last[bbu_col]; bb_lower = last[bbl_col]

                # --- 🔥 เรียกใช้ AI Smart Logic (แทนอันเก่า) ---
                vol_status, vol_color = analyze_volume(vol_now, vol_ma)
                ai_report = ai_smart_logic(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, vol_status)

                # --- แสดงผล (UI เดิม) ---
                logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
                icon_html = f"""<img src="{logo_url}" onerror="this.onerror=null; this.src='https://cdn-icons-png.flaticon.com/512/720/720453.png';" style="height:50px;width:50px;border-radius:50%;vertical-align:middle;margin-right:10px;">"""
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

                    # OHLC (เพิ่มเข้ามาเพื่อให้ครบถ้วนเหมือนเดิม)
                    def make_pill(change, percent):
                        color = "#16a34a" if change >= 0 else "#dc2626"
                        bg = "#e8f5ec" if change >= 0 else "#fee2e2"
                        arrow = "▲" if change >= 0 else "▼"
                        return f'<span style="background:{bg}; color:{color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{arrow} {change:+.2f} ({percent:.2f}%)</span>'
                    
                    if info.get('preMarketPrice'):
                         p = info['preMarketPrice']; c = info['preMarketChange']; pct = (c/(p-c))*100 if p!=c else 0
                         st.markdown(f'<div style="font-size:12px; margin-top:5px;">☀️ Pre: <b>{p:.2f}</b> {make_pill(c, pct)}</div>', unsafe_allow_html=True)
                
                with c2:
                    st_color = ai_report["status_color"]
                    main_status = ai_report["banner_title"]
                    # ใช้ st.success/error/warning เหมือนเดิมเพื่อให้ UI ไม่เพี้ยน
                    if st_color == "green": st.success(f"**{main_status}**\n\n{ai_report['context']}")
                    elif st_color == "red": st.error(f"**{main_status}**\n\n{ai_report['context']}")
                    else: st.warning(f"**{main_status}**\n\n{ai_report['context']}")

                    st.markdown(f"**Action:** {ai_report['action']['strategy']}")
                    for step in ai_report['action']['steps']: st.caption(f"- {step}")

                st.markdown("---")
                
                # --- ส่วน Metrics (เพิ่ม Volume Status เข้าไป) ---
                c3, c4, c5 = st.columns(3)
                with c3:
                    # MACD
                    macd_txt = "Bullish" if macd_val > macd_signal else "Bearish"
                    st.markdown(custom_metric_html("MACD", f"{macd_val:.3f}", macd_txt, "green" if macd_val > macd_signal else "red", ""), unsafe_allow_html=True)
                with c4:
                    # RSI
                    rsi_txt = "Overbought" if rsi >= 70 else "Oversold" if rsi <= 30 else "Neutral"
                    st.markdown(custom_metric_html("RSI (14)", f"{rsi:.2f}", rsi_txt, "red" if rsi >= 70 or rsi <= 30 else "gray", ""), unsafe_allow_html=True)
                with c5:
                    # Volume (ของใหม่!)
                    st.markdown(custom_metric_html("Volume", f"{vol_now/1000000:.2f}M", vol_status, vol_color, ""), unsafe_allow_html=True)

                # --- 🔥 ส่วนเสริม: PROS & CONS (ของใหม่ที่แทรกเพิ่ม) ---
                st.subheader("🧐 AI Deep Dive (เจาะลึก)")
                c_pros, c_cons = st.columns(2)
                with c_pros:
                    if ai_report['pros']:
                        st.success(f"**✅ ปัจจัยบวก ({len(ai_report['pros'])})**")
                        for p in ai_report['pros']: st.write(f"- {p}")
                    else: st.write("- ไม่มีปัจจัยบวกชัดเจน")
                with c_cons:
                    if ai_report['cons']:
                        st.error(f"**❌ ปัจจัยลบ ({len(ai_report['cons'])})**")
                        for c in ai_report['cons']: st.write(f"- {c}")
                    else: st.write("- ความเสี่ยงต่ำ")

                # Disclaimer Box (เหมือนเดิม)
                st.markdown("""<div class='disclaimer-box'>⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากระบบ AI Scoring System เพื่อประกอบการตัดสินใจเท่านั้น</div>""", unsafe_allow_html=True)

                st.divider()
                # Learning Section (เหมือนเดิม)
                display_learning_section(rsi, get_rsi_interpretation(rsi), macd_val, macd_signal, "Bull/Bear", adx_val, get_adx_interpretation(adx_val), price, bb_upper, bb_lower)

            else:
                st.error("ไม่พบข้อมูลหุ้น")
        
        if not realtime_mode: break
        time.sleep(10)
