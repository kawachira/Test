import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import random

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master Pro", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (เพิ่มส่วน Score Card) ---
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
    
    /* CSS สำหรับ Trend Score */
    .score-box {
        padding: 20px; border-radius: 15px; text-align: center; color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai Stock Master <span style='color:#3b82f6; font-size: 1.5rem;'>Pro Max</span></h1>", unsafe_allow_html=True)
st.write("")

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ (SMC + AI Scoring)")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น NVDA, TSLA, BTC-USD):", value="NVDA").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
            
        submit_btn = st.form_submit_button("🚀 วิเคราะห์เจาะลึกทันที")

# --- 4. Helper Functions (เพิ่ม SMC & Score) ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 Extreme Overbought (ระวังเทขาย)"
    elif rsi >= 70: return "🟠 Overbought (ราคาตึงตัว)"
    elif rsi >= 55: return "🟢 Bullish Zone (กระทิงครอง)"
    elif rsi >= 45: return "⚪ Sideway (เลือกทาง)"
    elif rsi >= 30: return "🟠 Bearish Zone (หมีครอง)"
    elif rsi > 20: return "🟢 Oversold (เริ่มถูก)"
    else: return "🟢 Extreme Oversold (ถูกมาก)"

# [NEW] ฟังก์ชันหา SMC Supply/Demand Zones (Swing High/Low Length 5)
def get_smc_zones(df, length=5):
    df = df.copy()
    df['Swing_High'] = False
    df['Swing_Low'] = False
    
    # Loop หา Swing High/Low
    for i in range(length, len(df) - length):
        # Check Swing Low (Demand)
        is_low = True
        current_low = df['Low'].iloc[i]
        for j in range(1, length + 1):
            if df['Low'].iloc[i-j] < current_low or df['Low'].iloc[i+j] < current_low:
                is_low = False; break
        if is_low: df.at[df.index[i], 'Swing_Low'] = True

        # Check Swing High (Supply)
        is_high = True
        current_high = df['High'].iloc[i]
        for j in range(1, length + 1):
            if df['High'].iloc[i-j] > current_high or df['High'].iloc[i+j] > current_high:
                is_high = False; break
        if is_high: df.at[df.index[i], 'Swing_High'] = True

    current_price = df['Close'].iloc[-1]
    
    # Filter Active Zones
    demands = df[df['Swing_Low'] == True]
    active_demands = demands[demands['Low'] < current_price].tail(3)['Low'].values.tolist()
    
    supplies = df[df['Swing_High'] == True]
    active_supplies = supplies[supplies['High'] > current_price].tail(3)['High'].values.tolist()
    
    return active_demands, active_supplies

# [NEW] ฟังก์ชันคำนวณคะแนน AI Trend Score (0-100)
def calculate_trend_score(price, ema20, ema50, ema200, rsi, macd, macd_signal, vol_now, vol_avg):
    score = 0
    # 1. Trend (50%)
    if price > ema200: score += 25
    if price > ema50: score += 15
    if price > ema20: score += 10
    
    # 2. Momentum (30%)
    if macd > macd_signal: score += 15
    if 50 <= rsi <= 70: score += 15
    elif rsi > 70: score += 5
    elif 40 < rsi < 50: score += 5
    
    # 3. Volume (20%)
    if vol_now > vol_avg: score += 20
    
    return score

# --- 5. Get Data ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "10y"
        df = ticker.history(period=period_val, interval=interval)
        
        info = ticker.info
        stock_info = {
            'longName': info.get('longName', symbol),
            'trailingPE': info.get('trailingPE', 'N/A'),
            'regularMarketPrice': info.get('regularMarketPrice'),
            'regularMarketChange': info.get('regularMarketChange'),
            'regularMarketChangePercent': info.get('regularMarketChangePercent'),
            'preMarketPrice': info.get('preMarketPrice'),
            'postMarketPrice': info.get('postMarketPrice'),
        }
        
        # Fallback if regularMarketPrice is None
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]
             stock_info['regularMarketChangePercent'] = (stock_info['regularMarketChange'] / df['Close'].iloc[-2])

        return df, stock_info
    except:
        return None, None

