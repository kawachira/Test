import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import random
import time

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (คงเดิม 100%) ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    h1 { text-align: center; font-size: 2.8rem !important; margin-bottom: 10px; }
    div[data-testid="stForm"] {
        border: none; padding: 30px; border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px; margin: 0 auto;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 12px; font-size: 1.2rem; font-weight: bold; padding: 15px 0;
    }
    div[data-testid="metric-container"] label { font-size: 1.1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ (Enhanced Edition)</span></h1>", unsafe_allow_html=True)
st.write("")

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB, TSLA):", value="EOSE").upper().strip()
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

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 Extreme Overbought"
    elif rsi >= 70: return "🟠 Overbought"
    elif rsi >= 55: return "🟢 Bullish Zone"
    elif rsi >= 45: return "⚪ Neutral"
    elif rsi >= 30: return "🟠 Bearish Zone"
    elif rsi > 20: return "🟢 Oversold"
    else: return "🟢 Extreme Oversold"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ N/A"
    if pe < 0: return "🔴 ขาดทุน"
    if pe < 15: return "🟢 หุ้นถูก (Value)"
    if pe < 30: return "🟡 ราคาเหมาะสม"
    return "🟠 หุ้นแพง (Growth)"

# --- 5. Get Data (Updated Cache Logic) ---
@st.cache_data(ttl=10, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "10y"
        df = ticker.history(period=period_val, interval=interval)
        
        # --- NEW: ดึงข้อมูล Market Cap และ Volume Avg เพื่อความแม่นยำ ---
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
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

# --- 6. AI Logic (UPDATED: เพิ่มตัวแปรใหม่เข้าไปคำนวณ) ---
# เพิ่ม arguments: macd_val, macd_signal, adx_val, bb_upper, bb_lower
def analyze_market_structure(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower):
    report = {
        "technical": {},
        "context": "",
        "action": {},
        "status_color": "",
        "banner_title": ""
    }

    def pick_one(sentences): return random.choice(sentences)

    # --- เช็ค Trend Strength ด้วย ADX ---
    trend_strength = ""
    if adx_val > 50: trend_strength = "Trend แข็งแกร่งมาก (Super Strong)"
    elif adx_val > 25: trend_strength = "มี Trend ชัดเจน (Strong)"
    else: trend_strength = "Trend อ่อนแอ / ไซด์เวย์ (Weak/Sideway)"

    # --- เช็ค Momentum ด้วย MACD ---
    macd_status = "Bullish" if macd_val > macd_signal else "Bearish"

    # --- Scenario 1: ขาขึ้นแข็งแกร่ง (Super Strong Uptrend) ---
    if price > ema200 and price > ema50 and price > ema20:
        report["status_color"] = "green"
        
        # เพิ่มการเช็ค MACD และ ADX เพื่อความแม่นยำ
        if adx_val > 25 and macd_status == "Bullish":
             report["banner_title"] = "🚀 Super Bullish: ขาขึ้นสมบูรณ์แบบ"
        else:
             report["banner_title"] = "Bullish: ขาขึ้น (แต่เริ่มตึงตัว)"

        report["technical"] = {
            "structure": f"ราคายืนเหนือทุกเส้น EMA + {trend_strength}",
            "status": f"MACD ตัดขึ้น ({macd_status}) สนับสนุนทิศทางขาขึ้น"
        }
        
        # เช็ค Bollinger Band: ถ้าราคาทะลุกรอบบน ระวังการย่อตัว
        if price > bb_upper:
            report["context"] = "⚠️ ราคาทะลุกรอบ Bollinger Band บน (Overextended) ระวังแรงขายทำกำไรระยะสั้น อย่าเพิ่งไล่ราคาตอนนี้"
            action_1 = "แบ่งขายทำกำไรบางส่วน (Trim Profit) แล้วรอรับกลับเมื่อย่อ"
        else:
            report["context"] = "โมเมนตัมแข็งแกร่ง รายใหญ่ยังคุมเกม ตลาดยังมีพื้นที่ให้วิ่งต่อ (Upside Open)"
            action_1 = "ถือต่อ (Let Profit Run) ใช้ EMA 20 เป็นจุด Trailing Stop"
            
        action_2 = f"จุดรับที่ดีคือ EMA 20 ({ema20:.2f}) หรือเส้นกลาง Bollinger"
        report["action"] = {"strategy": "**กลยุทธ์: Follow Trend (เกาะเทรนด์)**", "steps": [action_1, action_2]}

    # --- Scenario 2: ขาขึ้นพักตัว (Correction) ---
    elif price > ema200 and price < ema20:
        report["status_color"] = "orange"
        report["banner_title"] = "Correction: พักตัวในขาขึ้น"

        # ใช้ MACD ช่วยดูว่าพักตัวจบหรือยัง
        reversal_sign = "เริ่มมีสัญญาณกลับตัว" if macd_val > macd_signal else "แรงขายยังกดดันอยู่"

        report["technical"] = {
            "structure": "หลุด EMA 20 ลงมาพักตัว แต่ยังอยู่เหนือ EMA 200 (ระยะยาวยังขึ้น)",
            "status": f"ADX = {adx_val:.2f} ({trend_strength}) | MACD: {reversal_sign}"
        }
        
        report["context"] = "เป็นจังหวะย่อตัวเพื่อสร้างฐานใหม่ (Healthy Correction) ตราบใดที่ไม่หลุด EMA 200 โครงสร้างยังไม่เสีย"
        
        action_1 = f"รอสัญญาณกลับตัว (Reversal Candle) แถว EMA 50 ({ema50:.2f}) หรือ EMA 200"
        action_2 = "ถ้า MACD ตัดขึ้น (Cross up) อีกครั้ง คือสัญญาณเข้าซื้อรอบใหม่ (Re-entry)"

        report["action"] = {"strategy": "**กลยุทธ์: Buy on Dip (รอย่อซื้อ)**", "steps": [action_1, action_2]}

    # --- Scenario 3: ขาลง (Downtrend) ---
    elif price < ema200 and price < ema50:
        if price < ema20:
            if rsi < 25 or price < bb_lower: # เพิ่มเงื่อนไขหลุดกรอบล่าง BB
                report["status_color"] = "orange"
                report["banner_title"] = "Oversold Bounce: ลุ้นเด้งสั้น (Oversold)"
                report["technical"] = {
                    "structure": "ราคาลงลึกหลุดกรอบล่าง Bollinger / RSI ต่ำมาก",
                    "status": "เข้าเขต Selling Climax (ขายมากเกินไป) มีโอกาสดีดกลับแรงๆ"
                }
                report["context"] = "ความเสี่ยงสูง แต่ Reward คุ้มค่าสำหรับคนเล่นสั้น (High Risk High Return)"
                action_1 = "เก็งกำไรสั้นๆ (Scalp) เป้าขายคือเส้นกลาง Bollinger หรือ EMA 20"
                action_2 = "วาง Stop Loss ไว้ที่ Low ล่าสุดทันที ห้ามลืม"
            else:
                report["status_color"] = "red"
                report["banner_title"] = "Bearish: ขาลงเต็มตัว"
                report["technical"] = {
                    "structure": f"ราคาอยู่ใต้ EMA ทุกเส้น + {trend_strength}",
                    "status": "MACD อยู่ในแดนลบ (Negative Zone) ยืนยันขาลง"
                }
                report["context"] = "แรงขายยังคงครองตลาด (Dominated by Sellers) การเด้งขึ้นคือจังหวะขาย"
                action_1 = "ห้ามรับมีด (Don't Buy) จนกว่าราคาจะยืนเหนือ EMA 20 ได้"
                action_2 = "ใครติดดอย หาจังหวะเด้งเพื่อลดพอร์ต (Cut Loss / Reduce Position)"
        else:
             # เด้งในขาลง
            report["status_color"] = "orange"
            report["banner_title"] = "Rebound: เด้งเพื่อลงต่อ?"
            report["technical"] = {
                "structure": "ราคาดีดกลับมาหา EMA 50/200 แต่เทรนด์หลักยังลง",
                "status": f"MACD ตัดขึ้นระยะสั้น แต่ยังอยู่ใต้ศูนย์ (Weak Bullish)"
            }
            report["context"] = "ระวังกับดักกระทิง (Bull Trap) แนวต้าน EMA 200 มักจะผ่านยากในครั้งแรก"
            action_1 = f"จับตาแนวต้าน {ema200:.2f} ถ้าไม่ผ่านให้ขาย"
            action_2 = "เล่นสั้นเท่านั้น (Hit & Run)"
        
        report["action"] = {"strategy": "**กลยุทธ์: Defensive / Short Sell**", "steps": [action_1, action_2]}

    # --- Scenario 4: ไซด์เวย์ (Sideway) ---
    else:
        report["status_color"] = "yellow"
        # ใช้ Bollinger Band Width ช่วยดูการบีบตัว (Squeeze)
        bb_width = (bb_upper - bb_lower) / price
        sqz_text = "ระเบิดเลือกทางเร็วๆนี้" if bb_width < 0.10 else "แกว่งตัวในกรอบกว้าง"

        report["banner_title"] = "Sideway: รอเลือกทาง"
        report["technical"] = {
            "structure": "ราคาพันกันนัวเนีย EMA + ADX ต่ำ (ไม่มีเทรนด์)",
            "status": f"Bollinger Band บีบตัว: {sqz_text}"
        }
        report["context"] = "ตลาดยังไม่เลือกข้างชัดเจน (Indecision) การเทรดในช่วงนี้จะยากเพราะ False Signal เยอะ"
        action_1 = f"รอให้ราคา Breakout กรอบ Bollinger บน ({bb_upper:.2f}) หรือ ล่าง ({bb_lower:.2f}) ก่อน"
        action_2 = "เน้นซื้อที่แนวรับ ขายที่แนวต้าน (Swing Trade) อย่าหวังคำโต"
        
        report["action"] = {"strategy": "**กลยุทธ์: Wait & See / Swing Trade**", "steps": [action_1, action_2]}

    return report

# --- 7. Display (ใส่ระบบ Loop Real-time) ---
if submit_btn:
    st.divider()
    result_placeholder = st.empty()
    
    while True:
        with result_placeholder.container():
            with st.spinner(f"AI กำลังประมวลผล {symbol_input} แบบละเอียด (Full Loop)..."):
                df, info = get_data(symbol_input, tf_code)

            if df is not None and not df.empty and len(df) > 200:
                # --- CALCULATION ZONE (เพิ่มตรงนี้) ---
                # 1. EMAs & RSI (เดิม)
                df['EMA20'] = ta.ema(df['Close'], length=20)
                df['EMA50'] = ta.ema(df['Close'], length=50)
                df['EMA200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)
                
                # 2. MACD (ใหม่) - บอกโมเมนตัม
                macd = ta.macd(df['Close'])
                df = pd.concat([df, macd], axis=1) # รวมเข้า DF
                # macd columns: MACD_12_26_9, MACDh_12_26_9 (hist), MACDs_12_26_9 (signal)
                
                # 3. Bollinger Bands (ใหม่) - บอก Volatility
                bbands = ta.bbands(df['Close'], length=20, std=2)
                df = pd.concat([df, bbands], axis=1)
                # bb columns: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
                
                # 4. ADX (ใหม่) - บอก Trend Strength
                adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                df = pd.concat([df, adx], axis=1)
                # adx column: ADX_14

                # --- Extract Last Values ---
                last = df.iloc[-1]
                price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
                
                # ดึงค่าตัวแปรเดิม
                rsi = last['RSI']
                ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
                
                # ดึงค่าตัวแปรใหม่ (ใช้ชื่อ Column ตาม pandas_ta default)
                macd_val = last['MACD_12_26_9']
                macd_signal = last['MACDs_12_26_9']
                adx_val = last['ADX_14']
                bb_upper = last['BBU_20_2.0']
                bb_lower = last['BBL_20_2.0']
                
                # ส่งเข้า AI Logic ใหม่
                ai_report = analyze_market_structure(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower)

                # --- DISPLAY UI ---
                # Header
                st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
                
                # Price Section (คงเดิม)
                c1, c2 = st.columns(2)
                with c1:
                    reg_price = info.get('regularMarketPrice')
                    reg_chg = info.get('regularMarketChange')
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
                      <div style="
                        display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text};
                        padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">
                        {arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Pre/Post Logic (คงเดิม)
                    pre_p = info.get('preMarketPrice'); pre_c = info.get('preMarketChange'); 
                    post_p = info.get('postMarketPrice'); post_c = info.get('postMarketChange');
                    extra_html = ""
                    if pre_p and pre_c is not None:
                        extra_html += f"<div>☀️ ก่อนเปิด: <b>{pre_p:.2f}</b> <span style='color:{'#16a34a' if pre_c>0 else '#dc2626'}'>{arrow_html(pre_c)} {pre_c:+.2f}</span></div>"
                    if post_p and post_c is not None:
                        extra_html += f"<div>🌙 หลังปิด: <b>{post_p:.2f}</b> <span style='color:{'#16a34a' if post_c>0 else '#dc2626'}'>{arrow_html(post_c)} {post_c:+.2f}</span></div>"
                    if extra_html: st.markdown(f"<div style='font-size:14px; color:#6b7280; display:flex; gap: 15px; flex-wrap: wrap; margin-top: 5px;'>{extra_html}</div>", unsafe_allow_html=True)

                # Banner Status
                if tf_code == "1h": tf_label = "TF Hour"
                elif tf_code == "1wk": tf_label = "TF Week"
                else: tf_label = "TF Day"
                
                st_color = ai_report["status_color"]
                main_status = ai_report["banner_title"]
                if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
                elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
                else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

                # Metrics Row 1 (Basic)
                c3, c4, c5 = st.columns(3)
                with c3:
                    st.metric("📊 P/E Ratio", f"{info['trailingPE']:.2f}" if isinstance(info['trailingPE'], (int,float)) else "N/A")
                    st.caption(get_pe_interpretation(info['trailingPE']))
                with c4:
                    rsi_lbl = "Overbought" if rsi>=70 else ("Oversold" if rsi<=30 else "Neutral")
                    st.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_lbl, delta_color="inverse" if rsi>70 else "normal")
                with c5:
                    # NEW METRIC: ADX
                    adx_lbl = "Strong Trend" if adx_val > 25 else "Weak/Sideway"
                    st.metric("💪 ADX Strength", f"{adx_val:.2f}", adx_lbl)

                st.write("") 

                # Analysis Section
                c_ema, c_ai = st.columns([1.5, 2])
                with c_ema:
                    st.subheader("📉 Technical Indicators")
                    # Update ให้แสดงค่าใหม่ด้วย
                    st.markdown(f"""
                    <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'>
                        <div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd;'><b>Indicator</b> <b>Value</b></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{ema20:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 50</span> <span>{ema50:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{ema200:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between; color: #888;'><span>---</span><span>---</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>MACD</span> <span style='color:{'green' if macd_val > macd_signal else 'red'}'>{macd_val:.3f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>Upper Band</span> <span>{bb_upper:.2f}</span></div>
                        <div style='display:flex; justify-content:space-between;'><span>Lower Band</span> <span>{bb_lower:.2f}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.subheader("🚧 Key Levels (S/R)")
                    supports, resistances = [] , []
                    # Logic แนวรับแนวต้านเดิม เพิ่มเติมคือใช้ BB มาช่วย
                    if price > ema200: supports.extend([(ema20, "EMA 20"), (bb_lower, "BB Lower")])
                    else: resistances.extend([(ema200, "EMA 200"), (bb_upper, "BB Upper")])
                    
                    res_val = df['High'].tail(60).max(); resistances.append((res_val, "High 60 Days"))
                    sup_val = df['Low'].tail(60).min(); supports.append((sup_val, "Low 60 Days"))

                    st.markdown("#### 🟢 แนวรับ")
                    for v, d in supports: 
                        if v < price: st.write(f"- **{v:.2f}** : {d}")
                    st.markdown("#### 🔴 แนวต้าน")
                    for v, d in resistances:
                        if v > price: st.write(f"- **{v:.2f}** : {d}")

                with c_ai:
                    st.subheader("🤖 AI ADVANCED ANALYSIS")
                    with st.chat_message("assistant"):
                        st.markdown("### 🧠 1. บทวิเคราะห์เชิงลึก (Deep Dive):")
                        st.markdown(f"- **Market Structure:** {ai_report['technical']['structure']}")
                        st.markdown(f"- **Indicators Status:** {ai_report['technical']['status']}")
                        st.markdown("---")
                        st.markdown("### 🌍 2. สภาพคล่องและบริบท (Context):")
                        st.write(ai_report['context'])
                        st.markdown("---")
                        st.markdown("### 🎯 3. Action Plan (แผนการเทรด):")
                        st.info(ai_report['action']['strategy'])
                        for step in ai_report['action']['steps']:
                            st.write(f"- {step}")
            else:
                st.error("ไม่พบข้อมูลหุ้น หรือ ข้อมูลไม่เพียงพอสำหรับคำนวณ Indicator (ต้องมีมากกว่า 200 แท่งเทียน)")
        
        # Loop delay check
        if not realtime_mode: break
        time.sleep(10)