# --- 6. AI Logic (UPDATED: ใช้ Score, SMC, MACD, Vol) ---
def analyze_market_structure_pro(price, ema20, ema50, ema200, rsi, macd, macd_signal, vol_now, vol_avg, atr, score):
    report = {
        "technical": {}, "context": "", "action": {}, "status_color": "", "banner_title": ""
    }
    
    # MACD Filter
    macd_bullish = macd > macd_signal
    is_downtrend = price < ema200
    
    # Volume Check
    vol_status = "🔥 วอลุ่มเข้า" if vol_now > vol_avg else "❄️ วอลุ่มบาง"

    # --- Scenario Logic ---
    
    # 1. Super Bullish (Score 80+)
    if score >= 80:
        report["status_color"] = "green"
        report["banner_title"] = f"Strong Bullish (Score: {score}) - {vol_status}"
        report["technical"] = {
            "structure": "ราคา > EMA ทุกเส้น + MACD ตัดขึ้น + Volume สนับสนุน",
            "status": "กระทิงดุเต็มพิกัด (Trend Following Mode)"
        }
        report["context"] = "หุ้นแข็งแกร่งกว่าตลาดมาก โอกาสไปต่อสูง อย่าเพิ่งรีบขายหมู"
        report["action"] = {
            "strategy": "**Let Profit Run**",
            "steps": [
                f"✅ **ถือต่อ:** ใช้ EMA 20 ({ema20:.2f}) เป็นจุดล็อคกำไร",
                f"🛡️ **Stop Loss (ATR):** {price - (atr*2):.2f}"
            ]
        }

    # 2. Correction / Sideway (Score 50-79)
    elif 50 <= score < 80 and not is_downtrend:
        report["status_color"] = "orange"
        report["banner_title"] = f"Correction/Sideway (Score: {score})"
        report["technical"] = {
            "structure": "ราคาพักตัวในขาขึ้น (ย่อตัวสร้างฐาน)",
            "status": "MACD อาจจะพักตัว หรือ ราคาหลุด EMA สั้น"
        }
        report["context"] = "เป็นจังหวะย่อเพื่อไปต่อ (Buy on Dip) รอสะสมของเมื่อราคานิ่ง"
        report["action"] = {
            "strategy": "**Wait & Buy on Dip**",
            "steps": [
                f"🎯 **รอรับที่:** Demand Zone หรือ EMA 50 ({ema50:.2f})",
                "⚠️ รอแท่งเทียนกลับตัวก่อนเข้า อย่าเพิ่งรับมีด"
            ]
        }

    # 3. Bearish / Downtrend (Score < 50)
    else:
        # Filter: RSI ต่ำแต่เทรนด์ยังลงแรง (Fix จุดอ่อน)
        if rsi < 30 and not macd_bullish:
            report["status_color"] = "red"
            report["banner_title"] = f"Downtrend Strong (Score: {score})"
            report["technical"] = {"structure": "ขาลงเต็มตัว", "status": "RSI Oversold แต่ MACD ยังจม (ห้ามรับมีด)"}
            report["context"] = "อันตราย! ราคายังลงไม่สุด อย่าเสี่ยงสวนเทรนด์"
            report["action"] = {
                "strategy": "**Wait & See (กำเงินสด)**",
                "steps": ["ห้ามซื้อจนกว่าจะยืนเหนือ EMA 50 ได้", "มองหาโอกาส Short Sell ที่แนวต้าน"]
            }
        elif rsi < 30 and macd_bullish:
            report["status_color"] = "yellow"
            report["banner_title"] = "Rebound Chance? (ลุ้นเด้งสั้น)"
            report["technical"] = {"structure": "ราคาลงลึก", "status": "เกิด Divergence (RSI ต่ำ + MACD ตัดขึ้น)"}
            report["context"] = "อาจมีการเด้งสั้นๆ (Technical Rebound) แต่ความเสี่ยงสูง"
            report["action"] = {
                "strategy": "**Play Rebound (ซิ่งสั้นๆ)**",
                "steps": ["เข้าเร็วออกเร็ว", f"เป้าขาย: EMA 20 ({ema20:.2f})"]
            }
        else:
            report["status_color"] = "red"
            report["banner_title"] = f"Bearish Zone (Score: {score})"
            report["technical"] = {"structure": "ต่ำกว่า EMA 200", "status": "หมีคุมตลาด"}
            report["context"] = "ตลาดเป็นขาลงชัดเจน หลีกเลี่ยงไปก่อน"
            report["action"] = {
                "strategy": "**Defensive Mode**",
                "steps": ["ลดพอร์ต / ถือเงินสด", "รอสัญญาณกลับตัวที่ชัดเจนกว่านี้"]
            }

    return report

# --- 7. Display Logic ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังคำนวณข้อมูลเชิงลึก SMC + Trend Score ของ {symbol_input} ..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            # --- Calculation Zone ---
            # 1. Indicators
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            df['VOL_SMA'] = ta.sma(df['Volume'], length=5)
            
            macd = ta.macd(df['Close'])
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_SIGNAL'] = macd['MACDs_12_26_9']
            
            # 2. SMC Zones
            smc_demand, smc_supply = get_smc_zones(df, length=5)

            # 3. Last Values
            last = df.iloc[-1]
            price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
            
            # 4. AI Score
            score = calculate_trend_score(
                price, last['EMA20'], last['EMA50'], last['EMA200'], 
                last['RSI'], last['MACD'], last['MACD_SIGNAL'], 
                last['Volume'], last['VOL_SMA']
            )
            
            # 5. Get Report
            ai_report = analyze_market_structure_pro(
                price, last['EMA20'], last['EMA50'], last['EMA200'], 
                last['RSI'], last['MACD'], last['MACD_SIGNAL'], 
                last['Volume'], last['VOL_SMA'], last['ATR'], score
            )

            # --- UI Display ---
            
            # Header
            st.markdown(f"<h2 style='text-align: center; margin-top: -15px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
            
            # Price Section
            c_price, c_score = st.columns([1.5, 1])
            with c_price:
                reg_price = info.get('regularMarketPrice')
                reg_chg = info.get('regularMarketChange')
                reg_pct = info.get('regularMarketChangePercent', 0) * 100
                
                bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
                color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"
                
                st.markdown(f"""
                <div style="padding: 20px; background: {bg_color}; border-radius: 15px; display: flex; align-items: center; gap: 20px;">
                  <div style="font-size:45px; font-weight:700; color: #1f2937;">{reg_price:,.2f}</div>
                  <div style="font-size:24px; font-weight:600; color:{color_text};">{arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Metrics Row
                m1, m2, m3 = st.columns(3)
                m1.metric("📊 P/E Ratio", f"{info['trailingPE']:.2f}" if isinstance(info['trailingPE'], (int,float)) else "N/A")
                m2.metric("⚡ RSI (14)", f"{last['RSI']:.2f}", "Over" if last['RSI']>70 else "Norm")
                
                vol_pct = (last['Volume']/last['VOL_SMA'])*100
                m3.metric("🌊 Volume", f"{vol_pct:.0f}%", "vs Avg 5 Day", delta_color="normal")

            # Score Section (Visual Gauge)
            with c_score:
                score_color = "#22c55e" if score >= 75 else ("#eab308" if score >= 50 else "#ef4444")
                st.markdown(f"""
                <div class="score-box" style="background-color: {score_color};">
                    <h3 style="margin:0; color:white;">AI Trend Score</h3>
                    <h1 style="font-size: 70px; margin:0; color:white; font-weight:800;">{score}</h1>
                    <p style="margin:0; font-size: 14px; opacity: 0.9;">คะแนนความแข็งแกร่ง (เต็ม 100)</p>
                </div>
                """, unsafe_allow_html=True)

            st.write("") 

            # Analysis Section (Left: SMC/EMA, Right: AI Report)
            c_tech, c_ai = st.columns([1.3, 2])
            
            with c_tech:
                st.subheader("🧱 SMC Zones & Levels")
                st.info("โซนราคาสำคัญตามรอยเท้าเจ้ามือ (Smart Money)")
                
                # SMC Supply
                st.markdown("**🟦 Supply Zones (ต้านแข็ง):**")
                if smc_supply:
                    for s in reversed(smc_supply): st.markdown(f"- 🔴 **{s:,.2f}**")
                else: st.caption("- ไม่พบโซนต้านใกล้เคียง")
                
                st.markdown("---")
                
                # SMC Demand
                st.markdown("**🟧 Demand Zones (รับแข็ง):**")
                if smc_demand:
                    for d in reversed(smc_demand): st.markdown(f"- 🟢 **{d:,.2f}**")
                else: st.caption("- ไม่พบโซนรับใกล้เคียง")
                
                st.markdown("---")
                st.markdown("**📉 เส้นค่าเฉลี่ย (EMA):**")
                st.write(f"EMA 20 (สั้น): **{last['EMA20']:.2f}**")
                st.write(f"EMA 50 (กลาง): **{last['EMA50']:.2f}**")
                st.write(f"EMA 200 (ยาว): **{last['EMA200']:.2f}**")

            with c_ai:
                st.subheader("🤖 AI INTELLIGENT REPORT (PRO)")
                
                # Banner
                color_map = {"green": "success", "orange": "warning", "red": "error", "yellow": "warning"}
                msg_type = color_map.get(ai_report["status_color"], "info")
                
                if msg_type == "success": st.success(f"📈 {ai_report['banner_title']}")
                elif msg_type == "error": st.error(f"📉 {ai_report['banner_title']}")
                else: st.warning(f"⚖️ {ai_report['banner_title']}")

                with st.chat_message("assistant"):
                    st.markdown(f"**🧠 1. บทวิเคราะห์ (Technical Insight):**")
                    st.markdown(f"- {ai_report['technical']['structure']}")
                    st.markdown(f"- {ai_report['technical']['status']}")
                    
                    st.markdown("---")
                    
                    st.markdown(f"**📚 2. สรุปสถานการณ์ (Context):**")
                    st.markdown(f"_{ai_report['context']}_")
                    
                    st.markdown("---")
                    
                    st.markdown(f"**✅ 3. Action Plan (แนะนำ):**")
                    st.markdown(f"### {ai_report['action']['strategy']}")
                    for step in ai_report['action']['steps']:
                        st.markdown(f"- {step}")

            # Footer Space
            st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

        elif df is not None: st.warning("⚠️ ข้อมูลไม่พอคำนวณ (New Listing?)"); st.line_chart(df['Close'])
        else: st.error(f"❌ ไม่พบข้อมูล: {symbol_input}")
